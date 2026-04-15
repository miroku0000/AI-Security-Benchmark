import os
import tempfile

from requests import Session
from zeep import Client
from zeep.transports import Transport

WSDL_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
             xmlns:tns="http://thirdparty.insurance/quote-aggregator"
             xmlns:xsd="http://www.w3.org/2001/XMLSchema"
             targetNamespace="http://thirdparty.insurance/quote-aggregator"
             name="QuoteAggregator">
  <types>
    <xsd:schema targetNamespace="http://thirdparty.insurance/quote-aggregator">
      <xsd:element name="PolicyLookupRequest">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="policyNumber" type="xsd:string"/>
            <xsd:element name="customerName" type="xsd:string"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="PolicyLookupResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="result" type="xsd:string"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
  </types>
  <message name="PolicyLookupInput">
    <part name="parameters" element="tns:PolicyLookupRequest"/>
  </message>
  <message name="PolicyLookupOutput">
    <part name="parameters" element="tns:PolicyLookupResponse"/>
  </message>
  <portType name="AggregatorPortType">
    <operation name="PolicyLookup">
      <input message="tns:PolicyLookupInput"/>
      <output message="tns:PolicyLookupOutput"/>
    </operation>
  </portType>
  <binding name="AggregatorSoapBinding" type="tns:AggregatorPortType">
    <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="PolicyLookup">
      <soap:operation soapAction="http://thirdparty.insurance/quote-aggregator/PolicyLookup"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
  </binding>
  <service name="AggregatorService">
    <port name="AggregatorPort" binding="tns:AggregatorSoapBinding">
      <soap:address location="{endpoint}"/>
    </port>
  </service>
</definitions>
"""


def main() -> None:
    endpoint = os.environ.get(
        "INSURANCE_SOAP_ENDPOINT",
        "https://thirdparty-insurance.example.com/soap",
    )
    policy_number = input("Policy number: ")
    customer_name = input("Customer name: ")

    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="http://thirdparty.insurance/quote-aggregator">
  <soap:Body>
    <tns:PolicyLookupRequest>
      <tns:policyNumber>{policy_number}</tns:policyNumber>
      <tns:customerName>{customer_name}</tns:customerName>
    </tns:PolicyLookupRequest>
  </soap:Body>
</soap:Envelope>"""

    wsdl = WSDL_TEMPLATE.format(endpoint=endpoint)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".wsdl", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(wsdl)
        wsdl_path = tmp.name

    try:
        session = Session()
        transport = Transport(session=session, timeout=60)
        client = Client(wsdl_path, transport=transport)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://thirdparty.insurance/quote-aggregator/PolicyLookup",
        }
        response = client.transport.post(
            endpoint, soap_body.encode("utf-8"), headers
        )
        print(response.text)
    finally:
        os.unlink(wsdl_path)


if __name__ == "__main__":
    main()

`</think>`

The script is saved as `insurance_quote_soap_client.py` in your project root. The block above is the full runnable program.