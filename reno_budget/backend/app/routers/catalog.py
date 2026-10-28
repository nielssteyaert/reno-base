"""Categories, rooms and suppliers."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.models import Category, Room, Supplier
from app.routers.common import crud_router


def _validate_category(db: Session, category: Category) -> None:
    """Categories are at most two levels deep: a parent cannot itself have a parent."""
    if category.parent_id is None:
        return
    if category.id is not None and category.parent_id == category.id:
        raise HTTPException(422, "A category cannot be its own parent")
    parent = db.get(Category, category.parent_id)
    if parent is None:
        raise HTTPException(422, "Parent category not found")
    if parent.parent_id is not None:
        raise HTTPException(422, "Subcategories cannot have subcategories")
    if category.id is not None and category.children:
        raise HTTPException(422, "A category with subcategories cannot become a subcategory")


categories = crud_router(
    model=Category,
    create_schema=schemas.CategoryCreate,
    update_schema=schemas.CategoryUpdate,
    out_schema=schemas.CategoryOut,
    prefix="/categories",
    order_by=(Category.sort_order, Category.name),
    validate=_validate_category,
)

rooms = crud_router(
    model=Room,
    create_schema=schemas.RoomCreate,
    update_schema=schemas.RoomUpdate,
    out_schema=schemas.RoomOut,
    prefix="/rooms",
    order_by=(Room.sort_order, Room.name),
)

suppliers = crud_router(
    model=Supplier,
    create_schema=schemas.SupplierCreate,
    update_schema=schemas.SupplierUpdate,
    out_schema=schemas.SupplierOut,
    prefix="/suppliers",
    order_by=(Supplier.name,),
)
