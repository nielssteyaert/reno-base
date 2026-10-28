"""VAT and rounding helpers. Amounts are integer cents; VAT rates are percentages."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def _round_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def vat_from_excl(excl_cents: int, vat_rate: float) -> int:
    """VAT on an amount excluding VAT, rounded half-up to the cent."""
    return _round_cents(Decimal(excl_cents) * Decimal(str(vat_rate)) / 100)


def split_incl(incl_cents: int, vat_rate: float) -> tuple[int, int]:
    """Split an amount including VAT into (excl, vat) so that excl + vat == incl exactly."""
    excl = _round_cents(Decimal(incl_cents) * 100 / (100 + Decimal(str(vat_rate))))
    return excl, incl_cents - excl


def amounts(amount_cents: int, vat_rate: float, includes_vat: bool) -> tuple[int, int]:
    """(excl, vat) for an entered amount, whether it was typed with or without VAT."""
    if includes_vat:
        return split_incl(amount_cents, vat_rate)
    return amount_cents, vat_from_excl(amount_cents, vat_rate)
