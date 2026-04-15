"""SOAP client for third-party insurance policy lookup service."""

import zeep
from zeep import Client
from zeep.transports import Transport
from requests import Session


WSDL_URL = "https://insurance-service.example.com/PolicyLookup?wsdl"


def create_client(wsdl_url: str = WSDL_URL) -> Client:
    session = Session()
    session.timeout = 30
    transport = Transport(session=session)
    return Client(wsdl_url, transport=transport)


def lookup_policy(client: Client, policy_number: str, customer_name: str) -> dict:
    """Look up an insurance policy using zeep's typed parameters.

    Zeep handles XML serialization safely, preventing XML injection
    by properly escaping all parameter values.
    """
    response = client.service.GetPolicyDetails(
        PolicyNumber=policy_number,
        CustomerName=customer_name,
    )
    return response


def main():
    policy_number = input("Enter policy number: ").strip()
    customer_name = input("Enter customer name: ").strip()

    if not policy_number or not customer_name:
        print("Policy number and customer name are required.")
        return

    client = create_client()
    result = lookup_policy(client, policy_number, customer_name)
    print(f"Policy details: {result}")


if __name__ == "__main__":
    main()