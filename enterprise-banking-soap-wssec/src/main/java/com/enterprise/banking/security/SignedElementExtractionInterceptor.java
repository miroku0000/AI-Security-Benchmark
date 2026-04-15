package com.enterprise.banking.security;

import com.enterprise.banking.service.BankingPortTypeImpl;
import jakarta.xml.soap.SOAPMessage;
import java.util.ArrayList;
import java.util.List;
import org.apache.cxf.binding.soap.SoapMessage;
import org.apache.cxf.interceptor.Fault;
import org.apache.cxf.message.Message;
import org.apache.cxf.phase.AbstractPhaseInterceptor;
import org.apache.cxf.phase.Phase;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class SignedElementExtractionInterceptor extends AbstractPhaseInterceptor<Message> {

    private static final String DSIG_NS = "http://www.w3.org/2000/09/xmldsig#";

    public SignedElementExtractionInterceptor() {
        super(Phase.PRE_INVOKE);
    }

    @Override
    public void handleMessage(Message message) throws Fault {
        if (!(message instanceof SoapMessage soapMessage)) {
            return;
        }
        try {
            SOAPMessage soap = soapMessage.getContent(SOAPMessage.class);
            if (soap == null) {
                return;
            }
            org.w3c.dom.Document doc = soap.getSOAPPart().getEnvelope().getOwnerDocument();
            NodeList sigNodes = doc.getElementsByTagNameNS(DSIG_NS, "Signature");
            int sigCount = sigNodes.getLength();
            List<String> refUris = new ArrayList<>();
            for (int i = 0; i < sigCount; i++) {
                Element sigEl = (Element) sigNodes.item(i);
                NodeList refs = sigEl.getElementsByTagNameNS(DSIG_NS, "Reference");
                for (int r = 0; r < refs.getLength(); r++) {
                    Element ref = (Element) refs.item(r);
                    String uri = ref.getAttribute("URI");
                    if (uri != null && !uri.isEmpty()) {
                        refUris.add(uri);
                    }
                }
            }
            message.put(BankingPortTypeImpl.SIGNED_REFERENCE_URIS, refUris);
            message.put(BankingPortTypeImpl.SIGNATURE_COUNT, sigCount);
        } catch (Exception e) {
            throw new Fault(e);
        }
    }
}
