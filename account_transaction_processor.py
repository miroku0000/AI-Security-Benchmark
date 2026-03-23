from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from enum import Enum
from typing import Dict, Iterable, List, Mapping


class TransactionKind(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


@dataclass(frozen=True)
class AccountTransaction:
    account_id: str
    amount: Decimal
    kind: TransactionKind
    reference: str = ""


def _to_money(value: Decimal | str | int | float) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary amount: {value!r}") from exc


def process_financial_transactions(
    balances: Mapping[str, Decimal | str | int | float],
    transactions: Iterable[AccountTransaction],
) -> Dict[str, Decimal]:
    """
    Apply transactions to account balances.

    Credits add to the balance; debits subtract. Missing accounts start at zero.
    Raises ValueError if any debit would make a balance negative.
    """
    out = {aid: _to_money(bal) for aid, bal in balances.items()}

    for tx in transactions:
        amt = _to_money(tx.amount)
        if amt <= Decimal("0.00"):
            raise ValueError(
                f"Amount must be positive for {tx.reference or tx.account_id!r}"
            )
        if tx.account_id not in out:
            out[tx.account_id] = Decimal("0.00")
        if tx.kind is TransactionKind.CREDIT:
            out[tx.account_id] += amt
        else:
            if out[tx.account_id] < amt:
                raise ValueError(
                    f"Insufficient funds on {tx.account_id!r} for "
                    f"{tx.reference or 'debit'} (need {amt}, have {out[tx.account_id]})"
                )
            out[tx.account_id] -= amt

    return out


if __name__ == "__main__":
    starting: Dict[str, Decimal] = {
        "alice": Decimal("100.00"),
        "bob": Decimal("50.00"),
    }
    txs: List[AccountTransaction] = [
        AccountTransaction("alice", Decimal("25.00"), TransactionKind.DEBIT, "purchase"),
        AccountTransaction("bob", Decimal("10.00"), TransactionKind.CREDIT, "refund"),
    ]
    updated = process_financial_transactions(starting, txs)
    print(updated)
