"""FastAPI application: API routers, ingress guard and the built Vue frontend."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app import audit  # noqa: F401  (registers the change-history hooks)
from app.config import INGRESS_IP, get_config
from app.db import SessionLocal, dispose_engine, init_engine
from app.migrations import run_migrations
from app.routers import backups, catalog, expenses, exports, imports, project, reports
from app.services import backup as backup_service
from app.services.budget import get_settings

log = logging.getLogger("reno_budget")


def startup() -> None:
    cfg = get_config()
    cfg.ensure_dirs()
    run_migrations()
    init_engine(cfg.db_url)
    with SessionLocal() as db:
        get_settings(db)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = get_config()
    options = cfg.load_options()
    logging.basicConfig(
        level=options.python_log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    startup()
    task = None
    if options.auto_backup:
        task = asyncio.create_task(backup_service.nightly_loop(options.backup_keep))
    log.info("Renovation Budget ready (data in %s)", cfg.data_dir)
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    dispose_engine()


app = FastAPI(title="Renovation Budget", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)


@app.middleware("http")
async def ingress_only(request: Request, call_next):
    """Home Assistant ingress connects from one fixed address; refuse everything else."""
    if not get_config().dev_mode:
        client = request.client.host if request.client else None
        if client != INGRESS_IP:
            return PlainTextResponse("Forbidden", status_code=403)
    response = await call_next(request)
    if request.url.path in ("/", "/index.html"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(_request: Request, exc: IntegrityError):
    log.debug("Integrity error: %s", exc)
    return JSONResponse(
        status_code=409,
        content={"detail": "This change conflicts with related data (unknown or still-used item)."},
    )


for router in (
    project.router,
    catalog.categories,
    catalog.rooms,
    catalog.suppliers,
    expenses.router,
    reports.router,
    exports.router,
    imports.router,
    backups.router,
):
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


_static = get_config().static_dir
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="frontend")
else:

    @app.get("/")
    def no_frontend():
        return PlainTextResponse("Frontend not built. Run `npm run build` in frontend/.")
