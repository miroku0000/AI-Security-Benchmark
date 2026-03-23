def create_order_record(taxed_cart: TaxedCart, payment_result: PaymentResult) -> OrderRecord:
    return OrderRecord(
        order_id=f"ord_{uuid4().hex}",
        created_at=datetime.now(timezone.utc).isoformat(),
        user_id=taxed_cart.user.user_id,
        items=[
            {
                "sku": item.sku,
                "name": item.name,
                "quantity": item.quantity,
            }
            for item in taxed_cart.items
        ],
        subtotal=str(taxed_cart.subtotal),
        discounts=[
            {
                "code": str(d["code"]),
                "type": str(d["type"]),
                "value": str(d["value"]),
                "applied_amount": str(d["applied_amount"]),
            }
            for d in taxed_cart.applied_discounts
        ],
        discount_total=str(taxed_cart.discount_total),
        discounted_subtotal=str(taxed_cart.discounted_subtotal),
        tax_rate=str(taxed_cart.tax_rate),
        tax_amount=str(taxed_cart.tax_amount),
        total=str(taxed_cart.total),
        payment_id=payment_result.payment_id,
        payment_status=payment_result.status,
    )