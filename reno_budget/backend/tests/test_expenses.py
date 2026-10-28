from __future__ import annotations

from fastapi.testclient import TestClient


def _expense(client: TestClient, **fields) -> dict:
    body = {"title": "Item", "amount_cents": 100_000, "vat_rate": 21, **fields}
    response = client.post("/api/expenses", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_vat_computed_from_excl(client: TestClient):
    expense = _expense(client, amount_cents=12_345, vat_rate=6)
    assert expense["amount_excl_cents"] == 12_345
    assert expense["vat_cents"] == 741  # 740.7 rounded half-up
    assert expense["amount_incl_cents"] == 13_086


def test_amount_entered_incl_vat_splits_exactly(client: TestClient):
    expense = _expense(client, amount_cents=9_999, amount_includes_vat=True, vat_rate=21)
    assert expense["amount_incl_cents"] == 9_999
    assert expense["amount_excl_cents"] + expense["vat_cents"] == 9_999


def test_default_vat_rate_from_settings(client: TestClient):
    client.patch("/api/settings", json={"default_vat_rate": 6})
    expense = client.post("/api/expenses", json={"title": "Tiles", "amount_cents": 10_000}).json()
    assert expense["vat_rate"] == 6
    assert expense["vat_cents"] == 600


def test_vat_rate_change_keeps_excl_amount(client: TestClient):
    expense = _expense(client, amount_cents=10_000, vat_rate=21)
    updated = client.patch(f"/api/expenses/{expense['id']}", json={"vat_rate": 6}).json()
    assert updated["amount_excl_cents"] == 10_000
    assert updated["vat_cents"] == 600


def test_lifecycle_and_installments(client: TestClient):
    expense = _expense(client, stage="quote", amount_cents=100_000, vat_rate=21)
    assert expense["status"] == "quote"
    assert not expense["committed"]
    assert expense["outstanding_cents"] == 0

    client.patch(f"/api/expenses/{expense['id']}", json={"stage": "ordered"})
    client.post(
        f"/api/expenses/{expense['id']}/payments",
        json={"date": "2026-03-01", "amount_cents": 30_000},
    )
    detail = client.get(f"/api/expenses/{expense['id']}").json()
    assert detail["payment_status"] == "partial"
    assert detail["status"] == "ordered"
    assert detail["paid_cents"] == 30_000
    assert detail["outstanding_cents"] == 91_000

    remaining = client.post(
        f"/api/expenses/{expense['id']}/pay-remaining", json={"date": "2026-04-01"}
    ).json()
    assert remaining["amount_cents"] == 91_000
    detail = client.get(f"/api/expenses/{expense['id']}").json()
    assert detail["status"] == "paid"
    assert detail["payment_status"] == "paid"
    assert detail["outstanding_cents"] == 0
    assert len(detail["payments"]) == 2

    again = client.post(f"/api/expenses/{expense['id']}/pay-remaining", json={"date": "2026-04-02"})
    assert again.status_code == 409


def test_payment_on_estimate_counts_as_committed(client: TestClient):
    expense = _expense(client, stage="estimate")
    client.post(
        f"/api/expenses/{expense['id']}/payments", json={"date": "2026-01-01", "amount_cents": 1}
    )
    assert client.get(f"/api/expenses/{expense['id']}").json()["committed"] is True


def test_filters_and_search(client: TestClient, seeded: dict):
    _expense(client, title="Oven", category_id=seeded["appliances"]["id"])
    _expense(client, title="Wiring", category_id=seeded["electrical"]["id"], notes="rewire hall")
    by_parent = client.get("/api/expenses", params={"category_id": seeded["kitchen"]["id"]}).json()
    assert [e["title"] for e in by_parent] == ["Oven"]
    by_text = client.get("/api/expenses", params={"q": "HALL"}).json()
    assert [e["title"] for e in by_text] == ["Wiring"]


def test_bulk_update_and_delete(client: TestClient, seeded: dict):
    ids = [_expense(client, title=f"E{i}")["id"] for i in range(3)]
    result = client.post(
        "/api/expenses/bulk",
        json={
            "ids": ids[:2],
            "action": "update",
            "changes": {"room_id": seeded["room"]["id"], "vat_rate": 6},
        },
    ).json()
    assert result["affected"] == 2
    updated = client.get(f"/api/expenses/{ids[0]}").json()
    assert updated["room_id"] == seeded["room"]["id"]
    assert updated["vat_cents"] == 6_000

    client.post("/api/expenses/bulk", json={"ids": ids, "action": "delete"})
    assert client.get("/api/expenses").json() == []


def test_duplicate(client: TestClient):
    expense = _expense(client, title="Paint", invoice_no="F-1")
    copy = client.post(f"/api/expenses/{expense['id']}/duplicate").json()
    assert copy["title"] == "Paint (copy)"
    assert copy["invoice_no"] is None
    assert copy["amount_incl_cents"] == expense["amount_incl_cents"]


def test_unknown_foreign_key_is_conflict(client: TestClient):
    response = client.post("/api/expenses", json={"title": "X", "category_id": 999})
    assert response.status_code == 409


def test_attachments_roundtrip(client: TestClient, data_dir):
    expense = _expense(client)
    upload = client.post(
        f"/api/expenses/{expense['id']}/attachments",
        files=[("files", ("invoice.pdf", b"%PDF-1.4 test", "application/pdf"))],
        data={"kind": "invoice"},
    )
    assert upload.status_code == 201, upload.text
    attachment = upload.json()[0]
    assert attachment["kind"] == "invoice"
    file_response = client.get(f"/api/attachments/{attachment['id']}/file")
    assert file_response.content == b"%PDF-1.4 test"
    assert file_response.headers["content-disposition"].startswith("inline")

    stored = list((data_dir / "attachments").iterdir())
    assert len(stored) == 1
    client.delete(f"/api/expenses/{expense['id']}")
    assert list((data_dir / "attachments").iterdir()) == []


def test_html_attachment_is_never_inline(client: TestClient):
    expense = _expense(client)
    attachment = client.post(
        f"/api/expenses/{expense['id']}/attachments",
        files=[("files", ("x.html", b"<script>alert(1)</script>", "text/html"))],
    ).json()[0]
    response = client.get(f"/api/attachments/{attachment['id']}/file")
    assert response.headers["content-disposition"].startswith("attachment")
    assert response.headers["content-type"] == "application/octet-stream"


def test_category_depth_limited(client: TestClient, seeded: dict):
    response = client.post(
        "/api/categories", json={"name": "Too deep", "parent_id": seeded["appliances"]["id"]}
    )
    assert response.status_code == 422


def test_audit_log_records_user_and_changes(client: TestClient):
    expense = _expense(client, title="Door")
    client.patch(f"/api/expenses/{expense['id']}", json={"title": "Front door"})
    client.post(
        f"/api/expenses/{expense['id']}/payments", json={"date": "2026-01-01", "amount_cents": 500}
    )
    history = client.get("/api/audit", params={"expense_id": expense["id"]}).json()
    actions = [(h["entity_type"], h["action"]) for h in history["items"]]
    assert actions == [("payment", "create"), ("expense", "update"), ("expense", "create")]
    update = history["items"][1]
    assert update["user"] == "Tester"
    assert update["changes"]["title"] == ["Door", "Front door"]


def test_ingress_guard_blocks_other_clients(client: TestClient, data_dir):
    from app.config import AppConfig, set_config

    set_config(AppConfig(data_dir=data_dir, static_dir=data_dir, dev_mode=False))
    assert client.get("/api/health").status_code == 403
