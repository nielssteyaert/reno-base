"""Database models. All money is stored as integer cents."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Stage(enum.StrEnum):
    """Where an expense is in its lifecycle. "Paid" is derived from payments, not stored."""

    ESTIMATE = "estimate"
    QUOTE = "quote"
    ORDERED = "ordered"
    INVOICED = "invoiced"


class AttachmentKind(enum.StrEnum):
    QUOTE = "quote"
    INVOICE = "invoice"
    PHOTO = "photo"
    OTHER = "other"


class PaymentMethod(enum.StrEnum):
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    CASH = "cash"
    OTHER = "other"


class TimestampMixin:
    # Python-side defaults so timestamps follow the container's local time zone (TZ from HA).
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class Settings(TimestampMixin, Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_name: Mapped[str] = mapped_column(String(200), default="My renovation")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    locale: Mapped[str] = mapped_column(String(10), default="nl-BE")
    total_budget_cents: Mapped[int] = mapped_column(Integer, default=0)
    contingency_pct: Mapped[float] = mapped_column(Float, default=10.0)
    vat_rates: Mapped[list[float]] = mapped_column(JSON, default=lambda: [0.0, 6.0, 21.0])
    default_vat_rate: Mapped[float] = mapped_column(Float, default=21.0)
    start_date: Mapped[date | None] = mapped_column(Date)
    target_end_date: Mapped[date | None] = mapped_column(Date)


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    color: Mapped[str | None] = mapped_column(String(9))
    budget_cents: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    parent: Mapped[Category | None] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list[Category]] = relationship(back_populates="parent")


class Room(TimestampMixin, Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    color: Mapped[str | None] = mapped_column(String(9))
    budget_cents: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    contact_person: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(300))
    address: Mapped[str | None] = mapped_column(Text)
    vat_number: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class Milestone(TimestampMixin, Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    planned_start: Mapped[date | None] = mapped_column(Date)
    planned_end: Mapped[date | None] = mapped_column(Date)
    actual_start: Mapped[date | None] = mapped_column(Date)
    actual_end: Mapped[date | None] = mapped_column(Date)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey("rooms.id", ondelete="SET NULL"), index=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), index=True
    )
    milestone_id: Mapped[int | None] = mapped_column(
        ForeignKey("milestones.id", ondelete="SET NULL"), index=True
    )
    stage: Mapped[str] = mapped_column(String(20), default=Stage.ESTIMATE.value)
    amount_excl_cents: Mapped[int] = mapped_column(Integer, default=0)
    vat_rate: Mapped[float] = mapped_column(Float, default=21.0)
    vat_cents: Mapped[int] = mapped_column(Integer, default=0)
    expense_date: Mapped[date | None] = mapped_column(Date, index=True)
    due_date: Mapped[date | None] = mapped_column(Date)
    quote_ref: Mapped[str | None] = mapped_column(String(100))
    invoice_no: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(200))

    category: Mapped[Category | None] = relationship()
    room: Mapped[Room | None] = relationship()
    supplier: Mapped[Supplier | None] = relationship()
    milestone: Mapped[Milestone | None] = relationship()
    payments: Mapped[list[Payment]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", order_by="Payment.date"
    )
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", order_by="Attachment.id"
    )

    @property
    def amount_incl_cents(self) -> int:
        return self.amount_excl_cents + self.vat_cents


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(20), default=PaymentMethod.BANK_TRANSFER.value)
    reference: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)

    expense: Mapped[Expense] = relationship(back_populates="payments")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20), default=AttachmentKind.OTHER.value)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    uploaded_by: Mapped[str | None] = mapped_column(String(200))

    expense: Mapped[Expense] = relationship(back_populates="attachments")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    user: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    # Payments and attachments also carry their expense, so its history shows them.
    expense_id: Mapped[int | None] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(10))
    label: Mapped[str | None] = mapped_column(String(255))
    changes: Mapped[dict] = mapped_column(JSON, default=dict)
