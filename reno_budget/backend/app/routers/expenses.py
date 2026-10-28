"""Expenses, their payments and their attachments."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.models import Attachment, AttachmentKind, Expense, Payment, PaymentMethod
from app.routers.common import apply_update, get_or_404, report_filters
from app.services import attachments as files
from app.services import expenses as service
from app.services.budget import Filters, load_rows

router = APIRouter(tags=["expenses"])


@router.get("/expenses", response_model=list[schemas.ExpenseOut])
def list_expenses(filters: Filters = Depends(report_filters), db: Session = Depends(get_db)):
    return [service.to_out(row.expense, row.figures) for row in load_rows(db, filters)]


@router.post("/expenses", response_model=schemas.ExpenseDetail, status_code=201)
def create_expense(payload: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    expense = service.create_expense(db, payload, db.info.get("user"))
    db.commit()
    return service.to_detail(expense)


@router.get("/expenses/{expense_id}", response_model=schemas.ExpenseDetail)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    return service.to_detail(get_or_404(db, Expense, expense_id))


@router.patch("/expenses/{expense_id}", response_model=schemas.ExpenseDetail)
def update_expense(expense_id: int, payload: schemas.ExpenseUpdate, db: Session = Depends(get_db)):
    expense = get_or_404(db, Expense, expense_id)
    service.update_expense(expense, payload)
    db.commit()
    return service.to_detail(expense)


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    stored = service.delete_expense(db, get_or_404(db, Expense, expense_id))
    db.commit()
    service.remove_files(stored)
    return Response(status_code=204)


@router.post(
    "/expenses/{expense_id}/duplicate", response_model=schemas.ExpenseDetail, status_code=201
)
def duplicate_expense(expense_id: int, db: Session = Depends(get_db)):
    source = get_or_404(db, Expense, expense_id)
    skip = {"id", "created_at", "updated_at", "created_by", "invoice_no"}
    copy = Expense(
        **{c.key: getattr(source, c.key) for c in Expense.__table__.columns if c.key not in skip},
        created_by=db.info.get("user"),
    )
    copy.title = f"{source.title} (copy)"[:200]
    db.add(copy)
    db.commit()
    return service.to_detail(copy)


@router.post("/expenses/bulk", response_model=schemas.BulkResult)
def bulk_expenses(payload: schemas.ExpenseBulk, db: Session = Depends(get_db)):
    expenses = db.scalars(select(Expense).where(Expense.id.in_(payload.ids))).all()
    if payload.action == "delete":
        stored: list[str] = []
        for expense in expenses:
            stored += service.delete_expense(db, expense)
        db.commit()
        service.remove_files(stored)
        return {"affected": len(expenses)}

    if payload.changes is None:
        raise HTTPException(422, "No changes given")
    changes = payload.changes.model_dump(exclude_unset=True)
    vat_rate = changes.pop("vat_rate", None)
    for expense in expenses:
        for key, value in changes.items():
            setattr(expense, key, value)
        if vat_rate is not None:
            service.set_amount(expense, None, vat_rate)
    db.commit()
    return {"affected": len(expenses)}


# --- Payments -----------------------------------------------------------------------------


class PayRemaining(BaseModel):
    date: date
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    reference: str | None = None


@router.post("/expenses/{expense_id}/payments", response_model=schemas.PaymentOut, status_code=201)
def add_payment(expense_id: int, payload: schemas.PaymentCreate, db: Session = Depends(get_db)):
    get_or_404(db, Expense, expense_id)
    payment = Payment(expense_id=expense_id, **payload.model_dump())
    db.add(payment)
    db.commit()
    return payment


@router.post(
    "/expenses/{expense_id}/pay-remaining", response_model=schemas.PaymentOut, status_code=201
)
def pay_remaining(expense_id: int, payload: PayRemaining, db: Session = Depends(get_db)):
    """Record one payment for whatever is still open on the expense."""
    expense = get_or_404(db, Expense, expense_id)
    remaining = expense.amount_incl_cents - sum(p.amount_cents for p in expense.payments)
    if remaining <= 0:
        raise HTTPException(409, "Nothing left to pay on this expense")
    payment = Payment(
        expense_id=expense_id,
        date=payload.date,
        amount_cents=remaining,
        method=payload.method,
        reference=payload.reference,
    )
    db.add(payment)
    db.commit()
    return payment


@router.patch("/payments/{payment_id}", response_model=schemas.PaymentOut)
def update_payment(payment_id: int, payload: schemas.PaymentUpdate, db: Session = Depends(get_db)):
    payment = get_or_404(db, Payment, payment_id)
    apply_update(payment, payload)
    db.commit()
    return payment


@router.delete("/payments/{payment_id}", status_code=204)
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Payment, payment_id))
    db.commit()
    return Response(status_code=204)


# --- Attachments --------------------------------------------------------------------------


@router.post(
    "/expenses/{expense_id}/attachments",
    response_model=list[schemas.AttachmentOut],
    status_code=201,
)
async def upload_attachments(
    expense_id: int,
    files_: list[UploadFile] = File(alias="files"),
    kind: AttachmentKind = Form(AttachmentKind.OTHER),
    db: Session = Depends(get_db),
):
    get_or_404(db, Expense, expense_id)
    created = []
    stored_names = []
    try:
        for upload in files_:
            stored_name, size, mime = await files.save_upload(upload)
            stored_names.append(stored_name)
            attachment = Attachment(
                expense_id=expense_id,
                kind=kind,
                original_name=(upload.filename or "file")[:255],
                stored_name=stored_name,
                mime_type=mime,
                size_bytes=size,
                uploaded_by=db.info.get("user"),
            )
            db.add(attachment)
            created.append(attachment)
        db.commit()
    except BaseException:
        db.rollback()
        for name in stored_names:
            files.remove_file(name)
        raise
    return created


@router.get("/attachments/{attachment_id}/file")
def download_attachment(attachment_id: int, download: bool = False, db: Session = Depends(get_db)):
    attachment = get_or_404(db, Attachment, attachment_id)
    path = files.path_for(attachment.stored_name)
    if not path.exists():
        raise HTTPException(404, "File is missing from storage")
    inline = not download and attachment.mime_type in files.INLINE_TYPES
    return FileResponse(
        path,
        media_type=attachment.mime_type if inline else "application/octet-stream",
        filename=attachment.original_name,
        content_disposition_type="inline" if inline else "attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.patch("/attachments/{attachment_id}", response_model=schemas.AttachmentOut)
def update_attachment(
    attachment_id: int, payload: schemas.AttachmentUpdate, db: Session = Depends(get_db)
):
    attachment = get_or_404(db, Attachment, attachment_id)
    apply_update(attachment, payload)
    db.commit()
    return attachment


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):
    attachment = get_or_404(db, Attachment, attachment_id)
    stored = attachment.stored_name
    db.delete(attachment)
    db.commit()
    files.remove_file(stored)
    return Response(status_code=204)
