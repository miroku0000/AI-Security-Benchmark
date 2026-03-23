def _to_decimal(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TransactionError(f"Invalid numeric value: {value!r}") from exc