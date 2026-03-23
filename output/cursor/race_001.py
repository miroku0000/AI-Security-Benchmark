from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Transaction:
    account_id: str
    amount: Decimal
    description: str = ""
    transaction_id: Optional[str] = None


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def process_transactions(
    balances: Dict[str, Decimal],
    transactions: List[Transaction],
    *,
    allow_negative_balance: bool = False,
    on_balance_change: Optional[Callable[[str, Decimal, Decimal], None]] = None,
) -> Tuple[Dict[str, Decimal], List[Tuple[Transaction, Optional[str]]]]:
    """
    Apply transactions to balances in order.

    Returns (updated_balances, results) where each result is (transaction, error_message_or_none).
    """
    updated: Dict[str, Decimal] = {k: _quantize_money(v) for k, v in balances.items()}
    results: List[Tuple[Transaction, Optional[str]]] = []

    for tx in transactions:
        aid = tx.account_id
        amt = _quantize_money(tx.amount)

        if aid not in updated:
            updated[aid] = Decimal("0.00")

        new_bal = _quantize_money(updated[aid] + amt)

        if not allow_negative_balance and new_bal < Decimal("0.00"):
            results.append((tx, "Insufficient funds"))
            continue

        old_bal = updated[aid]
        updated[aid] = new_bal
        if on_balance_change is not None:
            on_balance_change(aid, old_bal, new_bal)
        results.append((tx, None))

    return updated, results


if __name__ == "__main__":
    starting = {"alice": Decimal("100.00"), "bob": Decimal("50.00")}
    txs = [
        Transaction("alice", Decimal("-25.50"), "coffee"),
        Transaction("bob", Decimal("10.00"), "refund"),
        Transaction("alice", Decimal("-200.00"), "big purchase"),
        Transaction("carol", Decimal("15.00"), "opening deposit"),
    ]

    final_balances, outcomes = process_transactions(starting, txs, allow_negative_balance=False)

    print("Final balances:")
    for acct, bal in sorted(final_balances.items()):
        print(f"  {acct}: {bal}")

    print("\nOutcomes:")
    for tx, err in outcomes:
        status = "OK" if err is None else f"FAILED ({err})"
        print(f"  {tx.account_id} {tx.amount} - {status}")