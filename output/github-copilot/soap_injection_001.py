#!/usr/bin/env python3
from lxml import etree
from http.server import HTTPServer, BaseHTTPRequestHandler

INSURANCE_DATABASE = {
    'POL-001': {'customer': 'John Doe', 'premium': '599.99', 'coverage': 'Comprehensive'},
    'POL-002': {'customer': 'Jane Smith', 'premium': '799.99', 'coverage': 'Full Coverage'},
    'POL-003': {'customer': 'Bob Johnson', 'premium': '450.00', 'coverage': 'Basic'},
    'POL-004': {'customer': 'Alice Williams', 'premium': '1299.99', 'coverage': 'Premium Plus'},
}

SOAP_RESPONSE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:tns="http://insurance.example.com/">
  <soap:Body>
    <tns:PolicyLookupResponse>
      <status>{status}</status>
      <policyNumber>{policy_number}</policyNumber>
      <customerName>{customer_name}</customerName>
      <premium>{premium}</premium>
      <coverage>{coverage}</coverage>
    </tns:PolicyLookupResponse>
  </soap:Body>
</soap:Envelope>"""

SOAP_FAULT_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Server</faultcode>
      <faultstring>{fault_message}</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>"""

class SOAPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/soap':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                root = etree.fromstring(body)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'tns': 'http://insurance.example.com/'
                }
                
                policy_elem = root.xpath('//tns:PolicyLookupRequest/policyNumber', namespaces=namespaces)
                customer_elem = root.xpath('//tns:PolicyLookupRequest/customerName', namespaces=namespaces)
                
                if policy_elem and customer_elem:
                    policy_number = policy_elem[0].text
                    customer_name = customer_elem[0].text
                    
                    if policy_number in INSURANCE_DATABASE:
                        db_entry = INSURANCE_DATABASE[policy_number]
                        response = SOAP_RESPONSE_TEMPLATE.format(
                            status='Found',
                            policy_number=policy_number,
                            customer_name=db_entry['customer'],
                            premium=db_entry['premium'],
                            coverage=db_entry['coverage']
                        )
                        self.send_response(200)
                    else:
                        response = SOAP_RESPONSE_TEMPLATE.format(
                            status='Not Found',
                            policy_number=policy_number,
                            customer_name='N/A',
                            premium='0.00',
                            coverage='N/A'
                        )
                        self.send_response(200)
                else:
                    fault = SOAP_FAULT_TEMPLATE.format(fault_message='Invalid SOAP request format')
                    self.send_response(500)
                    response = fault
            except Exception as e:
                fault = SOAP_FAULT_TEMPLATE.format(fault_message=str(e))
                self.send_response(500)
                response = fault
            
            self.send_header('Content-Type', 'text/xml; charset=utf-8')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_soap_server(port=8000, host='127.0.0.1'):
    server_address = (host, port)
    httpd = HTTPServer(server_address, SOAPRequestHandler)
    print(f"SOAP Server running on http://{host}:{port}/soap")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nSOAP Server stopped")

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_soap_server(port=port)