"""Request and response models for the REST API."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AttachmentKind, PaymentMethod, Stage

Color = str | None
Status = Literal["estimate", "quote", "ordered", "invoiced", "paid"]
PaymentStatus = Literal["unpaid", "partial", "paid"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Settings -----------------------------------------------------------------------------


class SettingsOut(ORM):
    project_name: str
    currency: str
    locale: str
    total_budget_cents: int
    contingency_pct: float
    vat_rates: list[float]
    default_vat_rate: float
    start_date: Date | None
    target_end_date: Date | None


class SettingsUpdate(BaseModel):
    project_name: str | None = Field(None, min_length=1, max_length=200)
    currency: str | None = Field(None, min_length=3, max_length=3)
    locale: str | None = Field(None, max_length=10)
    total_budget_cents: int | None = Field(None, ge=0)
    contingency_pct: float | None = Field(None, ge=0, le=100)
    vat_rates: list[float] | None = None
    default_vat_rate: float | None = Field(None, ge=0, le=100)
    start_date: Date | None = None
    target_end_date: Date | None = None

    @field_validator("vat_rates")
    @classmethod
    def _rates(cls, rates: list[float] | None) -> list[float] | None:
        if rates is None:
            return None
        if not rates or any(r < 0 or r > 100 for r in rates):
            raise ValueError("VAT rates must be between 0 and 100")
        return sorted(set(rates))


# --- Categories, rooms, suppliers ---------------------------------------------------------


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: int | None = None
    color: Color = None
    budget_cents: int | None = Field(None, ge=0)
    sort_order: int = 0
    archived: bool = False
    notes: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    parent_id: int | None = None
    color: Color = None
    budget_cents: int | None = Field(None, ge=0)
    sort_order: int | None = None
    archived: bool | None = None
    notes: str | None = None


class CategoryOut(ORM):
    id: int
    name: str
    parent_id: int | None
    color: str | None
    budget_cents: int | None
    sort_order: int
    archived: bool
    notes: str | None


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    color: Color = None
    budget_cents: int | None = Field(None, ge=0)
    sort_order: int = 0
    archived: bool = False
    notes: str | None = None


class RoomUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    color: Color = None
    budget_cents: int | None = Field(None, ge=0)
    sort_order: int | None = None
    archived: bool | None = None
    notes: str | None = None


class RoomOut(ORM):
    id: int
    name: str
    color: str | None
    budget_cents: int | None
    sort_order: int
    archived: bool
    notes: str | None


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    vat_number: str | None = None
    notes: str | None = None
    archived: bool = False


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    vat_number: str | None = None
    notes: str | None = None
    archived: bool | None = None


class SupplierOut(ORM):
    id: int
    name: str
    contact_person: str | None
    phone: str | None
    email: str | None
    website: str | None
    address: str | None
    vat_number: str | None
    notes: str | None
    archived: bool


# --- Milestones ---------------------------------------------------------------------------


class MilestoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    room_id: int | None = None
    planned_start: Date | None = None
    planned_end: Date | None = None
    actual_start: Date | None = None
    actual_end: Date | None = None
    sort_order: int = 0
    notes: str | None = None


class MilestoneUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    room_id: int | None = None
    planned_start: Date | None = None
    planned_end: Date | None = None
    actual_start: Date | None = None
    actual_end: Date | None = None
    sort_order: int | None = None
    notes: str | None = None


class MilestoneOut(ORM):
    id: int
    name: str
    room_id: int | None
    planned_start: Date | None
    planned_end: Date | None
    actual_start: Date | None
    actual_end: Date | None
    sort_order: int
    notes: str | None
    status: Literal["planned", "in_progress", "done", "late"]


# --- Payments and attachments -------------------------------------------------------------


class PaymentCreate(BaseModel):
    date: Date
    amount_cents: int = Field(gt=0)
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    reference: str | None = None
    note: str | None = None


class PaymentUpdate(BaseModel):
    date: Date | None = None
    amount_cents: int | None = Field(None, gt=0)
    method: PaymentMethod | None = None
    reference: str | None = None
    note: str | None = None


class PaymentOut(ORM):
    id: int
    expense_id: int
    date: Date
    amount_cents: int
    method: str
    reference: str | None
    note: str | None


class AttachmentOut(ORM):
    id: int
    expense_id: int
    kind: str
    original_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    uploaded_by: str | None


class AttachmentUpdate(BaseModel):
    kind: AttachmentKind | None = None
    original_name: str | None = Field(None, min_length=1, max_length=255)


# --- Expenses -----------------------------------------------------------------------------


class ExpenseFields(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    room_id: int | None = None
    supplier_id: int | None = None
    milestone_id: int | None = None
    stage: Stage = Stage.ESTIMATE
    expense_date: Date | None = None
    due_date: Date | None = None
    quote_ref: str | None = None
    invoice_no: str | None = None
    notes: str | None = None


class ExpenseCreate(ExpenseFields):
    amount_cents: int = Field(0, ge=0)
    amount_includes_vat: bool = False
    vat_rate: float | None = Field(None, ge=0, le=100)


class ExpenseUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    room_id: int | None = None
    supplier_id: int | None = None
    milestone_id: int | None = None
    stage: Stage | None = None
    expense_date: Date | None = None
    due_date: Date | None = None
    quote_ref: str | None = None
    invoice_no: str | None = None
    notes: str | None = None
    amount_cents: int | None = Field(None, ge=0)
    amount_includes_vat: bool = False
    vat_rate: float | None = Field(None, ge=0, le=100)


class ExpenseOut(ORM):
    id: int
    title: str
    description: str | None
    category_id: int | None
    room_id: int | None
    supplier_id: int | None
    milestone_id: int | None
    stage: str
    status: Status
    payment_status: PaymentStatus
    committed: bool
    amount_excl_cents: int
    vat_rate: float
    vat_cents: int
    amount_incl_cents: int
    paid_cents: int
    outstanding_cents: int
    expense_date: Date | None
    due_date: Date | None
    quote_ref: str | None
    invoice_no: str | None
    notes: str | None
    attachment_count: int
    payment_count: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None


class ExpenseDetail(ExpenseOut):
    payments: list[PaymentOut]
    attachments: list[AttachmentOut]


class ExpenseBulkChanges(BaseModel):
    category_id: int | None = None
    room_id: int | None = None
    supplier_id: int | None = None
    milestone_id: int | None = None
    stage: Stage | None = None
    vat_rate: float | None = Field(None, ge=0, le=100)


class ExpenseBulk(BaseModel):
    ids: list[int] = Field(min_length=1)
    action: Literal["update", "delete"]
    changes: ExpenseBulkChanges | None = None


class BulkResult(BaseModel):
    affected: int


# --- Audit --------------------------------------------------------------------------------


class AuditOut(ORM):
    id: int
    ts: datetime
    user: str
    entity_type: str
    entity_id: int
    expense_id: int | None
    action: str
    label: str | None
    changes: dict


class AuditPage(BaseModel):
    items: list[AuditOut]
    total: int
