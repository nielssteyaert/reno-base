"""Fill an empty data directory with a realistic demo renovation, for development and screenshots.

Usage (from backend/):  RENO_DATA_DIR=.devdata .venv/bin/python -m scripts.seed_demo
"""

from __future__ import annotations

import sys
from datetime import date

from sqlalchemy import func, select

from app import (
    audit,  # noqa: F401  (record the demo data in the change history)
    schemas,
)
from app.db import SessionLocal
from app.main import startup
from app.models import Category, Expense, Milestone, Payment, Room, Supplier
from app.services.budget import get_settings
from app.services.expenses import create_expense

CATEGORIES = {
    "Structural work": (2_500_000, ["Demolition", "Masonry"]),
    "Roof & insulation": (1_800_000, []),
    "Electrical": (900_000, []),
    "Plumbing & heating": (1_600_000, ["Heat pump"]),
    "Kitchen": (2_200_000, ["Cabinets", "Appliances", "Worktop"]),
    "Bathroom": (1_400_000, ["Tiles", "Sanitary"]),
    "Flooring": (700_000, []),
    "Painting & finishing": (500_000, []),
}
ROOMS = {
    "Kitchen": ("#eb6834", 2_600_000),
    "Bathroom": ("#1baf7a", 1_600_000),
    "Living room": ("#2a78d6", 1_200_000),
    "Bedrooms": ("#6250d6", 800_000),
    "Attic": ("#eda100", 1_500_000),
    "Whole house": (None, None),
}
SUPPLIERS = [
    ("Bouwbedrijf Peeters", "Jan Peeters", "+32 470 12 34 56"),
    ("Elektro Claes", "Sofie Claes", "+32 471 22 33 44"),
    ("Sanitair Janssens", "Koen Janssens", "+32 472 98 76 54"),
    ("Keukens De Smet", "An De Smet", "+32 473 11 22 33"),
    ("Dakwerken Maes", "Tom Maes", "+32 474 55 66 77"),
    ("Brico", None, None),
]
MILESTONES = [
    ("Demolition", "Whole house", (2026, 1, 12), (2026, 1, 30), (2026, 1, 12), (2026, 2, 6)),
    ("Roof renovation", "Attic", (2026, 2, 2), (2026, 3, 13), (2026, 2, 9), (2026, 3, 20)),
    (
        "Electrical & plumbing rough-in",
        "Whole house",
        (2026, 3, 2),
        (2026, 4, 17),
        (2026, 3, 9),
        None,
    ),
    ("Plastering", "Whole house", (2026, 4, 20), (2026, 5, 22), None, None),
    ("Kitchen installation", "Kitchen", (2026, 6, 1), (2026, 6, 19), None, None),
    ("Bathroom", "Bathroom", (2026, 6, 8), (2026, 7, 10), None, None),
    ("Floors & painting", "Whole house", (2026, 7, 13), (2026, 8, 28), None, None),
]

# title, category, room, supplier, milestone, stage, amount incl VAT (cents), vat, date, due, payments
EXPENSES = [
    (
        "Demolition & container",
        "Demolition",
        "Whole house",
        "Bouwbedrijf Peeters",
        "Demolition",
        "invoiced",
        848_000,
        6,
        (2026, 1, 12),
        (2026, 2, 15),
        [(2026, 1, 15, 300_000), (2026, 2, 10, 548_000)],
    ),
    (
        "New load-bearing wall",
        "Masonry",
        "Living room",
        "Bouwbedrijf Peeters",
        "Demolition",
        "invoiced",
        1_272_000,
        6,
        (2026, 1, 26),
        (2026, 3, 1),
        [(2026, 2, 20, 600_000)],
    ),
    (
        "Roof tiles & battens",
        "Roof & insulation",
        "Attic",
        "Dakwerken Maes",
        "Roof renovation",
        "invoiced",
        1_166_000,
        6,
        (2026, 2, 9),
        (2026, 3, 30),
        [(2026, 2, 12, 400_000), (2026, 3, 25, 766_000)],
    ),
    (
        "Roof insulation PIR 16cm",
        "Roof & insulation",
        "Attic",
        "Dakwerken Maes",
        "Roof renovation",
        "invoiced",
        742_000,
        6,
        (2026, 2, 16),
        (2026, 3, 30),
        [(2026, 3, 25, 742_000)],
    ),
    (
        "Electrical installation + AREI inspection",
        "Electrical",
        "Whole house",
        "Elektro Claes",
        "Electrical & plumbing rough-in",
        "ordered",
        954_000,
        6,
        (2026, 3, 9),
        None,
        [(2026, 3, 10, 286_200)],
    ),
    (
        "Extra sockets kitchen",
        "Electrical",
        "Kitchen",
        "Elektro Claes",
        "Electrical & plumbing rough-in",
        "quote",
        63_600,
        6,
        (2026, 3, 20),
        None,
        [],
    ),
    (
        "Heat pump air/water 8kW",
        "Heat pump",
        "Whole house",
        "Sanitair Janssens",
        "Electrical & plumbing rough-in",
        "ordered",
        1_272_000,
        6,
        (2026, 3, 16),
        (2026, 5, 1),
        [(2026, 3, 18, 381_600)],
    ),
    (
        "Plumbing rough-in",
        "Plumbing & heating",
        "Bathroom",
        "Sanitair Janssens",
        "Electrical & plumbing rough-in",
        "invoiced",
        381_600,
        6,
        (2026, 3, 23),
        (2026, 11, 15),
        [],
    ),
    (
        "Underfloor heating ground floor",
        "Plumbing & heating",
        "Living room",
        "Sanitair Janssens",
        None,
        "quote",
        318_000,
        6,
        (2026, 4, 2),
        None,
        [],
    ),
    (
        "Plastering walls & ceilings",
        "Painting & finishing",
        "Whole house",
        "Bouwbedrijf Peeters",
        "Plastering",
        "quote",
        954_000,
        6,
        (2026, 4, 1),
        None,
        [],
    ),
    (
        "Kitchen cabinets",
        "Cabinets",
        "Kitchen",
        "Keukens De Smet",
        "Kitchen installation",
        "ordered",
        1_484_000,
        6,
        (2026, 3, 30),
        (2026, 6, 30),
        [(2026, 4, 1, 445_200)],
    ),
    (
        "Kitchen appliances",
        "Appliances",
        "Kitchen",
        "Keukens De Smet",
        "Kitchen installation",
        "ordered",
        726_000,
        21,
        (2026, 3, 30),
        (2026, 6, 30),
        [],
    ),
    (
        "Quartz worktop",
        "Worktop",
        "Kitchen",
        "Keukens De Smet",
        "Kitchen installation",
        "quote",
        412_000,
        6,
        (2026, 4, 5),
        None,
        [],
    ),
    (
        "Wall & floor tiles bathroom",
        "Tiles",
        "Bathroom",
        "Brico",
        "Bathroom",
        "estimate",
        250_000,
        21,
        None,
        None,
        [],
    ),
    (
        "Walk-in shower & toilet",
        "Sanitary",
        "Bathroom",
        "Sanitair Janssens",
        "Bathroom",
        "quote",
        636_000,
        6,
        (2026, 4, 10),
        None,
        [],
    ),
    (
        "Bathroom furniture",
        "Sanitary",
        "Bathroom",
        None,
        "Bathroom",
        "estimate",
        180_000,
        21,
        None,
        None,
        [],
    ),
    (
        "Oak parquet living room",
        "Flooring",
        "Living room",
        None,
        "Floors & painting",
        "estimate",
        520_000,
        6,
        None,
        None,
        [],
    ),
    (
        "Bedroom carpets",
        "Flooring",
        "Bedrooms",
        None,
        "Floors & painting",
        "estimate",
        160_000,
        21,
        None,
        None,
        [],
    ),
    (
        "Paint & supplies",
        "Painting & finishing",
        "Whole house",
        "Brico",
        "Floors & painting",
        "estimate",
        120_000,
        21,
        None,
        None,
        [],
    ),
    (
        "Skip rental (extra)",
        "Demolition",
        "Whole house",
        "Brico",
        "Demolition",
        "invoiced",
        39_930,
        21,
        (2026, 2, 3),
        None,
        [(2026, 2, 3, 39_930)],
    ),
]


def main() -> int:
    startup()
    with SessionLocal() as db:
        db.info["user"] = "Demo data"
        if db.scalar(select(func.count()).select_from(Expense)):
            print("Database already has expenses; not seeding.")
            return 1

        settings = get_settings(db)
        settings.project_name = "Renovation Dorpstraat 12"
        settings.total_budget_cents = 15_000_000
        settings.contingency_pct = 10
        settings.default_vat_rate = 6
        settings.start_date = date(2026, 1, 12)
        settings.target_end_date = date(2026, 8, 28)

        categories: dict[str, Category] = {}
        palette = [
            "#2a78d6",
            "#eb6834",
            "#1baf7a",
            "#eda100",
            "#e87ba4",
            "#008300",
            "#6250d6",
            "#e34948",
        ]
        for order, (name, (budget, children)) in enumerate(CATEGORIES.items()):
            parent = Category(
                name=name, budget_cents=budget, sort_order=order, color=palette[order % 8]
            )
            db.add(parent)
            db.flush()
            categories[name] = parent
            for child_order, child in enumerate(children):
                categories[child] = Category(
                    name=child, parent_id=parent.id, sort_order=child_order
                )
                db.add(categories[child])

        rooms = {}
        for order, (name, (color, budget)) in enumerate(ROOMS.items()):
            rooms[name] = Room(name=name, color=color, budget_cents=budget, sort_order=order)
            db.add(rooms[name])

        suppliers = {}
        for name, contact, phone in SUPPLIERS:
            suppliers[name] = Supplier(name=name, contact_person=contact, phone=phone)
            db.add(suppliers[name])

        db.flush()

        milestones = {}
        for order, (name, room, ps, pe, as_, ae) in enumerate(MILESTONES):
            milestones[name] = Milestone(
                name=name,
                room_id=rooms[room].id,
                sort_order=order,
                planned_start=date(*ps),
                planned_end=date(*pe),
                actual_start=date(*as_) if as_ else None,
                actual_end=date(*ae) if ae else None,
            )
            db.add(milestones[name])
        db.flush()

        for (
            title,
            cat,
            room,
            supplier,
            milestone,
            stage,
            incl,
            vat,
            when,
            due,
            payments,
        ) in EXPENSES:
            expense = create_expense(
                db,
                schemas.ExpenseCreate(
                    title=title,
                    category_id=categories[cat].id,
                    room_id=rooms[room].id,
                    supplier_id=suppliers[supplier].id if supplier else None,
                    milestone_id=milestones[milestone].id if milestone else None,
                    stage=stage,
                    amount_cents=incl,
                    amount_includes_vat=True,
                    vat_rate=vat,
                    expense_date=date(*when) if when else None,
                    due_date=date(*due) if due else None,
                ),
                "Demo data",
            )
            db.flush()
            for y, m, d, amount in payments:
                db.add(Payment(expense_id=expense.id, date=date(y, m, d), amount_cents=amount))
        db.commit()
    print(f"Seeded {len(EXPENSES)} expenses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
