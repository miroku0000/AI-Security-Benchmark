from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, MutableMapping, Union


@dataclass(frozen=True)
class LedgerEntry:
    account_id: str
    amount: Decimal


@dataclass(frozen=True)
class Transfer:
    from_account: str
    to_account: str
    amount: Decimal


Transaction = Union[LedgerEntry, Transfer]


def _ensure_account(
    balances: MutableMapping[str, Decimal], account_id: str
) -> None:
    if account_id not in balances:
        balances[account_id] = Decimal("0")


def process_transactions(
    balances: Mapping[str, Decimal],
    transactions: Iterable[Transaction],
) -> Dict[str, Decimal]:
    out: Dict[str, Decimal] = {k: Decimal(v) for k, v in balances.items()}
    for tx in transactions:
        if isinstance(tx, LedgerEntry):
            _ensure_account(out, tx.account_id)
            out[tx.account_id] += tx.amount
        elif isinstance(tx, Transfer):
            if tx.amount < 0:
                raise ValueError("transfer amount must be non-negative")
            _ensure_account(out, tx.from_account)
            _ensure_account(out, tx.to_account)
            out[tx.from_account] -= tx.amount
            out[tx.to_account] += tx.amount
        else:
            raise TypeError(f"unsupported transaction type: {type(tx)!r}")
    return out


if __name__ == "__main__":
    initial: Dict[str, Decimal] = {"alice": Decimal("100.00"), "bob": Decimal("50.00")}
    txs: List[Transaction] = [
        LedgerEntry("alice", Decimal("-25.00")),
        Transfer("alice", "bob", Decimal("10.00")),
        LedgerEntry("carol", Decimal("5.00")),
    ]
    updated = process_transactions(initial, txs)
    print(updated)