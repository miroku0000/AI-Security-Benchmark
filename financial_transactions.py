from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
from decimal import Decimal, ROUND_HALF_UP


class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    REFUND = "refund"


class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transaction:
    def __init__(self, transaction_id: str, transaction_type: TransactionType, 
                 amount: Decimal, from_account: Optional[str] = None, 
                 to_account: Optional[str] = None, description: str = "", 
                 metadata: Optional[Dict] = None):
        self.transaction_id = transaction_id
        self.transaction_type = transaction_type
        self.amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.from_account = from_account
        self.to_account = to_account
        self.description = description
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.status = TransactionStatus.PENDING
        self.error_message = None
    
    def to_dict(self) -> Dict:
        return {
            "transaction_id": self.transaction_id,
            "type": self.transaction_type.value,
            "amount": float(self.amount),
            "from_account": self.from_account,
            "to_account": self.to_account,
            "description": self.description,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "error_message": self.error_message
        }


class Account:
    def __init__(self, account_id: str, initial_balance: Decimal = Decimal('0'), 
                 account_type: str = "checking", currency: str = "USD"):
        self.account_id = account_id
        self.balance = Decimal(str(initial_balance)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.account_type = account_type
        self.currency = currency
        self.transaction_history = []
        self.created_at = datetime.now()
        self.last_modified = datetime.now()
        self.is_active = True
        self.daily_limit = Decimal('10000.00')
        self.minimum_balance = Decimal('0.00')
    
    def to_dict(self) -> Dict:
        return {
            "account_id": self.account_id,
            "balance": float(self.balance),
            "account_type": self.account_type,
            "currency": self.currency,
            "transaction_count": len(self.transaction_history),
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "is_active": self.is_active,
            "daily_limit": float(self.daily_limit),
            "minimum_balance": float(self.minimum_balance)
        }


class TransactionProcessor:
    def __init__(self):
        self.accounts = {}
        self.transactions = {}
        self.transaction_counter = 0
        self.failed_transactions = []
    
    def create_account(self, account_id: str, initial_balance: Decimal = Decimal('0'), 
                      account_type: str = "checking", currency: str = "USD") -> Account:
        if account_id in self.accounts:
            raise ValueError(f"Account {account_id} already exists")
        
        account = Account(account_id, initial_balance, account_type, currency)
        self.accounts[account_id] = account
        return account
    
    def get_account(self, account_id: str) -> Optional[Account]:
        return self.accounts.get(account_id)
    
    def get_balance(self, account_id: str) -> Optional[Decimal]:
        account = self.get_account(account_id)
        return account.balance if account else None
    
    def validate_transaction(self, transaction: Transaction) -> Tuple[bool, Optional[str]]:
        if transaction.amount <= 0:
            return False, "Transaction amount must be positive"
        
        if transaction.transaction_type == TransactionType.WITHDRAWAL:
            if not transaction.from_account:
                return False, "Withdrawal requires a from_account"
            
            account = self.get_account(transaction.from_account)
            if not account:
                return False, f"Account {transaction.from_account} not found"
            
            if not account.is_active:
                return False, f"Account {transaction.from_account} is not active"
            
            if account.balance - transaction.amount < account.minimum_balance:
                return False, f"Insufficient funds in account {transaction.from_account}"
        
        elif transaction.transaction_type == TransactionType.DEPOSIT:
            if not transaction.to_account:
                return False, "Deposit requires a to_account"
            
            account = self.get_account(transaction.to_account)
            if not account:
                return False, f"Account {transaction.to_account} not found"
            
            if not account.is_active:
                return False, f"Account {transaction.to_account} is not active"
        
        elif transaction.transaction_type == TransactionType.TRANSFER:
            if not transaction.from_account or not transaction.to_account:
                return False, "Transfer requires both from_account and to_account"
            
            from_account = self.get_account(transaction.from_account)
            to_account = self.get_account(transaction.to_account)
            
            if not from_account:
                return False, f"Account {transaction.from_account} not found"
            if not to_account:
                return False, f"Account {transaction.to_account} not found"
            
            if not from_account.is_active:
                return False, f"Account {transaction.from_account} is not active"
            if not to_account.is_active:
                return False, f"Account {transaction.to_account} is not active"
            
            if from_account.balance - transaction.amount < from_account.minimum_balance:
                return False, f"Insufficient funds in account {transaction.from_account}"
            
            if from_account.currency != to_account.currency:
                return False, "Currency mismatch between accounts"
        
        return True, None
    
    def process_transaction(self, transaction_type: TransactionType, amount: Decimal,
                          from_account: Optional[str] = None, to_account: Optional[str] = None,
                          description: str = "", metadata: Optional[Dict] = None) -> Transaction:
        
        self.transaction_counter += 1
        transaction_id = f"TXN{self.transaction_counter:08d}"
        
        transaction = Transaction(
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            amount=amount,
            from_account=from_account,
            to_account=to_account,
            description=description,
            metadata=metadata
        )
        
        is_valid, error_message = self.validate_transaction(transaction)
        
        if not is_valid:
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = error_message
            self.failed_transactions.append(transaction)
            self.transactions[transaction_id] = transaction
            return transaction
        
        try:
            if transaction_type == TransactionType.DEPOSIT:
                account = self.accounts[to_account]
                account.balance += transaction.amount
                account.last_modified = datetime.now()
                account.transaction_history.append(transaction_id)
            
            elif transaction_type == TransactionType.WITHDRAWAL:
                account = self.accounts[from_account]
                account.balance -= transaction.amount
                account.last_modified = datetime.now()
                account.transaction_history.append(transaction_id)
            
            elif transaction_type == TransactionType.TRANSFER:
                from_acc = self.accounts[from_account]
                to_acc = self.accounts[to_account]
                
                from_acc.balance -= transaction.amount
                to_acc.balance += transaction.amount
                
                from_acc.last_modified = datetime.now()
                to_acc.last_modified = datetime.now()
                
                from_acc.transaction_history.append(transaction_id)
                to_acc.transaction_history.append(transaction_id)
            
            elif transaction_type == TransactionType.PAYMENT:
                if from_account:
                    account = self.accounts[from_account]
                    account.balance -= transaction.amount
                    account.last_modified = datetime.now()
                    account.transaction_history.append(transaction_id)
            
            elif transaction_type == TransactionType.REFUND:
                if to_account:
                    account = self.accounts[to_account]
                    account.balance += transaction.amount
                    account.last_modified = datetime.now()
                    account.transaction_history.append(transaction_id)
            
            transaction.status = TransactionStatus.COMPLETED
            self.transactions[transaction_id] = transaction
            
        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = str(e)
            self.failed_transactions.append(transaction)
            self.transactions[transaction_id] = transaction
        
        return transaction
    
    def batch_process_transactions(self, transactions: List[Dict]) -> List[Transaction]:
        processed = []
        
        for txn_data in transactions:
            transaction = self.process_transaction(
                transaction_type=TransactionType(txn_data['type']),
                amount=Decimal(str(txn_data['amount'])),
                from_account=txn_data.get('from_account'),
                to_account=txn_data.get('to_account'),
                description=txn_data.get('description', ''),
                metadata=txn_data.get('metadata', {})
            )
            processed.append(transaction)
        
        return processed
    
    def get_transaction_history(self, account_id: str, limit: int = 100) -> List[Dict]:
        account = self.get_account(account_id)
        if not account:
            return []
        
        history = []
        for txn_id in account.transaction_history[-limit:]:
            if txn_id in self.transactions:
                history.append(self.transactions[txn_id].to_dict())
        
        return history
    
    def calculate_daily_totals(self, account_id: str) -> Dict:
        account = self.get_account(account_id)
        if not account:
            return {"error": "Account not found"}
        
        today = datetime.now().date()
        daily_deposits = Decimal('0')
        daily_withdrawals = Decimal('0')
        daily_transfers_out = Decimal('0')
        daily_transfers_in = Decimal('0')
        
        for txn_id in account.transaction_history:
            if txn_id in self.transactions:
                txn = self.transactions[txn_id]
                if txn.timestamp.date() == today and txn.status == TransactionStatus.COMPLETED:
                    if txn.transaction_type == TransactionType.DEPOSIT and txn.to_account == account_id:
                        daily_deposits += txn.amount
                    elif txn.transaction_type == TransactionType.WITHDRAWAL and txn.from_account == account_id:
                        daily_withdrawals += txn.amount
                    elif txn.transaction_type == TransactionType.TRANSFER:
                        if txn.from_account == account_id:
                            daily_transfers_out += txn.amount
                        elif txn.to_account == account_id:
                            daily_transfers_in += txn.amount
        
        return {
            "date": today.isoformat(),
            "deposits": float(daily_deposits),
            "withdrawals": float(daily_withdrawals),
            "transfers_out": float(daily_transfers_out),
            "transfers_in": float(daily_transfers_in),
            "net_change": float(daily_deposits + daily_transfers_in - daily_withdrawals - daily_transfers_out)
        }
    
    def export_account_statement(self, account_id: str, format: str = "json") -> Optional[str]:
        account = self.get_account(account_id)
        if not account:
            return None
        
        statement = {
            "account": account.to_dict(),
            "transactions": self.get_transaction_history(account_id),
            "daily_totals": self.calculate_daily_totals(account_id),
            "statement_date": datetime.now().isoformat()
        }
        
        if format == "json":
            return json.dumps(statement, indent=2)
        else:
            return str(statement)
    
    def reverse_transaction(self, transaction_id: str, reason: str = "Reversal") -> Optional[Transaction]:
        if transaction_id not in self.transactions:
            return None
        
        original = self.transactions[transaction_id]
        
        if original.status != TransactionStatus.COMPLETED:
            return None
        
        reversal_type = TransactionType.REFUND
        if original.transaction_type == TransactionType.DEPOSIT:
            reversal_type = TransactionType.WITHDRAWAL
        elif original.transaction_type == TransactionType.WITHDRAWAL:
            reversal_type = TransactionType.DEPOSIT
        
        reversal = self.process_transaction(
            transaction_type=reversal_type,
            amount=original.amount,
            from_account=original.to_account if original.transaction_type == TransactionType.DEPOSIT else original.from_account,
            to_account=original.from_account if original.transaction_type == TransactionType.WITHDRAWAL else original.to_account,
            description=f"{reason}: Reversal of {transaction_id}",
            metadata={"original_transaction": transaction_id, "reversal_reason": reason}
        )
        
        if reversal.status == TransactionStatus.COMPLETED:
            original.status = TransactionStatus.CANCELLED
        
        return reversal
    
    def get_account_summary(self) -> Dict:
        total_accounts = len(self.accounts)
        active_accounts = sum(1 for acc in self.accounts.values() if acc.is_active)
        total_balance = sum(acc.balance for acc in self.accounts.values())
        total_transactions = len(self.transactions)
        completed_transactions = sum(1 for txn in self.transactions.values() 
                                   if txn.status == TransactionStatus.COMPLETED)
        failed_transactions = len(self.failed_transactions)
        
        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "total_balance": float(total_balance),
            "total_transactions": total_transactions,
            "completed_transactions": completed_transactions,
            "failed_transactions": failed_transactions,
            "success_rate": (completed_transactions / total_transactions * 100) if total_transactions > 0 else 0
        }


def process_financial_transactions(transactions_data: List[Dict], accounts_data: List[Dict]) -> Dict:
    processor = TransactionProcessor()
    
    for acc_data in accounts_data:
        processor.create_account(
            account_id=acc_data['account_id'],
            initial_balance=Decimal(str(acc_data.get('initial_balance', 0))),
            account_type=acc_data.get('account_type', 'checking'),
            currency=acc_data.get('currency', 'USD')
        )
    
    processed_transactions = processor.batch_process_transactions(transactions_data)
    
    results = {
        "processed_count": len(processed_transactions),
        "successful": sum(1 for t in processed_transactions if t.status == TransactionStatus.COMPLETED),
        "failed": sum(1 for t in processed_transactions if t.status == TransactionStatus.FAILED),
        "transactions": [t.to_dict() for t in processed_transactions],
        "updated_balances": {
            acc_id: float(acc.balance) for acc_id, acc in processor.accounts.items()
        },
        "summary": processor.get_account_summary()
    }
    
    return results


if __name__ == "__main__":
    sample_accounts = [
        {"account_id": "ACC001", "initial_balance": 5000.00, "account_type": "checking"},
        {"account_id": "ACC002", "initial_balance": 10000.00, "account_type": "savings"},
        {"account_id": "ACC003", "initial_balance": 2500.00, "account_type": "checking"}
    ]
    
    sample_transactions = [
        {"type": "deposit", "amount": 1000.00, "to_account": "ACC001", "description": "Salary deposit"},
        {"type": "transfer", "amount": 500.00, "from_account": "ACC001", "to_account": "ACC002", "description": "Monthly savings"},
        {"type": "withdrawal", "amount": 200.00, "from_account": "ACC001", "description": "ATM withdrawal"},
        {"type": "payment", "amount": 150.00, "from_account": "ACC003", "description": "Utility bill"},
        {"type": "transfer", "amount": 750.00, "from_account": "ACC002", "to_account": "ACC003", "description": "Fund transfer"},
        {"type": "deposit", "amount": 2000.00, "to_account": "ACC002", "description": "Investment return"},
        {"type": "withdrawal", "amount": 100000.00, "from_account": "ACC001", "description": "Large withdrawal attempt"}
    ]
    
    result = process_financial_transactions(sample_transactions, sample_accounts)
    print(json.dumps(result, indent=2))