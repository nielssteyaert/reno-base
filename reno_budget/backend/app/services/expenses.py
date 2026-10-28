"""Expense helpers shared by the expenses router, the importer and the seed script."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app import schemas
from app.models import Expense
from app.money import amounts, vat_from_excl
from app.services import attachments
from app.services.budget import ExpenseFigures, expense_figures, get_settings


def to_out(expense: Expense, figures: ExpenseFigures) -> dict:
    return {
        **{c.key: getattr(expense, c.key) for c in Expense.__table__.columns},
        "status": figures.status,
        "payment_status": figures.payment_status,
        "committed": figures.committed,
        "amount_incl_cents": figures.incl,
        "paid_cents": figures.paid,
        "outstanding_cents": figures.outstanding,
        "attachment_count": len(expense.attachments),
        "payment_count": len(expense.payments),
    }


def to_detail(expense: Expense) -> dict:
    paid = sum(p.amount_cents for p in expense.payments)
    data = to_out(expense, expense_figures(expense, paid))
    data["payments"] = expense.payments
    data["attachments"] = expense.attachments
    return data


def create_expense(db: Session, payload: schemas.ExpenseCreate, user: str | None) -> Expense:
    fields = payload.model_dump(exclude={"amount_cents", "amount_includes_vat", "vat_rate"})
    vat_rate = payload.vat_rate
    if vat_rate is None:
        vat_rate = get_settings(db).default_vat_rate
    excl, vat = amounts(payload.amount_cents, vat_rate, payload.amount_includes_vat)
    expense = Expense(
        **fields,
        vat_rate=vat_rate,
        amount_excl_cents=excl,
        vat_cents=vat,
        created_by=user,
    )
    db.add(expense)
    return expense


def update_expense(expense: Expense, payload: schemas.ExpenseUpdate) -> None:
    data = payload.model_dump(exclude_unset=True)
    amount = data.pop("amount_cents", None)
    includes_vat = data.pop("amount_includes_vat", False)
    vat_rate = data.pop("vat_rate", None)
    for key, value in data.items():
        setattr(expense, key, value)
    set_amount(expense, amount, vat_rate, includes_vat)


def set_amount(
    expense: Expense, amount: int | None, vat_rate: float | None, includes_vat: bool = False
) -> None:
    """Change the amount and/or VAT rate. A rate change alone keeps the amount excl. VAT."""
    if vat_rate is not None:
        expense.vat_rate = vat_rate
    if amount is not None:
        expense.amount_excl_cents, expense.vat_cents = amounts(
            amount, expense.vat_rate, includes_vat
        )
    elif vat_rate is not None:
        expense.vat_cents = vat_from_excl(expense.amount_excl_cents, expense.vat_rate)


def delete_expense(db: Session, expense: Expense) -> list[str]:
    """Delete an expense; returns stored attachment names to remove once committed."""
    stored = [a.stored_name for a in expense.attachments]
    db.delete(expense)
    return stored


def remove_files(stored_names: list[str]) -> None:
    for name in stored_names:
        attachments.remove_file(name)
