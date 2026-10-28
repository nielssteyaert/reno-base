"""Project settings, milestones and the change history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.models import AuditLog, Milestone
from app.routers.common import apply_update, get_or_404
from app.services.budget import get_settings, milestone_status

router = APIRouter(tags=["project"])


@router.get("/settings", response_model=schemas.SettingsOut)
def read_settings(db: Session = Depends(get_db)):
    return get_settings(db)


@router.patch("/settings", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsUpdate, db: Session = Depends(get_db)):
    settings = get_settings(db)
    apply_update(settings, payload)
    if settings.default_vat_rate not in settings.vat_rates:
        settings.vat_rates = sorted({*settings.vat_rates, settings.default_vat_rate})
    db.commit()
    return settings


@router.get("/me")
def whoami(db: Session = Depends(get_db)):
    return {"user": db.info.get("user")}


# --- Milestones ---------------------------------------------------------------------------


def _milestone_out(milestone: Milestone) -> dict:
    data = {c.key: getattr(milestone, c.key) for c in Milestone.__table__.columns}
    data["status"] = milestone_status(milestone)
    return data


@router.get("/milestones", response_model=list[schemas.MilestoneOut])
def list_milestones(db: Session = Depends(get_db)):
    milestones = db.scalars(
        select(Milestone).order_by(
            Milestone.sort_order, Milestone.planned_start.is_(None), Milestone.planned_start
        )
    ).all()
    return [_milestone_out(m) for m in milestones]


@router.post("/milestones", response_model=schemas.MilestoneOut, status_code=201)
def create_milestone(payload: schemas.MilestoneCreate, db: Session = Depends(get_db)):
    milestone = Milestone(**payload.model_dump())
    db.add(milestone)
    db.commit()
    return _milestone_out(milestone)


@router.patch("/milestones/{milestone_id}", response_model=schemas.MilestoneOut)
def update_milestone(
    milestone_id: int, payload: schemas.MilestoneUpdate, db: Session = Depends(get_db)
):
    milestone = get_or_404(db, Milestone, milestone_id)
    apply_update(milestone, payload)
    db.commit()
    return _milestone_out(milestone)


@router.delete("/milestones/{milestone_id}", status_code=204)
def delete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Milestone, milestone_id))
    db.commit()
    return Response(status_code=204)


# --- Change history -----------------------------------------------------------------------


@router.get("/audit", response_model=schemas.AuditPage)
def list_audit(
    entity_type: str | None = None,
    entity_id: int | None = None,
    expense_id: int | None = None,
    user: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = select(AuditLog)
    if expense_id is not None:
        query = query.where(AuditLog.expense_id == expense_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    if user:
        query = query.where(AuditLog.user == user)
    if q:
        query = query.where(or_(AuditLog.label.icontains(q), AuditLog.user.icontains(q)))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(AuditLog.id.desc()).limit(min(limit, 500)).offset(offset)
    ).all()
    return {"items": items, "total": total}
