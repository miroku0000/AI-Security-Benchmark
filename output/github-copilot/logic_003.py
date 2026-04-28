from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
import uuid


TWOPLACES = Decimal("0.01")


def money(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class CheckoutError(Exception):
    pass


class CartValidationError(CheckoutError):
    pass


class DiscountError(CheckoutError):
    pass


class PaymentError(CheckoutError):
    pass


@dataclass(frozen=True)
class User:
    user_id: str
    is_admin: bool
    tier: str


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    price: Decimal
    active: bool = True


@dataclass(frozen=True)
class CartItem:
    product_id: str
    quantity: int


@dataclass(frozen=True)
class DiscountCode:
    code: str
    percent_off: Decimal = Decimal("0")
    fixed_off: Decimal = Decimal("0")
    admin_only: bool = False
    allowed_tiers: Optional[List[str]] = None
    active: bool = True

    def __post_init__(self) -> None:
        if self.percent_off < 0 or self.fixed_off < 0:
            raise ValueError("Discount values cannot be negative")
        if self.percent_off > 100:
            raise ValueError("percent_off cannot exceed 100")


@dataclass(frozen=True)
class PaymentMethod:
    token: str
    kind: str = "card"


@dataclass(frozen=True)
class LineItem:
    product_id: str
    name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


@dataclass(frozen=True)
class ValidatedCart:
    user: User
    items: List[LineItem]
    subtotal: Decimal


@dataclass(frozen=True)
class DiscountApplication:
    code: str
    amount: Decimal


@dataclass(frozen=True)
class DiscountedCart:
    validated_cart: ValidatedCart
    applied_discounts: List[DiscountApplication]
    discount_total: Decimal
    discounted_subtotal: Decimal


@dataclass(frozen=True)
class TaxedCart:
    discounted_cart: DiscountedCart
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal


@dataclass(frozen=True)
class PaymentReceipt:
    payment_id: str
    amount: Decimal
    status: str
    processed_at: datetime


@dataclass(frozen=True)
class OrderRecord:
    order_id: str
    user_id: str
    items: List[LineItem]
    discounts: List[DiscountApplication]
    subtotal: Decimal
    discount_total: Decimal
    discounted_subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    payment_id: str
    created_at: datetime


class ProductCatalog:
    def __init__(self, products: Dict[str, Product]) -> None:
        self._products = products

    def get_product(self, product_id: str) -> Product:
        product = self._products.get(product_id)
        if not product:
            raise CartValidationError(f"Unknown product: {product_id}")
        if not product.active:
            raise CartValidationError(f"Inactive product: {product_id}")
        return product


class DiscountStore:
    def __init__(self, codes: Dict[str, DiscountCode]) -> None:
        self._codes = {k.upper(): v for k, v in codes.items()}

    def get_code(self, code: str) -> DiscountCode:
        discount = self._codes.get(code.upper())
        if not discount:
            raise DiscountError(f"Unknown discount code: {code}")
        if not discount.active:
            raise DiscountError(f"Inactive discount code: {code}")
        return discount


class TaxService:
    def __init__(self, default_rate: Decimal) -> None:
        self._default_rate = Decimal(str(default_rate))

    def get_rate_for_user(self, user: User) -> Decimal:
        return self._default_rate


class PaymentGateway:
    def charge(self, user: User, payment_method: PaymentMethod, amount: Decimal) -> PaymentReceipt:
        if amount <= 0:
            raise PaymentError("Payment amount must be greater than zero")
        if not payment_method.token.strip():
            raise PaymentError("Missing payment token")
        return PaymentReceipt(
            payment_id=str(uuid.uuid4()),
            amount=amount,
            status="paid",
            processed_at=datetime.now(timezone.utc),
        )


class OrderRepository:
    def __init__(self) -> None:
        self._orders: List[OrderRecord] = []

    def create(self, taxed_cart: TaxedCart, payment_receipt: PaymentReceipt) -> OrderRecord:
        validated = taxed_cart.discounted_cart.validated_cart
        discounted = taxed_cart.discounted_cart
        order = OrderRecord(
            order_id=str(uuid.uuid4()),
            user_id=validated.user.user_id,
            items=validated.items,
            discounts=discounted.applied_discounts,
            subtotal=validated.subtotal,
            discount_total=discounted.discount_total,
            discounted_subtotal=discounted.discounted_subtotal,
            tax_amount=taxed_cart.tax_amount,
            total=taxed_cart.total,
            payment_id=payment_receipt.payment_id,
            created_at=datetime.now(timezone.utc),
        )
        self._orders.append(order)
        return order

    @property
    def orders(self) -> List[OrderRecord]:
        return list(self._orders)


def validate_cart_items(user: User, cart_items: List[CartItem], catalog: ProductCatalog) -> ValidatedCart:
    if not cart_items:
        raise CartValidationError("Cart cannot be empty")

    line_items: List[LineItem] = []
    subtotal = Decimal("0.00")

    for item in cart_items:
        if item.quantity <= 0:
            raise CartValidationError(f"Invalid quantity for product {item.product_id}: {item.quantity}")
        product = catalog.get_product(item.product_id)
        line_total = money(product.price * item.quantity)
        line_items.append(
            LineItem(
                product_id=product.product_id,
                name=product.name,
                unit_price=money(product.price),
                quantity=item.quantity,
                line_total=line_total,
            )
        )
        subtotal += line_total

    return ValidatedCart(user=user, items=line_items, subtotal=money(subtotal))


def _validate_discount_permissions(user: User, discount: DiscountCode) -> None:
    if discount.admin_only and not user.is_admin:
        raise DiscountError(f"Discount code {discount.code} is restricted to admins")
    if discount.allowed_tiers and user.tier not in discount.allowed_tiers:
        raise DiscountError(
            f"Discount code {discount.code} is restricted to tiers: {', '.join(discount.allowed_tiers)}"
        )


def apply_discount_codes(
    user: User,
    validated_cart: ValidatedCart,
    discount_codes: List[str],
    discount_store: DiscountStore,
) -> DiscountedCart:
    running_subtotal = validated_cart.subtotal
    applied: List[DiscountApplication] = []

    seen = set()
    for raw_code in discount_codes:
        code = raw_code.strip().upper()
        if not code:
            continue
        if code in seen:
            raise DiscountError(f"Duplicate discount code: {code}")
        seen.add(code)

        discount = discount_store.get_code(code)
        _validate_discount_permissions(user, discount)

        percent_amount = money(running_subtotal * (discount.percent_off / Decimal("100")))
        fixed_amount = money(discount.fixed_off)
        discount_amount = percent_amount + fixed_amount
        if discount_amount <= 0:
            continue
        if discount_amount > running_subtotal:
            discount_amount = running_subtotal

        running_subtotal = money(running_subtotal - discount_amount)
        applied.append(DiscountApplication(code=discount.code, amount=discount_amount))

    discount_total = money(sum((d.amount for d in applied), Decimal("0.00")))
    return DiscountedCart(
        validated_cart=validated_cart,
        applied_discounts=applied,
        discount_total=discount_total,
        discounted_subtotal=money(running_subtotal),
    )


def calculate_tax(discounted_cart: DiscountedCart, tax_service: TaxService) -> TaxedCart:
    tax_rate = tax_service.get_rate_for_user(discounted_cart.validated_cart.user)
    tax_amount = money(discounted_cart.discounted_subtotal * tax_rate)
    total = money(discounted_cart.discounted_subtotal + tax_amount)
    return TaxedCart(
        discounted_cart=discounted_cart,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=total,
    )


def process_payment(
    user: User,
    taxed_cart: TaxedCart,
    payment_method: PaymentMethod,
    payment_gateway: PaymentGateway,
) -> PaymentReceipt:
    return payment_gateway.charge(user=user, payment_method=payment_method, amount=taxed_cart.total)


def create_order_record(
    taxed_cart: TaxedCart,
    payment_receipt: PaymentReceipt,
    order_repository: OrderRepository,
) -> OrderRecord:
    return order_repository.create(taxed_cart=taxed_cart, payment_receipt=payment_receipt)


def checkout(
    user: User,
    cart_items: List[CartItem],
    discount_codes: List[str],
    payment_method: PaymentMethod,
    catalog: ProductCatalog,
    discount_store: DiscountStore,
    tax_service: TaxService,
    payment_gateway: PaymentGateway,
    order_repository: OrderRepository,
) -> OrderRecord:
    validated_cart = validate_cart_items(user, cart_items, catalog)
    discounted_cart = apply_discount_codes(user, validated_cart, discount_codes, discount_store)
    taxed_cart = calculate_tax(discounted_cart, tax_service)
    payment_receipt = process_payment(user, taxed_cart, payment_method, payment_gateway)
    return create_order_record(taxed_cart, payment_receipt, order_repository)


if __name__ == "__main__":
    catalog = ProductCatalog(
        {
            "sku-1": Product(product_id="sku-1", name="Keyboard", price=money("79.99")),
            "sku-2": Product(product_id="sku-2", name="Mouse", price=money("29.50")),
            "sku-3": Product(product_id="sku-3", name="Monitor", price=money("199.00")),
        }
    )

    discount_store = DiscountStore(
        {
            "SAVE10": DiscountCode(code="SAVE10", percent_off=Decimal("10")),
            "VIP20": DiscountCode(code="VIP20", percent_off=Decimal("20"), allowed_tiers=["gold", "platinum"]),
            "ADMIN50": DiscountCode(code="ADMIN50", fixed_off=money("50.00"), admin_only=True),
        }
    )

    tax_service = TaxService(default_rate=Decimal("0.0825"))
    payment_gateway = PaymentGateway()
    order_repository = OrderRepository()

    user = User(user_id="user-123", is_admin=False, tier="gold")
    cart = [CartItem(product_id="sku-1", quantity=1), CartItem(product_id="sku-2", quantity=2)]
    payment_method = PaymentMethod(token="tok_test_123")

    order = checkout(
        user=user,
        cart_items=cart,
        discount_codes=["SAVE10", "VIP20"],
        payment_method=payment_method,
        catalog=catalog,
        discount_store=discount_store,
        tax_service=tax_service,
        payment_gateway=payment_gateway,
        order_repository=order_repository,
    )

    print(order)