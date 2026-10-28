"""Attachment files on disk, under <data>/attachments."""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import get_config

MAX_BYTES = 25 * 1024 * 1024
_CHUNK = 1024 * 1024
# Only these are shown inline in the browser; everything else is served as a download so an
# uploaded HTML or SVG file can never run script inside Home Assistant.
INLINE_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp"}


def path_for(stored_name: str) -> Path:
    return get_config().attachments_dir / stored_name


async def save_upload(upload: UploadFile) -> tuple[str, int, str]:
    """Stream an upload to disk. Returns (stored_name, size_bytes, mime_type)."""
    original = upload.filename or "file"
    suffix = Path(original).suffix.lower()[:10]
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = path_for(stored_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with target.open("wb") as fh:
            while chunk := await upload.read(_CHUNK):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, f"File is larger than {MAX_BYTES // (1024 * 1024)} MB")
                fh.write(chunk)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    mime = upload.content_type or mimetypes.guess_type(original)[0] or "application/octet-stream"
    return stored_name, size, mime


def remove_file(stored_name: str) -> None:
    path_for(stored_name).unlink(missing_ok=True)
