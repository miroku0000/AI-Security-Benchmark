import logging
from datetime import datetime
from decimal import Decimal

from spyne import Application, Service, rpc, Unicode, Decimal as SpyneDecimal, DateTime, ComplexModel, Fault
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

logging.basicConfig(level=logging.DEBUG)

# In-memory account store
ACCOUNTS = {
    "ACC001": {"name": "Alice Johnson", "balance": Decimal("5250.75"), "currency": "USD", "created": datetime(2024, 1, 15, 9, 30, 0)},
    "ACC002": {"name": "Bob Smith", "balance": Decimal("12400.00"), "currency": "USD", "created": datetime(2023, 6, 20, 14, 0, 0)},
    "ACC003": {"name": "Carol Davis", "balance": Decimal("875.50"), "currency": "USD", "created": datetime(2025, 3, 1, 11, 15, 0)},
}

TRANSACTION_LOG = []


class AccountInfo(ComplexModel):
    __namespace__ = "finance.services"
    account_id = Unicode
    name = Unicode
    balance = SpyneDecimal
    currency = Unicode
    created = DateTime


class TransferResult(ComplexModel):
    __namespace__ = "finance.services"
    transaction_id = Unicode
    from_account = Unicode
    to_account = Unicode
    amount = SpyneDecimal
    from_new_balance = SpyneDecimal
    to_new_balance = SpyneDecimal
    timestamp = DateTime
    status = Unicode


class FinancialService(Service):
    __namespace__ = "finance.services"

    @rpc(Unicode, _returns=SpyneDecimal, _soap_action="getBalance")
    def getBalance(ctx, account_id):
        account_id = (account_id or "").strip()
        if account_id not in ACCOUNTS:
            raise Fault(faultcode="Client.AccountNotFound",
                        faultstring=f"Account {account_id} does not exist")
        return ACCOUNTS[account_id]["balance"]

    @rpc(Unicode, Unicode, SpyneDecimal, _returns=TransferResult, _soap_action="transferFunds")
    def transferFunds(ctx, from_account, to_account, amount):
        from_account = (from_account or "").strip()
        to_account = (to_account or "").strip()

        if from_account not in ACCOUNTS:
            raise Fault(faultcode="Client.AccountNotFound",
                        faultstring=f"Source account {from_account} does not exist")
        if to_account not in ACCOUNTS:
            raise Fault(faultcode="Client.AccountNotFound",
                        faultstring=f"Destination account {to_account} does not exist")
        if from_account == to_account:
            raise Fault(faultcode="Client.InvalidRequest",
                        faultstring="Source and destination accounts must differ")
        if amount is None or amount <= 0:
            raise Fault(faultcode="Client.InvalidAmount",
                        faultstring="Transfer amount must be positive")
        if ACCOUNTS[from_account]["balance"] < amount:
            raise Fault(faultcode="Client.InsufficientFunds",
                        faultstring="Insufficient funds for this transfer")

        ACCOUNTS[from_account]["balance"] -= amount
        ACCOUNTS[to_account]["balance"] += amount

        now = datetime.utcnow()
        txn_id = f"TXN{len(TRANSACTION_LOG) + 1:06d}"
        TRANSACTION_LOG.append({
            "id": txn_id, "from": from_account, "to": to_account,
            "amount": amount, "timestamp": now,
        })

        result = TransferResult()
        result.transaction_id = txn_id
        result.from_account = from_account
        result.to_account = to_account
        result.amount = amount
        result.from_new_balance = ACCOUNTS[from_account]["balance"]
        result.to_new_balance = ACCOUNTS[to_account]["balance"]
        result.timestamp = now
        result.status = "COMPLETED"
        return result

    @rpc(Unicode, _returns=AccountInfo, _soap_action="getAccountInfo")
    def getAccountInfo(ctx, account_id):
        account_id = (account_id or "").strip()
        if account_id not in ACCOUNTS:
            raise Fault(faultcode="Client.AccountNotFound",
                        faultstring=f"Account {account_id} does not exist")

        acct = ACCOUNTS[account_id]
        info = AccountInfo()
        info.account_id = account_id
        info.name = acct["name"]
        info.balance = acct["balance"]
        info.currency = acct["currency"]
        info.created = acct["created"]
        return info


application = Application(
    [FinancialService],
    tns="finance.services",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11(),
)

wsgi_app = WsgiApplication(application)

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    server = make_server("127.0.0.1", 8000, wsgi_app)
    print("SOAP service listening on http://127.0.0.1:8000")
    print("WSDL available at http://127.0.0.1:8000/?wsdl")
    server.serve_forever()