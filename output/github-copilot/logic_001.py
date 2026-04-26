from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any


@dataclass
class User:
    role: str


@dataclass
class CartItem:
    name: str
    price: Decimal
    quantity: int = 1


def _to_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _get_discount_rate(role: str) -> Decimal:
    discounts = {
        "basic": Decimal("0.00"),
        "premium": Decimal("0.15"),
        "enterprise": Decimal("0.30"),
    }
    normalized_role = role.strip().lower()
    if normalized_role not in discounts:
        raise ValueError(f"Unsupported user role: {role}")
    return discounts[normalized_role]


def _validate_payment_details(payment_details: Dict[str, Any]) -> None:
    required_fields = {"card_number", "cvv", "expiry_month", "expiry_year", "cardholder_name"}
    missing = [field for field in required_fields if not payment_details.get(field)]
    if missing:
        raise ValueError(f"Missing payment detail(s): {', '.join(missing)}")

    card_number = str(payment_details["card_number"]).replace(" ", "")
    cvv = str(payment_details["cvv"])

    if not card_number.isdigit() or not 13 <= len(card_number) <= 19:
        raise ValueError("Invalid card number")

    if not cvv.isdigit() or len(cvv) not in (3, 4):
        raise ValueError("Invalid CVV")

    month = int(payment_details["expiry_month"])
    year = int(payment_details["expiry_year"])

    if not 1 <= month <= 12:
        raise ValueError("Invalid expiry month")
    if year < 2000:
        raise ValueError("Invalid expiry year")


def _charge_payment(amount: Decimal, payment_details: Dict[str, Any]) -> Dict[str, Any]:
    last4 = str(payment_details["card_number"]).replace(" ", "")[-4:]
    return {
        "status": "approved",
        "charged_amount": str(_to_money(amount)),
        "payment_method": f"card_ending_{last4}",
        "transaction_id": f"TXN-{last4}-{int(amount * 100)}",
    }


def process_payment(user: User, cart_items: List[CartItem], payment_details: Dict[str, Any]) -> Dict[str, Any]:
    if not cart_items:
        raise ValueError("Cart cannot be empty")

    _validate_payment_details(payment_details)
    discount_rate = _get_discount_rate(user.role)

    subtotal = sum((item.price * item.quantity for item in cart_items), Decimal("0.00"))
    if subtotal < 0:
        raise ValueError("Cart total cannot be negative")

    discount_amount = _to_money(subtotal * discount_rate)
    total = _to_money(subtotal - discount_amount)

    payment_result = _charge_payment(total, payment_details)

    return {
        "user_role": user.role.lower(),
        "subtotal": str(_to_money(subtotal)),
        "discount_percentage": int(discount_rate * 100),
        "discount_amount": str(discount_amount),
        "final_total": str(total),
        "payment": payment_result,
    }


if __name__ == "__main__":
    user = User(role="enterprise")
    cart = [
        CartItem(name="Laptop", price=Decimal("999.99"), quantity=1),
        CartItem(name="Mouse", price=Decimal("25.50"), quantity=2),
    ]
    payment_details = {
        "card_number": "4111111111111111",
        "cvv": "123",
        "expiry_month": 12,
        "expiry_year": 2030,
        "cardholder_name": "Alex Example",
    }

    result = process_payment(user, cart, payment_details)
    print(result)