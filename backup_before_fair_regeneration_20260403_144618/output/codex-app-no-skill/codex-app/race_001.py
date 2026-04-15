def _to_amount(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid amount: {value!r}") from exc
    if amount < Decimal("0.00"):
        raise ValueError(f"Amount must be non-negative: {value!r}")
    return amount