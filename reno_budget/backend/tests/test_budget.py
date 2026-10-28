from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.models import Milestone
from app.money import split_incl, vat_from_excl
from app.services.budget import health, milestone_status


def _expense(client: TestClient, **fields) -> dict:
    body = {"title": "Item", "vat_rate": 0, **fields}
    response = client.post("/api/expenses", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _pay(client: TestClient, expense_id: int, amount: int, day: str = "2026-02-10") -> None:
    response = client.post(
        f"/api/expenses/{expense_id}/payments", json={"date": day, "amount_cents": amount}
    )
    assert response.status_code == 201


def test_rounding_helpers():
    assert vat_from_excl(50, 21) == 11  # 10.5 → 11 (half-up)
    assert vat_from_excl(0, 21) == 0
    for incl in (1, 99, 12_100, 99_999):
        excl, vat = split_incl(incl, 6)
        assert excl + vat == incl


def test_health_thresholds():
    assert health(100, None) == "none"
    assert health(80, 100) == "ok"
    assert health(90, 100) == "warning"
    assert health(101, 100) == "over"


def test_milestone_status():
    today = date(2026, 5, 1)
    assert milestone_status(Milestone(name="a"), today) == "planned"
    assert (
        milestone_status(Milestone(name="b", actual_start=date(2026, 4, 1)), today) == "in_progress"
    )
    assert milestone_status(Milestone(name="c", planned_end=date(2026, 4, 30)), today) == "late"
    assert (
        milestone_status(
            Milestone(name="d", planned_end=date(2026, 4, 1), actual_end=date(2026, 4, 2)), today
        )
        == "done"
    )


def test_project_summary_and_contingency(client: TestClient, seeded: dict):
    # budget 100,000.00 with a 10% reserve → working budget 90,000.00
    _expense(client, stage="estimate", amount_cents=1_000_000)
    _expense(client, stage="quote", amount_cents=2_000_000)
    ordered = _expense(client, stage="ordered", amount_cents=3_000_000)
    _pay(client, ordered["id"], 1_000_000)

    summary = client.get("/api/reports/summary").json()
    assert summary["estimated"] == 1_000_000
    assert summary["quoted"] == 2_000_000
    assert summary["committed"] == 3_000_000
    assert summary["paid"] == 1_000_000
    assert summary["outstanding"] == 2_000_000
    assert summary["forecast"] == 6_000_000
    assert summary["remaining"] == 4_000_000
    assert summary["contingency_reserve"] == 1_000_000
    assert summary["working_budget"] == 9_000_000
    assert summary["uses_contingency"] is False
    assert summary["pct_committed"] == 0.3
    # category budgets: Kitchen 30k + Electrical 10k allocated out of the 90k working budget
    assert summary["allocated_budget"] == 4_000_000
    assert summary["unallocated_budget"] == 5_000_000

    _expense(client, stage="estimate", amount_cents=3_500_000)
    summary = client.get("/api/reports/summary").json()
    assert summary["uses_contingency"] is True
    assert summary["over_budget"] is False
    assert summary["contingency_used"] == 500_000

    funnel = {f["status"]: f for f in summary["funnel"]}
    assert funnel["estimate"]["count"] == 2
    assert funnel["ordered"]["amount"] == 3_000_000


def test_category_rollup_and_budget_from_children(client: TestClient, seeded: dict):
    kitchen, appliances = seeded["kitchen"], seeded["appliances"]
    client.patch(f"/api/categories/{appliances['id']}", json={"budget_cents": 500_000})
    _expense(client, category_id=kitchen["id"], stage="ordered", amount_cents=1_000_000)
    _expense(client, category_id=appliances["id"], stage="ordered", amount_cents=600_000)
    _expense(client, stage="estimate", amount_cents=100)

    rows = client.get("/api/reports/categories").json()
    kitchen_row = next(r for r in rows if r["name"] == "Kitchen")
    assert kitchen_row["committed"] == 1_600_000
    assert kitchen_row["budget"] == 3_000_000
    child = kitchen_row["children"][0]
    assert child["name"] == "Appliances"
    assert child["health"] == "over"
    assert rows[-1]["name"] == "Uncategorized"
    assert rows[-1]["estimated"] == 100

    # A parent without its own budget uses the sum of its children's budgets.
    client.patch(f"/api/categories/{kitchen['id']}", json={"budget_cents": None})
    kitchen_row = next(
        r for r in client.get("/api/reports/categories").json() if r["name"] == "Kitchen"
    )
    assert kitchen_row["budget"] == 500_000


def test_rooms_and_suppliers(client: TestClient, seeded: dict):
    room, supplier = seeded["room"], seeded["supplier"]
    paid = _expense(
        client,
        room_id=room["id"],
        supplier_id=supplier["id"],
        stage="invoiced",
        amount_cents=200_000,
    )
    _pay(client, paid["id"], 200_000, "2026-03-15")
    _expense(client, supplier_id=supplier["id"], stage="quote", amount_cents=50_000)

    room_row = next(r for r in client.get("/api/reports/rooms").json() if r["id"] == room["id"])
    assert room_row["paid"] == 200_000
    assert room_row["pct_paid"] == 0.04

    supplier_row = client.get("/api/reports/suppliers").json()[0]
    assert supplier_row["name"] == "ACME Builders"
    assert supplier_row["count"] == 2
    assert supplier_row["quoted"] == 50_000
    assert supplier_row["last_payment"] == "2026-03-15"


def test_monthly_and_upcoming(client: TestClient):
    first = _expense(
        client,
        stage="invoiced",
        amount_cents=1_000,
        expense_date="2026-01-05",
        due_date="2026-02-01",
    )
    _pay(client, first["id"], 400, "2026-01-20")
    _expense(client, stage="ordered", amount_cents=500, expense_date="2026-03-01")

    data = client.get("/api/reports/monthly").json()
    months = {m["month"]: m for m in data["months"]}
    assert months["2026-01"]["paid"] == 400
    assert months["2026-01"]["committed"] == 1_000
    assert months["2026-02"]["paid"] == 0
    assert months["2026-03"]["cumulative_committed"] == 1_500

    upcoming = client.get("/api/reports/forecast").json()["upcoming"]
    assert {"month": "2026-02", "amount": 600} in upcoming
    assert {"month": "unscheduled", "amount": 500} in upcoming


def test_report_filters(client: TestClient, seeded: dict):
    _expense(
        client, category_id=seeded["electrical"]["id"], amount_cents=100, expense_date="2026-01-01"
    )
    _expense(
        client, category_id=seeded["kitchen"]["id"], amount_cents=200, expense_date="2026-06-01"
    )
    summary = client.get("/api/reports/summary", params={"date_from": "2026-03-01"}).json()
    assert summary["count"] == 1
    assert summary["estimated"] == 200
    summary = client.get(
        "/api/reports/summary",
        params={"status": ["estimate"], "category_id": seeded["electrical"]["id"]},
    ).json()
    assert summary["count"] == 1
    assert summary["estimated"] == 100


def test_dashboard_shape(client: TestClient, seeded: dict):
    _expense(client, stage="invoiced", amount_cents=100, due_date="2020-01-01")
    client.post(
        "/api/milestones",
        json={"name": "Demolition", "planned_start": "2026-01-01", "planned_end": "2026-01-31"},
    )
    data = client.get("/api/reports/dashboard").json()
    assert set(data) == {"summary", "categories", "rooms", "due", "milestones", "recent"}
    assert data["due"][0]["overdue"] is True
    assert data["milestones"][0]["name"] == "Demolition"
    assert data["recent"]
