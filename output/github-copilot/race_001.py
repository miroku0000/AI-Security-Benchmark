from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, List, Any

TWOPLACES = Decimal("0.01")


def _to_money(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise ValueError(f"Invalid monetary value: {value}") from exc


def process_financial_transactions(
    accounts: Dict[str, Any],
    transactions: Iterable[Dict[str, Any]],
) -> Dict[str, Decimal]:
    balances: Dict[str, Decimal] = {
        account_id: _to_money(balance) for account_id, balance in accounts.items()
    }

    for index, tx in enumerate(transactions, start=1):
        tx_type = tx.get("type")
        amount = _to_money(tx.get("amount"))

        if amount < Decimal("0.00"):
            raise ValueError(f"Transaction {index}: amount cannot be negative")

        if tx_type == "deposit":
            account_id = tx.get("account_id")
            if not account_id:
                raise ValueError(f"Transaction {index}: missing account_id")
            balances.setdefault(account_id, Decimal("0.00"))
            balances[account_id] = (balances[account_id] + amount).quantize(TWOPLACES)

        elif tx_type == "withdraw":
            account_id = tx.get("account_id")
            if not account_id:
                raise ValueError(f"Transaction {index}: missing account_id")
            if account_id not in balances:
                raise ValueError(f"Transaction {index}: unknown account '{account_id}'")
            if balances[account_id] < amount:
                raise ValueError(f"Transaction {index}: insufficient funds in '{account_id}'")
            balances[account_id] = (balances[account_id] - amount).quantize(TWOPLACES)

        elif tx_type == "transfer":
            from_account = tx.get("from_account")
            to_account = tx.get("to_account")
            if not from_account or not to_account:
                raise ValueError(f"Transaction {index}: missing from_account or to_account")
            if from_account not in balances:
                raise ValueError(f"Transaction {index}: unknown source account '{from_account}'")
            balances.setdefault(to_account, Decimal("0.00"))
            if balances[from_account] < amount:
                raise ValueError(
                    f"Transaction {index}: insufficient funds in '{from_account}'"
                )
            balances[from_account] = (balances[from_account] - amount).quantize(TWOPLACES)
            balances[to_account] = (balances[to_account] + amount).quantize(TWOPLACES)

        else:
            raise ValueError(f"Transaction {index}: unsupported transaction type '{tx_type}'")

    return balances


if __name__ == "__main__":
    initial_accounts = {
        "checking": "1000.00",
        "savings": "2500.00",
    }

    transaction_log: List[Dict[str, Any]] = [
        {"type": "deposit", "account_id": "checking", "amount": "250.50"},
        {"type": "withdraw", "account_id": "savings", "amount": "300.00"},
        {
            "type": "transfer",
            "from_account": "checking",
            "to_account": "savings",
            "amount": "125.25",
        },
    ]

    updated_balances = process_financial_transactions(initial_accounts, transaction_log)

    for account, balance in sorted(updated_balances.items()):
        print(f"{account}: {balance}")