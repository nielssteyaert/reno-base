from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig, get_config, set_config
from app.main import app


@pytest.fixture
def data_dir(tmp_path: Path) -> Iterator[Path]:
    original = get_config()
    set_config(AppConfig(data_dir=tmp_path, static_dir=tmp_path / "static", dev_mode=True))
    yield tmp_path
    set_config(original)


@pytest.fixture
def client(data_dir: Path) -> Iterator[TestClient]:
    with TestClient(app, headers={"X-Remote-User-Display-Name": "Tester"}) as test_client:
        yield test_client


@pytest.fixture
def seeded(client: TestClient) -> dict:
    """A small project: 100k budget, 10% contingency, two categories, a room and a supplier."""
    client.patch("/api/settings", json={"total_budget_cents": 10_000_000, "contingency_pct": 10})
    kitchen = client.post(
        "/api/categories", json={"name": "Kitchen", "budget_cents": 3_000_000}
    ).json()
    appliances = client.post(
        "/api/categories", json={"name": "Appliances", "parent_id": kitchen["id"]}
    ).json()
    electrical = client.post(
        "/api/categories", json={"name": "Electrical", "budget_cents": 1_000_000}
    ).json()
    room = client.post(
        "/api/rooms", json={"name": "Ground floor", "budget_cents": 5_000_000}
    ).json()
    supplier = client.post("/api/suppliers", json={"name": "ACME Builders"}).json()
    return {
        "kitchen": kitchen,
        "appliances": appliances,
        "electrical": electrical,
        "room": room,
        "supplier": supplier,
    }
