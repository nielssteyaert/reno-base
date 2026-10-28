from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient


def _make_data(client: TestClient) -> int:
    expense = client.post("/api/expenses", json={"title": "Kitchen", "amount_cents": 1_000}).json()
    client.post(
        f"/api/expenses/{expense['id']}/attachments",
        files=[("files", ("quote.pdf", b"%PDF quote", "application/pdf"))],
    )
    return expense["id"]


def test_backup_restore_roundtrip(client: TestClient, data_dir):
    expense_id = _make_data(client)
    name = client.post("/api/backups").json()["name"]

    listed = client.get("/api/backups").json()
    assert listed[0]["name"] == name
    assert listed[0]["attachments"] == 1
    assert listed[0]["reason"] == "manual"

    # Change everything after the backup, then restore.
    client.delete(f"/api/expenses/{expense_id}")
    client.post("/api/expenses", json={"title": "After backup", "amount_cents": 5})
    assert [e["title"] for e in client.get("/api/expenses").json()] == ["After backup"]

    result = client.post(f"/api/backups/{name}/restore").json()
    assert result["safety_backup"].endswith("-pre-restore.zip")
    expenses = client.get("/api/expenses").json()
    assert [e["title"] for e in expenses] == ["Kitchen"]
    detail = client.get(f"/api/expenses/{expense_id}").json()
    file_response = client.get(f"/api/attachments/{detail['attachments'][0]['id']}/file")
    assert file_response.content == b"%PDF quote"


def test_download_and_upload_restore(client: TestClient):
    _make_data(client)
    name = client.post("/api/backups").json()["name"]
    blob = client.get(f"/api/backups/{name}").content
    client.post("/api/expenses", json={"title": "Extra", "amount_cents": 5})

    response = client.post(
        "/api/backups/upload-restore", files={"file": ("backup.zip", blob, "application/zip")}
    )
    assert response.status_code == 200, response.text
    assert [e["title"] for e in client.get("/api/expenses").json()] == ["Kitchen"]


def test_restore_rejects_garbage(client: TestClient):
    response = client.post(
        "/api/backups/upload-restore", files={"file": ("x.zip", b"not a zip", "application/zip")}
    )
    assert response.status_code == 422

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("manifest.json", "{}")
        zf.writestr("reno.db", b"garbage")
    response = client.post(
        "/api/backups/upload-restore",
        files={"file": ("x.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 422


def test_backup_names_are_validated(client: TestClient):
    assert client.get("/api/backups/..%2Freno.db").status_code in (404, 422)
    assert client.delete("/api/backups/evil.zip").status_code == 422


def test_prune_keeps_newest_auto_backups(client: TestClient, data_dir):
    from app.services import backup

    for stamp in ("20260101-030000", "20260102-030000", "20260103-030000"):
        (data_dir / "backups" / f"reno-backup-{stamp}-auto.zip").write_bytes(b"x")
    (data_dir / "backups" / "reno-backup-20250101-030000-manual.zip").write_bytes(b"x")
    backup.prune(keep=2)
    remaining = sorted(p.name for p in (data_dir / "backups").iterdir())
    assert remaining == [
        "reno-backup-20250101-030000-manual.zip",
        "reno-backup-20260102-030000-auto.zip",
        "reno-backup-20260103-030000-auto.zip",
    ]
