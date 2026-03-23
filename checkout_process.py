from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4


class UserTier(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class User:
    id: str
    tier: UserTier
    is_admin: bool = False


@dataclass(frozen=True)
class CartItem:
    sku: str
    quantity: int
    unit_price_cents: int
    name: str = ""


@dataclass(frozen=True)
class Cart:
    items: tuple[CartItem, ...]


class DiscountScope(str, Enum):
    PUBLIC = "public"
    ADMIN_ONLY = "admin_only"
    TIER_PREMIUM = "tier_premium"
    TIER_ENTERPRISE = "tier_enterprise"


@dataclass(frozen=True)
class DiscountCode:
    code: str
    scope: DiscountScope
    percent_off: Decimal
    max_discount_cents: Optional[int] = None


@dataclass
class ValidationResult:
    ok: bool
    user: User
    cart: Cart
    subtotal_cents: int
    line_totals_cents: tuple[int, ...]
    errors: tuple[str, ...] = ()


@dataclass
class DiscountResult:
    ok: bool
    validation: ValidationResult
    applied_codes: tuple[str, ...]
    discount_cents: int
    subtotal_after_discount_cents: int
    errors: tuple[str, ...] = ()


@dataclass
class TaxResult:
    ok: bool
    discount: DiscountResult
    tax_rate: Decimal
    tax_cents: int
    total_cents: int
    errors: tuple[str, ...] = ()


@dataclass
class PaymentResult:
    ok: bool
    tax: TaxResult
    transaction_id: str
    amount_charged_cents: int
    errors: tuple[str, ...] = ()


@dataclass
class Order:
    order_id: str
    user_id: str
    payment: PaymentResult
    items_snapshot: tuple[dict[str, Any], ...]


DISCOUNT_REGISTRY: dict[str, DiscountCode] = {
    "SAVE10": DiscountCode("SAVE10", DiscountScope.PUBLIC, Decimal("10")),
    "ADMIN50": DiscountCode("ADMIN50", DiscountScope.ADMIN_ONLY, Decimal("50")),
    "PREMIUM15": DiscountCode("PREMIUM15", DiscountScope.TIER_PREMIUM, Decimal("15")),
    "VIP20": DiscountCode("VIP20", DiscountScope.TIER_ENTERPRISE, Decimal("20"), max_discount_cents=5000),
}


def _user_may_use_discount(user: User, d: DiscountCode) -> bool:
    if d.scope == DiscountScope.PUBLIC:
        return True
    if d.scope == DiscountScope.ADMIN_ONLY:
        return user.is_admin
    if d.scope == DiscountScope.TIER_PREMIUM:
        return user.tier in (UserTier.PREMIUM, UserTier.ENTERPRISE) or user.is_admin
    if d.scope == DiscountScope.TIER_ENTERPRISE:
        return user.tier == UserTier.ENTERPRISE or user.is_admin
    return False


def validate_cart(cart: Cart, user: User) -> ValidationResult:
    errors: list[str] = []
    if not cart.items:
        errors.append("cart is empty")
    line_totals: list[int] = []
    for it in cart.items:
        if it.quantity <= 0:
            errors.append(f"invalid quantity for {it.sku}")
        if it.unit_price_cents < 0:
            errors.append(f"invalid price for {it.sku}")
        if not it.sku:
            errors.append("item missing sku")
        line_totals.append(max(0, it.quantity) * max(0, it.unit_price_cents))
    subtotal = sum(line_totals)
    ok = len(errors) == 0
    return ValidationResult(
        ok=ok,
        user=user,
        cart=cart,
        subtotal_cents=subtotal,
        line_totals_cents=tuple(line_totals),
        errors=tuple(errors),
    )


def apply_discount_codes(
    validation: ValidationResult,
    codes: tuple[str, ...],
    user: User,
    registry: dict[str, DiscountCode] = DISCOUNT_REGISTRY,
) -> DiscountResult:
    if not validation.ok:
        return DiscountResult(
            ok=False,
            validation=validation,
            applied_codes=(),
            discount_cents=0,
            subtotal_after_discount_cents=validation.subtotal_cents,
            errors=validation.errors + ("cannot apply discounts: cart invalid",),
        )
    subtotal = validation.subtotal_cents
    errs: list[str] = []
    seen: set[str] = set()
    resolved: list[tuple[str, DiscountCode]] = []
    for raw in codes:
        key = raw.strip().upper()
        if key in seen:
            errs.append(f"duplicate code: {raw}")
            continue
        seen.add(key)
        d = registry.get(key)
        if d is None:
            errs.append(f"unknown discount code: {raw}")
            continue
        if not _user_may_use_discount(user, d):
            errs.append(f"not allowed to use code: {raw}")
            continue
        pct = d.percent_off
        if pct < 0 or pct > 100:
            errs.append(f"invalid discount configuration: {raw}")
            continue
        resolved.append((key, d))
    if errs:
        return DiscountResult(
            ok=False,
            validation=validation,
            applied_codes=(),
            discount_cents=0,
            subtotal_after_discount_cents=subtotal,
            errors=tuple(errs),
        )
    total_discount = 0
    applied: list[str] = []
    running = subtotal
    for key, d in resolved:
        line_disc = (Decimal(running) * d.percent_off / Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        disc = int(line_disc)
        if d.max_discount_cents is not None:
            disc = min(disc, d.max_discount_cents)
        disc = min(disc, running)
        if disc > 0:
            total_discount += disc
            running -= disc
            applied.append(key)
    after = max(0, subtotal - total_discount)
    return DiscountResult(
        ok=True,
        validation=validation,
        applied_codes=tuple(applied),
        discount_cents=total_discount,
        subtotal_after_discount_cents=after,
        errors=(),
    )


def calculate_tax(
    discount_result: DiscountResult,
    tax_rate: Decimal,
    tax_region: str = "default",
) -> TaxResult:
    if not discount_result.ok:
        return TaxResult(
            ok=False,
            discount=discount_result,
            tax_rate=tax_rate,
            tax_cents=0,
            total_cents=0,
            errors=discount_result.errors + ("cannot calculate tax: discount step failed",),
        )
    if tax_rate < 0:
        return TaxResult(
            ok=False,
            discount=discount_result,
            tax_rate=tax_rate,
            tax_cents=0,
            total_cents=0,
            errors=("invalid tax rate",),
        )
    base = discount_result.subtotal_after_discount_cents
    tax_amt = (Decimal(base) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    tax_cents = int(tax_amt)
    total = base + tax_cents
    _ = tax_region
    return TaxResult(
        ok=True,
        discount=discount_result,
        tax_rate=tax_rate,
        tax_cents=tax_cents,
        total_cents=total,
        errors=(),
    )


def process_payment(
    tax_result: TaxResult,
    charge_fn: Optional[Callable[[int], tuple[bool, str]]] = None,
) -> PaymentResult:
    if not tax_result.ok:
        return PaymentResult(
            ok=False,
            tax=tax_result,
            transaction_id="",
            amount_charged_cents=0,
            errors=tax_result.errors + ("cannot charge: tax step failed",),
        )
    amount = tax_result.total_cents
    if amount < 0:
        return PaymentResult(
            ok=False,
            tax=tax_result,
            transaction_id="",
            amount_charged_cents=0,
            errors=("invalid charge amount",),
        )

    def default_charge(amt: int) -> tuple[bool, str]:
        if amt == 0:
            return True, f"noop-{uuid4().hex[:12]}"
        return True, f"txn-{uuid4().hex}"

    fn = charge_fn or default_charge
    success, txn_id = fn(amount)
    if not success:
        return PaymentResult(
            ok=False,
            tax=tax_result,
            transaction_id="",
            amount_charged_cents=0,
            errors=("payment declined",),
        )
    return PaymentResult(
        ok=True,
        tax=tax_result,
        transaction_id=txn_id,
        amount_charged_cents=amount,
        errors=(),
    )


def create_order_record(payment_result: PaymentResult) -> Order:
    if not payment_result.ok:
        raise ValueError("cannot create order: payment failed")
    v = payment_result.tax.discount.validation
    snap = []
    for it, lt in zip(v.cart.items, v.line_totals_cents, strict=True):
        snap.append(
            {
                "sku": it.sku,
                "name": it.name,
                "quantity": it.quantity,
                "unit_price_cents": it.unit_price_cents,
                "line_total_cents": lt,
            }
        )
    return Order(
        order_id=f"ord-{uuid4().hex}",
        user_id=v.user.id,
        payment=payment_result,
        items_snapshot=tuple(snap),
    )


def run_checkout(
    cart: Cart,
    user: User,
    discount_codes: tuple[str, ...],
    tax_rate: Decimal,
    charge_fn: Optional[Callable[[int], tuple[bool, str]]] = None,
) -> tuple[ValidationResult, DiscountResult, TaxResult, PaymentResult, Order]:
    v = validate_cart(cart, user)
    d = apply_discount_codes(v, discount_codes, user)
    t = calculate_tax(d, tax_rate)
    p = process_payment(t, charge_fn=charge_fn)
    if not p.ok:
        raise RuntimeError(f"checkout failed: {p.errors}")
    order = create_order_record(p)
    return v, d, t, p, order


if __name__ == "__main__":
    u = User(id="u1", tier=UserTier.PREMIUM, is_admin=False)
    c = Cart(
        items=(
            CartItem("SKU1", 2, 1500, "Widget"),
            CartItem("SKU2", 1, 3200, "Gadget"),
        )
    )
    v, d, t, p, order = run_checkout(c, u, ("SAVE10", "PREMIUM15"), Decimal("0.0825"))
    assert v.ok and d.ok and t.ok and p.ok
    print(order.order_id, order.payment.amount_charged_cents)
