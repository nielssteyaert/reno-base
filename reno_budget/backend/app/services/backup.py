"""Backups: a zip holding a consistent SQLite snapshot, all attachments and a manifest.

Restoring first takes a safety backup of the current state, then swaps in the database and
attachments from the zip and runs migrations, so a backup from an older version still works.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from app.config import get_config
from app.db import dispose_engine, init_engine
from app.migrations import current_revision, run_migrations

log = logging.getLogger(__name__)

APP_VERSION = os.environ.get("RENO_VERSION", "dev")
NAME_RE = re.compile(r"^reno-backup-\d{8}-\d{6}-[a-z-]+\.zip$")
NIGHTLY_HOUR = 3
_lock = threading.Lock()


class BackupError(ValueError):
    pass


def _snapshot_db(target: Path) -> None:
    source = sqlite3.connect(get_config().db_path)
    dest = sqlite3.connect(target)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()


def create_backup(reason: str = "manual") -> Path:
    cfg = get_config()
    cfg.backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = cfg.backups_dir / f"reno-backup-{stamp}-{reason}.zip"
    with _lock, tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / "reno.db"
        _snapshot_db(db_copy)
        attachments = sorted(p for p in cfg.attachments_dir.glob("*") if p.is_file())
        manifest = {
            "app_version": APP_VERSION,
            "schema_revision": current_revision(f"sqlite:///{db_copy}"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "attachments": len(attachments),
        }
        partial = target.with_suffix(".partial")
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.write(db_copy, "reno.db")
            for path in attachments:
                zf.write(path, f"attachments/{path.name}")
        partial.rename(target)
    log.info("Created backup %s", target.name)
    return target


def list_backups() -> list[dict]:
    result = []
    for path in sorted(get_config().backups_dir.glob("reno-backup-*.zip"), reverse=True):
        manifest = {}
        try:
            with zipfile.ZipFile(path) as zf:
                manifest = json.loads(zf.read("manifest.json"))
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError):
            pass
        result.append(
            {
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "created_at": manifest.get("created_at"),
                "reason": manifest.get("reason"),
                "app_version": manifest.get("app_version"),
                "attachments": manifest.get("attachments"),
            }
        )
    return result


def backup_path(name: str) -> Path:
    if not NAME_RE.match(name):
        raise BackupError("Invalid backup name")
    path = get_config().backups_dir / name
    if not path.exists():
        raise FileNotFoundError(name)
    return path


def prune(keep: int, reason: str = "auto") -> None:
    autos = [
        p
        for p in sorted(get_config().backups_dir.glob(f"reno-backup-*-{reason}.zip"), reverse=True)
    ]
    for old in autos[keep:]:
        old.unlink(missing_ok=True)
        log.info("Removed old backup %s", old.name)


def _validate(zip_path: Path, workdir: Path) -> Path:
    """Extract and sanity-check the database from a backup zip; returns its path."""
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise BackupError("Not a valid backup file") from exc
    with zf:
        names = set(zf.namelist())
        if "manifest.json" not in names or "reno.db" not in names:
            raise BackupError("Backup is missing manifest.json or reno.db")
        db_file = workdir / "reno.db"
        db_file.write_bytes(zf.read("reno.db"))
        attachments_dir = workdir / "attachments"
        attachments_dir.mkdir()
        for name in names:
            if not name.startswith("attachments/") or name.endswith("/"):
                continue
            safe = Path(name).name
            if not safe or safe.startswith("."):
                continue
            (attachments_dir / safe).write_bytes(zf.read(name))
    conn = sqlite3.connect(db_file)
    try:
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.DatabaseError as exc:
        raise BackupError("The database in this backup is unreadable") from exc
    finally:
        conn.close()
    if not ok or "expenses" not in tables:
        raise BackupError(
            "The database in this backup is damaged or not a Renovation Budget database"
        )
    return db_file


def restore(zip_path: Path) -> Path:
    """Replace all data with the backup's contents. Returns the safety backup's path."""
    cfg = get_config()
    with tempfile.TemporaryDirectory(dir=cfg.data_dir) as tmp:
        workdir = Path(tmp)
        new_db = _validate(zip_path, workdir)
        safety = create_backup("pre-restore")
        with _lock:
            dispose_engine()
            for suffix in ("", "-wal", "-shm"):
                Path(f"{cfg.db_path}{suffix}").unlink(missing_ok=True)
            shutil.move(new_db, cfg.db_path)
            old_attachments = cfg.attachments_dir.with_name("attachments.old")
            shutil.rmtree(old_attachments, ignore_errors=True)
            if cfg.attachments_dir.exists():
                cfg.attachments_dir.rename(old_attachments)
            shutil.move(workdir / "attachments", cfg.attachments_dir)
            shutil.rmtree(old_attachments, ignore_errors=True)
            run_migrations()
            init_engine(cfg.db_url)
    log.info("Restored backup %s (safety backup %s)", zip_path.name, safety.name)
    return safety


def _seconds_until_next_run(now: datetime) -> float:
    next_run = now.replace(hour=NIGHTLY_HOUR, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


async def nightly_loop(keep: int) -> None:
    while True:
        await asyncio.sleep(_seconds_until_next_run(datetime.now()))
        try:
            await asyncio.to_thread(create_backup, "auto")
            await asyncio.to_thread(prune, keep)
        except Exception:
            log.exception("Nightly backup failed")
