"""Dashboard and report data. All figures come from app.services.budget."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.models import AuditLog, Milestone
from app.routers.common import report_filters
from app.services import budget
from app.services.budget import Filters, load_rows

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    rows = load_rows(db)
    today = date.today()
    milestones = db.scalars(select(Milestone)).all()
    open_milestones = [m for m in milestones if budget.milestone_status(m, today) != "done"]
    open_milestones.sort(key=lambda m: (m.planned_end or m.planned_start or date.max, m.id))
    recent = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(10)).all()
    return {
        "summary": budget.project_summary(db, rows),
        "categories": budget.by_category(db, rows),
        "rooms": budget.by_room(db, rows),
        "due": budget.due_list(rows),
        "milestones": [
            {
                "id": m.id,
                "name": m.name,
                "planned_start": m.planned_start,
                "planned_end": m.planned_end,
                "status": budget.milestone_status(m, today),
            }
            for m in open_milestones[:5]
        ],
        "recent": [schemas.AuditOut.model_validate(a) for a in recent],
    }


@router.get("/summary")
def summary(filters: Filters = Depends(report_filters), db: Session = Depends(get_db)):
    return budget.project_summary(db, load_rows(db, filters))


@router.get("/categories")
def categories(filters: Filters = Depends(report_filters), db: Session = Depends(get_db)):
    return budget.by_category(db, load_rows(db, filters))


@router.get("/rooms")
def rooms(filters: Filters = Depends(report_filters), db: Session = Depends(get_db)):
    return budget.by_room(db, load_rows(db, filters))


@router.get("/suppliers")
def suppliers(filters: Filters = Depends(report_filters), db: Session = Depends(get_db)):
    return budget.by_supplier(db, load_rows(db, filters))


@router.get("/monthly")
def monthly(filters: Filters = Depends(report_filters), db: Session = Depends(get_db)):
    rows = load_rows(db, filters)
    settings = budget.get_settings(db)
    return {"budget": settings.total_budget_cents, "months": budget.monthly(db, rows)}


@router.get("/forecast")
def forecast(filters: Filters = Depends(report_filters), db: Session = Depends(get_db)):
    rows = load_rows(db, filters)
    return {
        "summary": budget.project_summary(db, rows),
        "categories": budget.by_category(db, rows),
        "upcoming": budget.upcoming_payments(rows),
    }


@router.get("/milestones")
def milestones(db: Session = Depends(get_db)):
    """Linked-expense totals per milestone, for the timeline."""
    return budget.by_milestone(db, load_rows(db))
