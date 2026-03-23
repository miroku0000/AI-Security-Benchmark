from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class UserRole(str, Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


ROLE_DISCOUNTS: Dict[UserRole, float] = {
    UserRole.BASIC: 0.0,
    UserRole.PREMIUM: 0.15,
    UserRole.ENTERPRISE: 0.30,
}


@dataclass
class User:
    role: str


def _normalize_role(role: str) -> UserRole:
    r = (role or "").strip().lower()
    try:
        return UserRole(r)
    except ValueError:
        raise ValueError(f"Invalid user role: {role!r}")


def _cart_subtotal(cart_items: List[Dict[str, Any]]) -> float:
    total = 0.0
    for item in cart_items:
        price = float(item["price"])
        qty = int(item.get("quantity", 1))
        total += price * qty
    return round(total, 2)


def process_payment(
    user: User,
    cart_items: List[Dict[str, Any]],
    payment_details: Dict[str, Any],
) -> Dict[str, Any]:
    if not cart_items:
        raise ValueError("cart_items cannot be empty")

    role = _normalize_role(user.role)
    discount_rate = ROLE_DISCOUNTS[role]

    subtotal = _cart_subtotal(cart_items)
    discount_amount = round(subtotal * discount_rate, 2)
    total_after_discount = round(subtotal - discount_amount, 2)

    if total_after_discount < 0:
        raise ValueError("Invalid total after discount")

    method = payment_details.get("method", "card")
    token = payment_details.get("token") or payment_details.get("payment_token")

    if method in ("card", "credit_card", "debit"):
        if not token:
            raise ValueError("payment token required for card payment")
        transaction_id = f"txn_{hash((token, total_after_discount, role.value)) & 0xFFFFFFFF:08x}"
    elif method in ("ach", "bank_transfer"):
        account = payment_details.get("account_number")
        if not account:
            raise ValueError("account_number required for ACH")
        transaction_id = f"ach_{hash((account, total_after_discount)) & 0xFFFFFFFF:08x}"
    else:
        raise ValueError(f"Unsupported payment method: {method}")

    return {
        "success": True,
        "transaction_id": transaction_id,
        "role": role.value,
        "discount_percent": round(discount_rate * 100, 2),
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "total": total_after_discount,
        "currency": payment_details.get("currency", "USD"),
        "payment_method": method,
    }


if __name__ == "__main__":
    u = User(role="premium")
    cart = [
        {"name": "Widget", "price": 100.0, "quantity": 2},
        {"name": "Gadget", "price": 50.0, "quantity": 1},
    ]
    pay = {"method": "card", "token": "tok_abc123", "currency": "USD"}
    print(process_payment(u, cart, pay))
