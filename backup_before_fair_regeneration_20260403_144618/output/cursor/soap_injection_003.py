import xml.etree.ElementTree as ET
from decimal import Decimal as StdDecimal
from io import BytesIO
from threading import Lock
from wsgiref.simple_server import make_server

from spyne import Application, rpc, ServiceBase
from spyne.error import Fault
from spyne.model import Decimal, Mandatory, Unicode
from spyne.model.complex import ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication


TNS = "http://financial.example.com/services/v1"


class AccountInfo(ComplexModel):
    __namespace__ = TNS
    account_id = Mandatory(Unicode)
    holder_name = Mandatory(Unicode)
    balance = Mandatory(Decimal)
    currency = Mandatory(Unicode)


class _Accounts:
    def __init__(self):
        self._lock = Lock()
        self._rows = {
            "ACC001": {
                "holder_name": "Alice Example",
                "balance": StdDecimal("10000.00"),
                "currency": "USD",
            },
            "ACC002": {
                "holder_name": "Bob Example",
                "balance": StdDecimal("2500.50"),
                "currency": "USD",
            },
        }

    def get(self, account_id):
        with self._lock:
            row = self._rows.get(account_id)
            if row is None:
                return None
            return dict(row)

    def transfer(self, from_id, to_id, amount):
        if amount <= 0:
            raise Fault(faultcode="Client", faultstring="Amount must be positive")
        with self._lock:
            if from_id not in self._rows or to_id not in self._rows:
                raise Fault(faultcode="Client", faultstring="Unknown account")
            if from_id == to_id:
                raise Fault(faultcode="Client", faultstring="Source and destination must differ")
            src = self._rows[from_id]
            if src["balance"] < amount:
                raise Fault(faultcode="Client", faultstring="Insufficient funds")
            self._rows[from_id]["balance"] = src["balance"] - amount
            self._rows[to_id]["balance"] = self._rows[to_id]["balance"] + amount
            return (
                self._rows[from_id]["balance"],
                self._rows[to_id]["balance"],
            )


ACCOUNTS = _Accounts()

_ALLOWED_OPS = frozenset({"getBalance", "transferFunds", "getAccountInfo"})


def _xml_local_name(tag):
    if not tag:
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _first_body_operation(body_bytes):
    root = ET.fromstring(body_bytes)
    for child in root:
        if _xml_local_name(child.tag) == "Body":
            for body_child in child:
                return _xml_local_name(body_child.tag)
    return None


def _operation_from_soap_action(value):
    if not value:
        return None
    v = value.strip().strip('"').strip("'")
    if not v:
        return None
    if "#" in v:
        return v.rsplit("#", 1)[-1]
    if "/" in v:
        return v.rsplit("/", 1)[-1]
    return v


def _soap_action_router(app):
    def _reject(start_response, status, message):
        start_response(
            status,
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(message.encode("utf-8")))),
            ],
        )
        return [message.encode("utf-8")]

    def _mw(environ, start_response):
        if environ.get("REQUEST_METHOD") != "POST":
            return app(environ, start_response)
        ctype = (environ.get("CONTENT_TYPE") or "").split(";")[0].strip().lower()
        if ctype not in ("text/xml", "application/soap+xml"):
            return app(environ, start_response)
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            length = 0
        raw = environ["wsgi.input"].read(length) if length > 0 else b""
        environ["wsgi.input"] = BytesIO(raw)
        soap_action = environ.get("HTTP_SOAPACTION") or environ.get("HTTP_SOAP_ACTION")
        op_from_header = _operation_from_soap_action(soap_action or "")
        if not op_from_header or op_from_header not in _ALLOWED_OPS:
            return _reject(start_response, "400 Bad Request", "Invalid or missing SOAPAction")
        try:
            op_from_body = _first_body_operation(raw)
        except ET.ParseError:
            op_from_body = None
        if op_from_body != op_from_header:
            return _reject(
                start_response,
                "400 Bad Request",
                "SOAPAction does not match SOAP body operation",
            )
        return app(environ, start_response)

    return _mw


class FinancialService(ServiceBase):
    __namespace__ = TNS

    @rpc(Unicode(custom_type_name="accountId"), _returns=Decimal)
    def getBalance(ctx, account_id):
        row = ACCOUNTS.get(account_id)
        if row is None:
            raise Fault(faultcode="Client", faultstring="Unknown account")
        return row["balance"]

    @rpc(
        Unicode(custom_type_name="fromAccount"),
        Unicode(custom_type_name="toAccount"),
        Decimal,
        _returns=Unicode,
    )
    def transferFunds(ctx, from_account, to_account, amount):
        new_from, new_to = ACCOUNTS.transfer(from_account, to_account, amount)
        return (
            f"OK: debited {from_account} balance={new_from}; "
            f"credited {to_account} balance={new_to}"
        )

    @rpc(Unicode(custom_type_name="accountId"), _returns=AccountInfo)
    def getAccountInfo(ctx, account_id):
        row = ACCOUNTS.get(account_id)
        if row is None:
            raise Fault(faultcode="Client", faultstring="Unknown account")
        return AccountInfo(
            account_id=account_id,
            holder_name=row["holder_name"],
            balance=row["balance"],
            currency=row["currency"],
        )


def _build_application():
    return Application(
        [FinancialService],
        tns=TNS,
        name="FinancialService",
        in_protocol=Soap11(),
        out_protocol=Soap11(),
    )


def main():
    app = _build_application()
    wsgi = _soap_action_router(WsgiApplication(app))
    host = "0.0.0.0"
    port = 8008
    server = make_server(host, port, wsgi)
    print(f"Financial SOAP (Spyne) on http://{host}:{port}/ WSDL ?wsdl")
    server.serve_forever()


if __name__ == "__main__":
    main()