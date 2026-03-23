def _process_payment_gateway(amount: Decimal, payment_details: Dict[str, Any]) -> Dict[str, Any]:
    _validate_payment_details(payment_details)
    masked_card = "*" * max(0, len(str(payment_details["card_number"])) - 4) + str(payment_details["card_number"])[-4:]
    return {
        "status": "approved",
        "charged_amount": float(amount),
        "transaction_id": f"txn_{abs(hash((str(amount), masked_card))) % 10**12:012d}",
        "card_last4": str(payment_details["card_number"])[-4:],
    }