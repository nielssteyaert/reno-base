"""Change history: every insert, update and delete of a tracked model becomes an AuditLog row.

The acting user is taken from ``session.info["user"]``, which ``app.db.get_db`` fills from
the Home Assistant ingress headers.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import event, insert, inspect
from sqlalchemy.orm import Session

from app.models import (
    Attachment,
    AuditLog,
    Category,
    Expense,
    Milestone,
    Payment,
    Room,
    Settings,
    Supplier,
)

TRACKED: dict[type, str] = {
    Settings: "settings",
    Category: "category",
    Room: "room",
    Supplier: "supplier",
    Milestone: "milestone",
    Expense: "expense",
    Payment: "payment",
    Attachment: "attachment",
}

_IGNORED_FIELDS = {"created_at", "updated_at", "uploaded_at"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _columns(obj: Any) -> list[str]:
    return [c.key for c in inspect(obj).mapper.column_attrs if c.key not in _IGNORED_FIELDS]


def _snapshot(obj: Any) -> dict[str, list[Any]]:
    return {key: [None, _jsonable(getattr(obj, key))] for key in _columns(obj) if key != "id"}


def _diff(obj: Any) -> dict[str, list[Any]]:
    state = inspect(obj)
    changes: dict[str, list[Any]] = {}
    for key in _columns(obj):
        history = state.attrs[key].history
        if not history.has_changes():
            continue
        old = history.deleted[0] if history.deleted else None
        new = history.added[0] if history.added else None
        if old != new:
            changes[key] = [_jsonable(old), _jsonable(new)]
    return changes


def _label(obj: Any) -> str | None:
    for attr in ("title", "name", "project_name", "original_name"):
        value = getattr(obj, attr, None)
        if value:
            return str(value)[:255]
    if isinstance(obj, Payment):
        return f"Payment {obj.amount_cents / 100:.2f}"
    return None


def _expense_id(obj: Any) -> int | None:
    if isinstance(obj, Expense):
        return obj.id
    if isinstance(obj, (Payment, Attachment)):
        return obj.expense_id
    return None


@event.listens_for(Session, "before_flush")
def _collect(session: Session, _flush_context, _instances) -> None:
    pending = session.info.setdefault("audit_pending", [])
    for obj in session.new:
        if type(obj) in TRACKED:
            pending.append(("create", obj, None))
    for obj in session.dirty:
        if type(obj) in TRACKED and session.is_modified(obj, include_collections=False):
            changes = _diff(obj)
            if changes:
                pending.append(("update", obj, changes))
    for obj in session.deleted:
        if type(obj) in TRACKED:
            pending.append(("delete", obj, _snapshot(obj)))


@event.listens_for(Session, "after_flush")
def _write(session: Session, _flush_context) -> None:
    pending = session.info.pop("audit_pending", [])
    if not pending:
        return
    user = session.info.get("user", "system")
    rows = []
    for action, obj, changes in pending:
        if action == "create":
            changes = _snapshot(obj)
        rows.append(
            {
                "ts": datetime.now(),
                "user": user,
                "entity_type": TRACKED[type(obj)],
                "entity_id": obj.id,
                "expense_id": _expense_id(obj),
                "action": action,
                "label": _label(obj),
                "changes": changes or {},
            }
        )
    session.connection().execute(insert(AuditLog), rows)
