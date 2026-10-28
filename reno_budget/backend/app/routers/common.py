"""Shared helpers for routers: 404 lookups, partial updates and a generic CRUD router.

No `from __future__ import annotations` here: FastAPI must see the real schema classes
in the generated endpoint signatures.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.budget import Filters


def get_or_404(db: Session, model: type, entity_id: int) -> Any:
    entity = db.get(model, entity_id)
    if entity is None:
        raise HTTPException(404, f"{model.__name__} {entity_id} not found")
    return entity


def apply_update(entity: Any, update: BaseModel) -> None:
    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(entity, key, value)


def report_filters(
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: list[int] = Query(default_factory=list),
    room_id: list[int] = Query(default_factory=list),
    supplier_id: list[int] = Query(default_factory=list),
    milestone_id: list[int] = Query(default_factory=list),
    status: list[str] = Query(default_factory=list),
    q: str | None = None,
) -> Filters:
    return Filters(
        date_from=date_from,
        date_to=date_to,
        category_ids=category_id,
        room_ids=room_id,
        supplier_ids=supplier_id,
        milestone_ids=milestone_id,
        statuses=status,
        q=q,
    )


def crud_router(
    *,
    model: type,
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    out_schema: type[BaseModel],
    prefix: str,
    order_by: tuple = (),
    validate: Callable[[Session, Any], None] | None = None,
) -> APIRouter:
    """List/create/get/update/delete endpoints for a simple model."""
    router = APIRouter(prefix=prefix, tags=[prefix.strip("/")])

    @router.get("", response_model=list[out_schema])
    def list_items(db: Session = Depends(get_db)):
        return db.scalars(select(model).order_by(*order_by)).all()

    @router.post("", response_model=out_schema, status_code=201)
    def create_item(payload: create_schema, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        entity = model(**payload.model_dump())
        if validate:
            validate(db, entity)
        db.add(entity)
        db.commit()
        return entity

    @router.get("/{entity_id}", response_model=out_schema)
    def get_item(entity_id: int, db: Session = Depends(get_db)):
        return get_or_404(db, model, entity_id)

    @router.patch("/{entity_id}", response_model=out_schema)
    def update_item(entity_id: int, payload: update_schema, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        entity = get_or_404(db, model, entity_id)
        apply_update(entity, payload)
        if validate:
            validate(db, entity)
        db.commit()
        return entity

    @router.delete("/{entity_id}", status_code=204)
    def delete_item(entity_id: int, db: Session = Depends(get_db)):
        db.delete(get_or_404(db, model, entity_id))
        db.commit()
        return Response(status_code=204)

    return router
