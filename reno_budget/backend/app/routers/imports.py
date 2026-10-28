"""Expense import from Excel/CSV: template, upload, inspect, preview and commit."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.db import get_db
from app.routers.exports import xlsx_response
from app.services import importer
from app.services.budget import get_settings
from app.services.importer import ImportRequest

router = APIRouter(prefix="/import", tags=["import"])


class InspectRequest(BaseModel):
    token: str
    sheet: str | None = None


@router.get("/fields")
def fields():
    return importer.field_list()


@router.get("/template")
def template(db: Session = Depends(get_db)):
    wb = importer.template_workbook(get_settings(db).currency)
    return xlsx_response(wb, "renovation-import-template.xlsx")


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    token = await importer.save_upload(file)
    try:
        return await run_in_threadpool(importer.inspect, token)
    except HTTPException:
        importer.remove_upload(importer.upload_path(token))
        raise


@router.post("/inspect")
def inspect(payload: InspectRequest):
    return importer.inspect(payload.token, payload.sheet)


@router.post("/preview")
def preview(payload: ImportRequest, db: Session = Depends(get_db)):
    return importer.preview(db, payload)


@router.post("/commit")
def commit(payload: ImportRequest, db: Session = Depends(get_db)):
    return importer.commit(db, payload)
