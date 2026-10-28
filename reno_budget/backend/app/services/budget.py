"""Budget figures: the single place where committed, paid, forecast and remaining are defined.

Definitions (all amounts incl. VAT):
- An expense is *committed* once it is ordered or invoiced, or as soon as anything is paid on it.
- *estimated* / *quoted*: expenses still at the estimate / quote stage (not committed).
- *forecast* = committed + quoted + estimated: what the renovation is expected to cost.
- *outstanding* = committed but not yet paid.
- The project's contingency is a reserve held *inside* the total budget:
  working budget = total budget - contingency reserve.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Expense, Milestone, Payment, Room, Settings, Stage, Supplier

COMMITTED_STAGES = {Stage.ORDERED.value, Stage.INVOICED.value}
STATUSES = ["estimate", "quote", "ordered", "invoiced", "paid"]
WARNING_RATIO = 0.9


@dataclass(frozen=True)
class ExpenseFigures:
    excl: int
    vat: int
    incl: int
    paid: int
    committed: bool
    status: str
    payment_status: str

    @property
    def outstanding(self) -> int:
        return max(self.incl - self.paid, 0) if self.committed else 0


def expense_figures(expense: Expense, paid: int) -> ExpenseFigures:
    incl = expense.amount_excl_cents + expense.vat_cents
    fully_paid = paid > 0 and paid >= incl
    if fully_paid:
        payment_status = "paid"
    elif paid > 0:
        payment_status = "partial"
    else:
        payment_status = "unpaid"
    return ExpenseFigures(
        excl=expense.amount_excl_cents,
        vat=expense.vat_cents,
        incl=incl,
        paid=paid,
        committed=expense.stage in COMMITTED_STAGES or paid > 0,
        status="paid" if fully_paid else expense.stage,
        payment_status=payment_status,
    )


@dataclass
class Totals:
    count: int = 0
    excl: int = 0
    vat: int = 0
    incl: int = 0
    estimated: int = 0
    quoted: int = 0
    committed: int = 0
    paid: int = 0
    outstanding: int = 0

    def add(self, f: ExpenseFigures, stage: str) -> None:
        self.count += 1
        self.excl += f.excl
        self.vat += f.vat
        self.incl += f.incl
        self.paid += f.paid
        if f.committed:
            self.committed += f.incl
            self.outstanding += f.outstanding
        elif stage == Stage.QUOTE.value:
            self.quoted += f.incl
        else:
            self.estimated += f.incl

    @property
    def forecast(self) -> int:
        return self.committed + self.quoted + self.estimated


def _ratio(part: int, whole: int | None) -> float | None:
    if not whole:
        return None
    return round(part / whole, 4)


def health(forecast: int, budget: int | None) -> str:
    if not budget:
        return "none"
    if forecast > budget:
        return "over"
    if forecast >= budget * WARNING_RATIO:
        return "warning"
    return "ok"


def budget_line(totals: Totals, budget: int | None) -> dict:
    """Totals plus budget comparison, as returned by every report row."""
    data = asdict(totals)
    data.update(
        forecast=totals.forecast,
        budget=budget,
        remaining=None if budget is None else budget - totals.forecast,
        pct_committed=_ratio(totals.committed, budget),
        pct_forecast=_ratio(totals.forecast, budget),
        pct_paid=_ratio(totals.paid, budget),
        health=health(totals.forecast, budget),
    )
    return data


# --- Loading and filtering ----------------------------------------------------------------


@dataclass
class Filters:
    date_from: date | None = None
    date_to: date | None = None
    category_ids: list[int] = field(default_factory=list)
    room_ids: list[int] = field(default_factory=list)
    supplier_ids: list[int] = field(default_factory=list)
    milestone_ids: list[int] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    q: str | None = None

    @property
    def active(self) -> bool:
        return any(
            [
                self.date_from,
                self.date_to,
                self.category_ids,
                self.room_ids,
                self.supplier_ids,
                self.milestone_ids,
                self.statuses,
                self.q,
            ]
        )


@dataclass(frozen=True)
class Row:
    expense: Expense
    figures: ExpenseFigures


def paid_by_expense(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Payment.expense_id, func.sum(Payment.amount_cents)).group_by(Payment.expense_id)
    )
    return {expense_id: int(total) for expense_id, total in rows}


def _expand_categories(db: Session, ids: Iterable[int]) -> set[int]:
    wanted = set(ids)
    children = db.execute(select(Category.id, Category.parent_id)).all()
    wanted |= {cid for cid, parent in children if parent in wanted}
    return wanted


def _matches_text(expense: Expense, needle: str) -> bool:
    haystack = [
        expense.title,
        expense.description,
        expense.notes,
        expense.quote_ref,
        expense.invoice_no,
        expense.supplier.name if expense.supplier else None,
    ]
    return any(needle in value.lower() for value in haystack if value)


def load_rows(db: Session, filters: Filters | None = None) -> list[Row]:
    filters = filters or Filters()
    paid = paid_by_expense(db)
    expenses = db.scalars(select(Expense).order_by(Expense.expense_date, Expense.id)).all()
    categories = _expand_categories(db, filters.category_ids) if filters.category_ids else None
    needle = filters.q.strip().lower() if filters.q else None

    rows = []
    for expense in expenses:
        if filters.date_from and (
            not expense.expense_date or expense.expense_date < filters.date_from
        ):
            continue
        if filters.date_to and (not expense.expense_date or expense.expense_date > filters.date_to):
            continue
        if categories is not None and expense.category_id not in categories:
            continue
        if filters.room_ids and expense.room_id not in filters.room_ids:
            continue
        if filters.supplier_ids and expense.supplier_id not in filters.supplier_ids:
            continue
        if filters.milestone_ids and expense.milestone_id not in filters.milestone_ids:
            continue
        figures = expense_figures(expense, paid.get(expense.id, 0))
        if filters.statuses and figures.status not in filters.statuses:
            continue
        if needle and not _matches_text(expense, needle):
            continue
        rows.append(Row(expense, figures))
    return rows


def get_settings(db: Session) -> Settings:
    settings = db.get(Settings, 1)
    if settings is None:
        settings = Settings(id=1)
        db.add(settings)
        db.commit()
    return settings


# --- Reports ------------------------------------------------------------------------------


def _group(rows: Iterable[Row], key: Callable[[Expense], int | None]) -> dict[int | None, Totals]:
    groups: dict[int | None, Totals] = defaultdict(Totals)
    for row in rows:
        groups[key(row.expense)].add(row.figures, row.expense.stage)
    return groups


def project_summary(db: Session, rows: list[Row]) -> dict:
    settings = get_settings(db)
    totals = Totals()
    funnel = {status: {"count": 0, "amount": 0} for status in STATUSES}
    for row in rows:
        totals.add(row.figures, row.expense.stage)
        funnel[row.figures.status]["count"] += 1
        funnel[row.figures.status]["amount"] += row.figures.incl

    total_budget = settings.total_budget_cents or None
    reserve = round((settings.total_budget_cents or 0) * settings.contingency_pct / 100)
    working_budget = (settings.total_budget_cents or 0) - reserve
    allocated = sum(
        c.budget_cents or 0
        for c in db.scalars(select(Category).where(Category.parent_id.is_(None))).all()
    )
    line = budget_line(totals, total_budget)
    line.update(
        contingency_pct=settings.contingency_pct,
        contingency_reserve=reserve,
        working_budget=working_budget,
        uses_contingency=bool(total_budget) and totals.forecast > working_budget,
        over_budget=bool(total_budget) and totals.forecast > (total_budget or 0),
        contingency_used=max(0, min(totals.forecast - working_budget, reserve))
        if total_budget
        else 0,
        allocated_budget=allocated,
        unallocated_budget=working_budget - allocated,
        funnel=[{"status": s, **funnel[s]} for s in STATUSES],
    )
    return line


def by_category(db: Session, rows: list[Row]) -> list[dict]:
    """Category tree: each parent row rolls up its own expenses plus its children's."""
    categories = db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()
    groups = _group(rows, lambda e: e.category_id)
    parents = [c for c in categories if c.parent_id is None]
    children_of: dict[int, list[Category]] = defaultdict(list)
    for c in categories:
        if c.parent_id is not None:
            children_of[c.parent_id].append(c)

    result = []
    for parent in parents:
        child_rows = []
        rollup = Totals()
        _merge(rollup, groups.get(parent.id))
        for child in children_of.get(parent.id, []):
            totals = groups.get(child.id, Totals())
            _merge(rollup, totals)
            child_rows.append(_named_line(child, totals, child.budget_cents))
        child_budgets = [c["budget"] for c in child_rows if c["budget"] is not None]
        budget = parent.budget_cents
        if budget is None and child_budgets:
            budget = sum(child_budgets)
        line = _named_line(parent, rollup, budget)
        line["children"] = child_rows
        result.append(line)
    if None in groups:
        result.append(_unassigned("Uncategorized", groups[None]))
    return result


def by_room(db: Session, rows: list[Row]) -> list[dict]:
    rooms = db.scalars(select(Room).order_by(Room.sort_order, Room.name)).all()
    groups = _group(rows, lambda e: e.room_id)
    result = [_named_line(r, groups.get(r.id, Totals()), r.budget_cents) for r in rooms]
    if None in groups:
        result.append(_unassigned("No room", groups[None]))
    return result


def by_supplier(db: Session, rows: list[Row]) -> list[dict]:
    suppliers = db.scalars(select(Supplier).order_by(Supplier.name)).all()
    groups = _group(rows, lambda e: e.supplier_id)
    expense_ids_by_supplier: dict[int | None, list[int]] = defaultdict(list)
    for row in rows:
        expense_ids_by_supplier[row.expense.supplier_id].append(row.expense.id)
    last_paid = dict(
        db.execute(
            select(Expense.supplier_id, func.max(Payment.date))
            .join(Payment, Payment.expense_id == Expense.id)
            .group_by(Expense.supplier_id)
        ).all()
    )
    result = []
    for supplier in suppliers:
        if supplier.id not in groups and supplier.archived:
            continue
        line = _named_line(supplier, groups.get(supplier.id, Totals()), None)
        line["last_payment"] = last_paid.get(supplier.id)
        result.append(line)
    if None in groups:
        result.append(_unassigned("No supplier", groups[None]))
    result.sort(key=lambda r: r["forecast"], reverse=True)
    return result


def by_milestone(db: Session, rows: list[Row]) -> dict[int, dict]:
    groups = _group(rows, lambda e: e.milestone_id)
    return {mid: budget_line(t, None) for mid, t in groups.items() if mid is not None}


def monthly(db: Session, rows: list[Row]) -> list[dict]:
    """Paid per month (by payment date) and committed per month (by expense date)."""
    expense_ids = {row.expense.id for row in rows}
    paid: dict[str, int] = defaultdict(int)
    for payment in db.scalars(select(Payment)).all():
        if payment.expense_id in expense_ids:
            paid[payment.date.strftime("%Y-%m")] += payment.amount_cents
    committed: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.figures.committed:
            when = row.expense.expense_date or row.expense.created_at.date()
            committed[when.strftime("%Y-%m")] += row.figures.incl

    months = sorted(set(paid) | set(committed))
    if not months:
        return []
    months = _month_range(months[0], max(months[-1], date.today().strftime("%Y-%m")))
    result = []
    cum_paid = cum_committed = 0
    for month in months:
        cum_paid += paid.get(month, 0)
        cum_committed += committed.get(month, 0)
        result.append(
            {
                "month": month,
                "paid": paid.get(month, 0),
                "committed": committed.get(month, 0),
                "cumulative_paid": cum_paid,
                "cumulative_committed": cum_committed,
            }
        )
    return result


def upcoming_payments(rows: list[Row]) -> list[dict]:
    """Committed, unpaid expenses grouped by the month they are due."""
    buckets: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.figures.outstanding:
            key = row.expense.due_date.strftime("%Y-%m") if row.expense.due_date else "unscheduled"
            buckets[key] += row.figures.outstanding
    return [{"month": k, "amount": buckets[k]} for k in sorted(buckets)]


def due_list(rows: list[Row], limit: int = 10) -> list[dict]:
    today = date.today()
    due = [r for r in rows if r.figures.outstanding and r.expense.due_date]
    due.sort(key=lambda r: r.expense.due_date)
    return [
        {
            "id": r.expense.id,
            "title": r.expense.title,
            "due_date": r.expense.due_date,
            "outstanding": r.figures.outstanding,
            "overdue": r.expense.due_date < today,
            "supplier_id": r.expense.supplier_id,
        }
        for r in due[:limit]
    ]


def milestone_status(milestone: Milestone, today: date | None = None) -> str:
    today = today or date.today()
    if milestone.actual_end:
        return "done"
    if milestone.planned_end and milestone.planned_end < today:
        return "late"
    if milestone.actual_start:
        return "in_progress"
    return "planned"


# --- Helpers ------------------------------------------------------------------------------


def _merge(target: Totals, source: Totals | None) -> None:
    if source is None:
        return
    for key in asdict(source):
        setattr(target, key, getattr(target, key) + getattr(source, key))


def _named_line(entity, totals: Totals, budget: int | None) -> dict:
    line = budget_line(totals, budget)
    line.update(
        id=entity.id,
        name=entity.name,
        color=getattr(entity, "color", None),
        archived=getattr(entity, "archived", False),
    )
    return line


def _unassigned(name: str, totals: Totals) -> dict:
    line = budget_line(totals, None)
    line.update(id=None, name=name, color=None, archived=False)
    return line


def _month_range(first: str, last: str) -> list[str]:
    year, month = map(int, first.split("-"))
    end_year, end_month = map(int, last.split("-"))
    months = []
    while (year, month) <= (end_year, end_month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return months
