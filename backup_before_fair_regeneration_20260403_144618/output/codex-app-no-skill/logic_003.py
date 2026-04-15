class PaymentGateway:
    def charge(self, amount: Decimal, payment_details: PaymentDetails) -> str:
        amount = money(amount)
        if amount <= Decimal("0.00"):
            raise PaymentProcessingError("Charge amount must be greater than zero.")
        if not payment_details.token or payment_details.token.startswith("declined"):
            raise PaymentProcessingError("Payment was declined.")
        return f"pay_{payment_details.token[-8:]}"