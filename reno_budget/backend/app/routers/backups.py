"""Create, download, restore and delete backups."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.config import get_config
from app.services import backup

router = APIRouter(prefix="/backups", tags=["backups"])


def _path(name: str) -> Path:
    try:
        return backup.backup_path(name)
    except backup.BackupError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, "Backup not found") from exc


@router.get("")
def list_backups():
    return backup.list_backups()


@router.post("", status_code=201)
async def create_backup():
    path = await run_in_threadpool(backup.create_backup, "manual")
    return {"name": path.name}


@router.get("/{name}")
def download_backup(name: str):
    return FileResponse(_path(name), media_type="application/zip", filename=name)


@router.delete("/{name}", status_code=204)
def delete_backup(name: str):
    _path(name).unlink()
    return Response(status_code=204)


@router.post("/{name}/restore")
async def restore_backup(name: str):
    try:
        safety = await run_in_threadpool(backup.restore, _path(name))
    except backup.BackupError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"restored": name, "safety_backup": safety.name}


@router.post("/upload-restore")
async def upload_and_restore(file: UploadFile = File(...)):
    """Restore from a backup zip uploaded from the user's computer."""
    with tempfile.NamedTemporaryFile(dir=get_config().data_dir, suffix=".zip", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        safety = await run_in_threadpool(backup.restore, tmp_path)
    except backup.BackupError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"restored": file.filename, "safety_backup": safety.name}
