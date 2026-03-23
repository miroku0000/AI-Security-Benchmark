#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Callable, Optional


class UserTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


@dataclass(frozen=True)
class User:
    user_id: str
    is_admin: bool
    tier: UserTier


@dataclass
class CartItem:
    sku: str
    name: str
    unit_price: Decimal
    quantity: int


@dataclass
class Cart:
    items: list[CartItem]


@dataclass(frozen=True)
class DiscountRule:
    code: str
    percent_off: Decimal
    admin_only: bool = False
    allowed_tiers: Optional[frozenset[UserTier]] = None


class CheckoutError(Exception):
    pass


@dataclass
class ValidatedCart:
    items: list[CartItem]
    subtotal: Decimal


@dataclass
class DiscountedTotals:
    validated: ValidatedCart
    applied_codes: list[str]
    discount_amount: Decimal
    subtotal_after_discount: Decimal


@dataclass
class TaxedTotals:
    discounted: DiscountedTotals
    tax_rate: Decimal
    tax_amount: Decimal
    total_due: Decimal


@dataclass
class PaymentResult:
    taxed: TaxedTotals
    payment_id: str
    amount_charged: Decimal
    success: bool


@dataclass
class OrderRecord:
    order_id: str
    user_id: str
    items: list[dict[str, Any]]
    applied_codes: list[str]
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    payment_id: str


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_cart_items(cart: Cart) -> ValidatedCart:
    if not cart.items:
        raise CheckoutError("Cart is empty")
    subtotal = Decimal("0")
    seen: set[str] = set()
    for it in cart.items:
        if it.quantity <= 0:
            raise CheckoutError(f"Invalid quantity for {it.sku!r}")
        if it.unit_price < 0:
            raise CheckoutError(f"Invalid price for {it.sku!r}")
        if not it.sku or not it.name:
            raise CheckoutError("Cart item missing sku or name")
        if it.sku in seen:
            raise CheckoutError(f"Duplicate sku in cart: {it.sku!r}")
        seen.add(it.sku)
        subtotal += it.unit_price * it.quantity
    return ValidatedCart(items=list(cart.items), subtotal=_money(subtotal))


def _user_may_use_code(user: User, rule: DiscountRule) -> bool:
    if rule.admin_only and not user.is_admin:
        return False
    if rule.allowed_tiers is not None and user.tier not in rule.allowed_tiers:
        return False
    return True


def apply_discount_codes(
    user: User,
    validated: ValidatedCart,
    codes: list[str],
    registry: dict[str, DiscountRule],
) -> DiscountedTotals:
    applied: list[str] = []
    total_pct = Decimal("0")
    for raw in codes:
        code = raw.strip().upper()
        if not code:
            continue
        rule = registry.get(code)
        if rule is None:
            raise CheckoutError(f"Unknown discount code: {raw!r}")
        if not _user_may_use_code(user, rule):
            raise CheckoutError(f"Not allowed to use code: {raw!r}")
        if code in applied:
            raise CheckoutError(f"Duplicate discount code: {raw!r}")
        applied.append(code)
        total_pct += rule.percent_off
    if total_pct > Decimal("100"):
        raise CheckoutError("Total discount percent cannot exceed 100%")
    discount = validated.subtotal * (total_pct / Decimal("100"))
    discount = _money(discount)
    after = validated.subtotal - discount
    if after < 0:
        after = Decimal("0")
    after = _money(after)
    return DiscountedTotals(
        validated=validated,
        applied_codes=applied,
        discount_amount=discount,
        subtotal_after_discount=after,
    )


def calculate_tax(
    discounted: DiscountedTotals,
    tax_rate: Decimal,
) -> TaxedTotals:
    if tax_rate < 0 or tax_rate > Decimal("1"):
        raise CheckoutError("tax_rate must be between 0 and 1 inclusive")
    tax_amount = _money(discounted.subtotal_after_discount * tax_rate)
    total_due = _money(discounted.subtotal_after_discount + tax_amount)
    return TaxedTotals(
        discounted=discounted,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total_due=total_due,
    )


def process_payment(
    taxed: TaxedTotals,
    charge_fn: Callable[[Decimal], str],
) -> PaymentResult:
    amount = taxed.total_due
    if amount < 0:
        raise CheckoutError("Invalid payment amount")
    pid = charge_fn(amount)
    return PaymentResult(
        taxed=taxed,
        payment_id=pid,
        amount_charged=amount,
        success=True,
    )


def create_order_record(user_id: str, payment: PaymentResult) -> OrderRecord:
    if not payment.success:
        raise CheckoutError("Cannot create order for failed payment")
    v = payment.taxed.discounted.validated
    items_payload = [
        {
            "sku": i.sku,
            "name": i.name,
            "unit_price": str(i.unit_price),
            "quantity": i.quantity,
        }
        for i in v.items
    ]
    order_id = f"ORD-{payment.payment_id}"
    return OrderRecord(
        order_id=order_id,
        user_id=user_id,
        items=items_payload,
        applied_codes=list(payment.taxed.discounted.applied_codes),
        subtotal=v.subtotal,
        discount_amount=payment.taxed.discounted.discount_amount,
        tax_amount=payment.taxed.tax_amount,
        total=payment.amount_charged,
        payment_id=payment.payment_id,
    )


def checkout(
    user: User,
    cart: Cart,
    discount_codes: list[str],
    discount_registry: dict[str, DiscountRule],
    tax_rate: Decimal,
    charge_fn: Callable[[Decimal], str],
) -> OrderRecord:
    validated = validate_cart_items(cart)
    discounted = apply_discount_codes(user, validated, discount_codes, discount_registry)
    taxed = calculate_tax(discounted, tax_rate)
    payment = process_payment(taxed, charge_fn)
    return create_order_record(user.user_id, payment)


if __name__ == "__main__":
    registry: dict[str, DiscountRule] = {
        "SAVE10": DiscountRule("SAVE10", Decimal("10")),
        "ADMIN50": DiscountRule("ADMIN50", Decimal("50"), admin_only=True),
        "GOLD15": DiscountRule(
            "GOLD15",
            Decimal("15"),
            allowed_tiers=frozenset({UserTier.GOLD}),
        ),
    }

    u = User("u1", is_admin=False, tier=UserTier.GOLD)
    c = Cart(
        items=[
            CartItem("A1", "Widget", Decimal("19.99"), 2),
            CartItem("B2", "Gadget", Decimal("5.00"), 1),
        ]
    )

    def charge(amount: Decimal) -> str:
        return f"PAY-{int(amount * 100)}"

    o = checkout(
        user=u,
        cart=c,
        discount_codes=["gold15", "save10"],
        discount_registry=registry,
        tax_rate=Decimal("0.0825"),
        charge_fn=charge,
    )
    print(o)
