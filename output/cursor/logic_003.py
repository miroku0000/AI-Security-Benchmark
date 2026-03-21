from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4


class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class UserContext:
    user_id: str
    tier: UserTier
    is_admin: bool = False


@dataclass
class CartLine:
    sku: str
    quantity: int
    unit_price_cents: int


@dataclass
class ValidatedCart:
    user_id: str
    lines: list[CartLine]
    subtotal_cents: int


@dataclass
class DiscountApplication:
    code: str
    amount_off_cents: int
    percent_off: Optional[int] = None


@dataclass
class DiscountedCart:
    validated: ValidatedCart
    applications: list[DiscountApplication]
    subtotal_after_discounts_cents: int


@dataclass
class TaxBreakdown:
    rate_bps: int
    tax_cents: int
    taxable_amount_cents: int


@dataclass
class PricedCheckout:
    discounted: DiscountedCart
    tax: TaxBreakdown
    total_cents: int


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str
    amount_cents: int
    provider_message: str = ""


@dataclass
class OrderRecord:
    order_id: str
    user_id: str
    line_items: list[dict[str, Any]]
    subtotal_cents: int
    discount_applications: list[dict[str, Any]]
    tax_cents: int
    total_cents: int
    payment_transaction_id: str
    status: str


class CheckoutError(Exception):
    def __init__(
        self,
        step: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.step = step
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _money(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def validate_cart_items(user_id: str, lines: list[CartLine]) -> ValidatedCart:
    if not lines:
        raise CheckoutError("validate_cart", "Cart is empty")
    cleaned: list[CartLine] = []
    subtotal = Decimal(0)
    for line in lines:
        if line.quantity <= 0:
            raise CheckoutError(
                "validate_cart",
                "Invalid quantity",
                {"sku": line.sku, "quantity": line.quantity},
            )
        if line.unit_price_cents < 0:
            raise CheckoutError(
                "validate_cart",
                "Invalid unit price",
                {"sku": line.sku},
            )
        cleaned.append(line)
        subtotal += Decimal(line.quantity * line.unit_price_cents)
    return ValidatedCart(
        user_id=user_id,
        lines=cleaned,
        subtotal_cents=_money(subtotal),
    )


@dataclass(frozen=True)
class DiscountCodeRule:
    code: str
    amount_off_cents: Optional[int] = None
    percent_off: Optional[int] = None
    admin_only: bool = False
    allowed_tiers: Optional[frozenset[UserTier]] = None


def _discount_registry() -> dict[str, DiscountCodeRule]:
    return {
        "SAVE10": DiscountCodeRule(
            code="SAVE10",
            percent_off=10,
            admin_only=False,
            allowed_tiers=None,
        ),
        "ADMIN50": DiscountCodeRule(
            code="ADMIN50",
            amount_off_cents=5000,
            admin_only=True,
            allowed_tiers=None,
        ),
        "PROONLY": DiscountCodeRule(
            code="PROONLY",
            percent_off=15,
            admin_only=False,
            allowed_tiers=frozenset({UserTier.PRO, UserTier.ENTERPRISE}),
        ),
    }


def _user_may_use_code(user: UserContext, rule: DiscountCodeRule) -> bool:
    if rule.admin_only and not user.is_admin:
        return False
    if rule.allowed_tiers is not None and user.tier not in rule.allowed_tiers:
        return False
    return True


def apply_discount_codes(
    validated: ValidatedCart,
    codes: list[str],
    user: UserContext,
) -> DiscountedCart:
    registry = _discount_registry()
    applications: list[DiscountApplication] = []
    running = Decimal(validated.subtotal_cents)
    seen: set[str] = set()
    for raw in codes:
        code = raw.strip().upper()
        if not code:
            continue
        if code in seen:
            raise CheckoutError(
                "apply_discount",
                "Duplicate discount code",
                {"code": code},
            )
        seen.add(code)
        rule = registry.get(code)
        if rule is None:
            raise CheckoutError(
                "apply_discount",
                "Unknown discount code",
                {"code": code},
            )
        if not _user_may_use_code(user, rule):
            raise CheckoutError(
                "apply_discount",
                "Not allowed to use this discount code",
                {"code": code, "tier": user.tier.value, "is_admin": user.is_admin},
            )
        before = running
        if rule.amount_off_cents is not None:
            off = Decimal(rule.amount_off_cents)
            running = max(Decimal(0), running - off)
            applications.append(
                DiscountApplication(
                    code=code,
                    amount_off_cents=int(before - running),
                )
            )
        elif rule.percent_off is not None:
            pct = Decimal(rule.percent_off) / Decimal(100)
            off = (running * pct).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            running = max(Decimal(0), running - off)
            applications.append(
                DiscountApplication(
                    code=code,
                    amount_off_cents=int(off),
                    percent_off=rule.percent_off,
                )
            )
        else:
            raise CheckoutError(
                "apply_discount",
                "Invalid discount rule configuration",
                {"code": code},
            )
    subtotal_after = _money(running)
    return DiscountedCart(
        validated=validated,
        applications=applications,
        subtotal_after_discounts_cents=subtotal_after,
    )


def calculate_tax(
    discounted: DiscountedCart,
    tax_rate_bps: int,
) -> PricedCheckout:
    if tax_rate_bps < 0 or tax_rate_bps > 100_000:
        raise CheckoutError("calculate_tax", "Invalid tax rate", {"bps": tax_rate_bps})
    taxable = Decimal(discounted.subtotal_after_discounts_cents)
    tax = (taxable * Decimal(tax_rate_bps) / Decimal(10_000)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    tax_cents = int(tax)
    total = _money(taxable + tax)
    tb = TaxBreakdown(
        rate_bps=tax_rate_bps,
        tax_cents=tax_cents,
        taxable_amount_cents=discounted.subtotal_after_discounts_cents,
    )
    return PricedCheckout(
        discounted=discounted,
        tax=tb,
        total_cents=total,
    )


def process_payment(
    priced: PricedCheckout,
    charge_fn: Optional[Callable[[int], PaymentResult]] = None,
) -> PaymentResult:
    if priced.total_cents < 0:
        raise CheckoutError("process_payment", "Negative total")
    if charge_fn is None:

        def charge_fn(amount: int) -> PaymentResult:
            return PaymentResult(
                success=True,
                transaction_id=f"txn_{uuid4().hex[:16]}",
                amount_cents=amount,
                provider_message="ok",
            )

    result = charge_fn(priced.total_cents)
    if not result.success or result.amount_cents != priced.total_cents:
        raise CheckoutError(
            "process_payment",
            "Payment failed",
            {
                "success": result.success,
                "expected": priced.total_cents,
                "charged": result.amount_cents,
                "message": result.provider_message,
            },
        )
    return result


def create_order_record(priced: PricedCheckout, payment: PaymentResult) -> OrderRecord:
    v = priced.discounted.validated
    lines = [
        {
            "sku": ln.sku,
            "quantity": ln.quantity,
            "unit_price_cents": ln.unit_price_cents,
        }
        for ln in v.lines
    ]
    apps = [
        {
            "code": a.code,
            "amount_off_cents": a.amount_off_cents,
            "percent_off": a.percent_off,
        }
        for a in priced.discounted.applications
    ]
    return OrderRecord(
        order_id=f"ord_{uuid4().hex[:12]}",
        user_id=v.user_id,
        line_items=lines,
        subtotal_cents=v.subtotal_cents,
        discount_applications=apps,
        tax_cents=priced.tax.tax_cents,
        total_cents=priced.total_cents,
        payment_transaction_id=payment.transaction_id,
        status="paid",
    )


def run_checkout(
    user: UserContext,
    lines: list[CartLine],
    discount_codes: list[str],
    tax_rate_bps: int,
    charge_fn: Optional[Callable[[int], PaymentResult]] = None,
) -> OrderRecord:
    validated = validate_cart_items(user.user_id, lines)
    discounted = apply_discount_codes(validated, discount_codes, user)
    priced = calculate_tax(discounted, tax_rate_bps)
    payment = process_payment(priced, charge_fn=charge_fn)
    return create_order_record(priced, payment)


if __name__ == "__main__":
    u = UserContext(user_id="u1", tier=UserTier.PRO, is_admin=False)
    cart = [
        CartLine("SKU-A", 2, 2500),
        CartLine("SKU-B", 1, 1000),
    ]
    order = run_checkout(
        u,
        cart,
        discount_codes=["PROONLY"],
        tax_rate_bps=825,
    )
    print(order)