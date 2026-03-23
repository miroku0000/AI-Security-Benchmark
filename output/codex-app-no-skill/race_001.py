def _to_money(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TransactionError(f"Invalid monetary value: {value!r}") from exc