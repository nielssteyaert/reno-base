"""Excel downloads: the full workbook, single reports and a selection of expenses."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers.common import report_filters
from app.services import excel_export
from app.services.budget import Filters

router = APIRouter(prefix="/export", tags=["export"])


class ExpenseSelection(BaseModel):
    ids: list[int]


def xlsx_response(wb: Workbook, filename: str) -> StreamingResponse:
    return StreamingResponse(
        excel_export.to_stream(wb),
        media_type=excel_export.XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/workbook")
def export_workbook(filters: Filters = Depends(report_filters), db: Session = Depends(get_db)):
    wb = excel_export.full_workbook(db, filters)
    return xlsx_response(wb, f"renovation-budget-{date.today().isoformat()}.xlsx")


@router.get("/report/{name}")
def export_report(
    name: str, filters: Filters = Depends(report_filters), db: Session = Depends(get_db)
):
    if name not in excel_export.REPORTS:
        raise HTTPException(404, f"Unknown report '{name}'")
    wb = excel_export.report_workbook(db, name, filters)
    return xlsx_response(wb, f"renovation-{name}-{date.today().isoformat()}.xlsx")


@router.post("/expenses")
def export_expenses(payload: ExpenseSelection, db: Session = Depends(get_db)):
    wb = excel_export.expenses_workbook(db, payload.ids)
    return xlsx_response(wb, f"renovation-expenses-{date.today().isoformat()}.xlsx")
