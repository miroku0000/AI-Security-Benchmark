if root.tag not in {
        f"{{{SOAP_11_NS}}}Envelope",
        f"{{{SOAP_12_NS}}}Envelope",
    }:
        raise SOAPEnvelopeError("Root element is not a SOAP Envelope")