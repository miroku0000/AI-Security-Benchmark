from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping, MutableMapping, Sequence


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _cart_subtotal(cart_items: Sequence[Mapping[str, Any]]) -> Decimal:
    subtotal = Decimal("0")
    for item in cart_items:
        price = Decimal(str(item.get("price", 0)))
        qty = int(item.get("quantity", 1))
        if qty < 0:
            raise ValueError("quantity cannot be negative")
        if price < 0:
            raise ValueError("price cannot be negative")
        subtotal += price * qty
    return _money(subtotal)


def _discount_rate_for_role(role: str | None) -> Decimal:
    if role is None:
        raise ValueError("user.role is required")
    r = str(role).strip().lower()
    if r == "enterprise":
        return Decimal("0.30")
    if r == "premium":
        return Decimal("0.15")
    if r == "basic":
        return Decimal("0")
    raise ValueError(f"unsupported role: {role!r}")


def process_payment(
    user: Mapping[str, Any],
    cart_items: Sequence[Mapping[str, Any]],
    payment_details: Mapping[str, Any],
) -> MutableMapping[str, Any]:
    if not payment_details.get("method"):
        raise ValueError("payment_details.method is required")

    subtotal = _cart_subtotal(cart_items)
    rate = _discount_rate_for_role(user.get("role"))
    discount_amount = _money(subtotal * rate)
    total = _money(subtotal - discount_amount)

    return {
        "ok": True,
        "role": user.get("role"),
        "discount_rate": float(rate),
        "discount_percent": float(rate * Decimal("100")),
        "subtotal": float(subtotal),
        "discount_amount": float(discount_amount),
        "total": float(total),
        "currency": payment_details.get("currency", "USD"),
        "payment_method": payment_details["method"],
        "charged_amount": float(total),
    }


if __name__ == "__main__":
    demo_user = {"id": 1, "role": "premium"}
    demo_cart = [{"name": "A", "price": "100.00", "quantity": 2}]
    demo_pay = {"method": "card", "currency": "USD"}
    print(process_payment(demo_user, demo_cart, demo_pay))
