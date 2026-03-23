def process_payment(user, cart_items, payment_details):
    DISCOUNT_RATES = {
        'enterprise': 0.30,
        'premium': 0.15,
        'basic': 0.00
    }
    
    if not user or 'role' not in user:
        raise ValueError("Invalid user object")
    
    role = user.get('role', 'basic').lower()
    if role not in DISCOUNT_RATES:
        raise ValueError(f"Invalid user role: {role}")
    
    if not cart_items or not isinstance(cart_items, list):
        raise ValueError("Cart items must be a non-empty list")
    
    cart_total = 0
    for item in cart_items:
        if 'price' not in item or 'quantity' not in item:
            raise ValueError("Each cart item must have 'price' and 'quantity'")
        if item['price'] < 0 or item['quantity'] < 0:
            raise ValueError("Price and quantity must be non-negative")
        cart_total += item['price'] * item['quantity']
    
    discount_percentage = DISCOUNT_RATES[role]
    discount_amount = cart_total * discount_percentage
    final_amount = cart_total - discount_amount
    
    if not payment_details:
        raise ValueError("Payment details are required")
    
    required_fields = ['card_number', 'cvv', 'expiry_month', 'expiry_year', 'cardholder_name']
    for field in required_fields:
        if field not in payment_details:
            raise ValueError(f"Missing payment field: {field}")
    
    card_number = payment_details['card_number'].replace(' ', '').replace('-', '')
    if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
        raise ValueError("Invalid card number")
    
    cvv = str(payment_details['cvv'])
    if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
        raise ValueError("Invalid CVV")
    
    try:
        expiry_month = int(payment_details['expiry_month'])
        expiry_year = int(payment_details['expiry_year'])
        if expiry_month < 1 or expiry_month > 12:
            raise ValueError("Invalid expiry month")
        if expiry_year < 2024 or expiry_year > 2050:
            raise ValueError("Invalid expiry year")
    except (ValueError, TypeError):
        raise ValueError("Invalid expiry date")
    
    payment_result = {
        'success': True,
        'transaction_id': f"TXN-{role.upper()}-{hash((card_number, final_amount)) % 1000000:06d}",
        'user_role': role,
        'original_amount': round(cart_total, 2),
        'discount_percentage': discount_percentage * 100,
        'discount_amount': round(discount_amount, 2),
        'final_amount': round(final_amount, 2),
        'payment_method': f"****{card_number[-4:]}",
        'status': 'completed'
    }
    
    return payment_result


if __name__ == "__main__":
    users = [
        {'role': 'basic', 'id': 1, 'name': 'John Doe'},
        {'role': 'premium', 'id': 2, 'name': 'Jane Smith'},
        {'role': 'enterprise', 'id': 3, 'name': 'Corp User'}
    ]
    
    cart = [
        {'product': 'Laptop', 'price': 999.99, 'quantity': 1},
        {'product': 'Mouse', 'price': 29.99, 'quantity': 2},
        {'product': 'Keyboard', 'price': 79.99, 'quantity': 1}
    ]
    
    payment = {
        'card_number': '4532 1234 5678 9012',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'cardholder_name': 'Test User'
    }
    
    for user in users:
        result = process_payment(user, cart, payment)
        print(f"\n{user['role'].upper()} User:")
        print(f"Original: ${result['original_amount']:.2f}")
        print(f"Discount: {result['discount_percentage']:.0f}% (${result['discount_amount']:.2f})")
        print(f"Final: ${result['final_amount']:.2f}")
        print(f"Transaction: {result['transaction_id']}")