def process_payment(user: User, cart_items: List[CartItem], payment_details: Dict[str, Any]) -> Dict[str, Any]:
    role_discounts = {
        "basic": 0.00,
        "premium": 0.15,
        "enterprise": 0.30,
    }