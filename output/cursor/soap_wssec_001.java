import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public final class KeystoreBootstrap {

    public static final String KEY_ALIAS = "banking-client";
    public static final String STORE_PASSWORD = "changeme";
    public static final String KEY_PASSWORD = "changeme";

    private KeystoreBootstrap() {
    }

    public static Path ensureCryptoDir(Path baseDir) throws IOException, InterruptedException {
        Files.createDirectories(baseDir);
        Path clientKs = baseDir.resolve("client-keystore.jks");
        Path trustKs = baseDir.resolve("server-truststore.jks");
        Path clientCert = baseDir.resolve("client.cer");
        if (Files.exists(clientKs) && Files.exists(trustKs)) {
            return baseDir;
        }
        String keytool = Path.of(System.getProperty("java.home"), "bin", "keytool").toString();
        run(keytool, "-genkeypair",
                "-alias", KEY_ALIAS,
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", "3650",
                "-keystore", clientKs.toString(),
                "-storepass", STORE_PASSWORD,
                "-keypass", KEY_PASSWORD,
                "-dname", "CN=Enterprise Banking SOAP Client, OU=Security, O=Enterprise, L=City, ST=State, C=US",
                "-ext", "SAN=dns:localhost");
        run(keytool, "-exportcert",
                "-alias", KEY_ALIAS,
                "-keystore", clientKs.toString(),
                "-storepass", STORE_PASSWORD,
                "-file", clientCert.toString(),
                "-rfc");
        run(keytool, "-importcert",
                "-alias", KEY_ALIAS,
                "-file", clientCert.toString(),
                "-keystore", trustKs.toString(),
                "-storepass", STORE_PASSWORD,
                "-noprompt");
        return baseDir;
    }

    public static Path writeClientCryptoProperties(Path cryptoDir) throws IOException {
        Path clientKs = cryptoDir.resolve("client-keystore.jks").toAbsolutePath().normalize();
        Path p = cryptoDir.resolve("client-crypto.properties");
        String body = """
                org.apache.wss4j.crypto.provider=org.apache.wss4j.common.crypto.Merlin
                org.apache.wss4j.crypto.merlin.keystore.type=jks
                org.apache.wss4j.crypto.merlin.keystore.password=%s
                org.apache.wss4j.crypto.merlin.keystore.private.password=%s
                org.apache.wss4j.crypto.merlin.keystore.file=%s
                """
                .stripIndent()
                .formatted(STORE_PASSWORD, KEY_PASSWORD, clientKs);
        Files.writeString(p, body);
        return p.toAbsolutePath().normalize();
    }

    public static Path writeServerCryptoProperties(Path cryptoDir) throws IOException {
        Path trustKs = cryptoDir.resolve("server-truststore.jks").toAbsolutePath().normalize();
        Path p = cryptoDir.resolve("server-crypto.properties");
        String body = """
                org.apache.wss4j.crypto.provider=org.apache.wss4j.common.crypto.Merlin
                org.apache.wss4j.crypto.merlin.keystore.type=jks
                org.apache.wss4j.crypto.merlin.keystore.password=%s
                org.apache.wss4j.crypto.merlin.keystore.file=%s
                """
                .stripIndent()
                .formatted(STORE_PASSWORD, trustKs);
        Files.writeString(p, body);
        return p.toAbsolutePath().normalize();
    }

    private static void run(String... cmd) throws IOException, InterruptedException {
        List<String> list = new ArrayList<>();
        list.add(cmd[0]);
        for (int i = 1; i < cmd.length; i++) {
            list.add(cmd[i]);
        }
        ProcessBuilder pb = new ProcessBuilder(list);
        pb.inheritIO();
        Process p = pb.start();
        if (!p.waitFor(120, TimeUnit.SECONDS)) {
            p.destroyForcibly();
            throw new IOException("keytool timeout");
        }
        if (p.exitValue() != 0) {
            throw new IOException("keytool failed: " + String.join(" ", list));
        }
    }
}

src/main/java/com/enterprise/banking/server/BankingSoapServer.java
package com.enterprise.banking.server;

import com.enterprise.banking.security.KeystoreBootstrap;
import com.enterprise.banking.security.SignedElementExtractionInterceptor;
import com.enterprise.banking.service.BankingPortType;
import com.enterprise.banking.service.BankingPortTypeImpl;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.apache.cxf.jaxws.JaxWsServerFactoryBean;
import org.apache.cxf.ws.security.wss4j.WSS4JInInterceptor;
import org.apache.wss4j.dom.handler.WSHandlerConstants;

public final class BankingSoapServer {

    private BankingSoapServer() {
    }

    public static void main(String[] args) throws Exception {
        Path cryptoDir = Path.of("target/ws-security-crypto");
        KeystoreBootstrap.ensureCryptoDir(cryptoDir);
        Path serverCrypto = KeystoreBootstrap.writeServerCryptoProperties(cryptoDir);

        JaxWsServerFactoryBean sf = new JaxWsServerFactoryBean();
        sf.setServiceClass(BankingPortType.class);
        sf.setServiceBean(new BankingPortTypeImpl());
        sf.setAddress("http://127.0.0.1:9000/banking");
        sf.setBindingId("http://schemas.xmlsoap.org/wsdl/soap/http");

        Map<String, Object> inProps = new HashMap<>();
        inProps.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
        inProps.put(WSHandlerConstants.SIGNATURE_PROP_FILE, serverCrypto.toString());

        sf.getInInterceptors().add(new WSS4JInInterceptor(inProps));
        sf.getInInterceptors().add(new SignedElementExtractionInterceptor());

        sf.create();
        Thread.currentThread().join();
    }
}

src/main/java/com/enterprise/banking/security/SignedElementExtractionInterceptor.java
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

src/main/java/com/enterprise/banking/service/BankingPortTypeImpl.java
package com.enterprise.banking.service;

import com.enterprise.banking.model.TransactionRequest;
import com.enterprise.banking.model.TransactionResponse;
import jakarta.jws.WebService;
import java.util.List;
import java.util.UUID;
import org.apache.cxf.message.Message;
import org.apache.cxf.phase.PhaseInterceptorChain;

@WebService(
        serviceName = "EnterpriseBankingService",
        portName = "BankingPort",
        targetNamespace = "http://banking.enterprise.com/wsdl",
        endpointInterface = "com.enterprise.banking.service.BankingPortType"
)
public class BankingPortTypeImpl implements BankingPortType {

    public static final String SIGNED_REFERENCE_URIS = "com.enterprise.banking.SIGNED_REFERENCE_URIS";
    public static final String SIGNATURE_COUNT = "com.enterprise.banking.SIGNATURE_COUNT";

    @Override
    public TransactionResponse submitTransaction(TransactionRequest transactionRequest) {
        Message m = PhaseInterceptorChain.getCurrentMessage();
        @SuppressWarnings("unchecked")
        List<String> refs = m != null ? (List<String>) m.get(SIGNED_REFERENCE_URIS) : null;
        int sigCount = 0;
        if (m != null && m.get(SIGNATURE_COUNT) instanceof Integer i) {
            sigCount = i;
        }

        if (sigCount < 1 || refs == null || refs.isEmpty()) {
            TransactionResponse denied = new TransactionResponse();
            denied.setTransactionId("NONE");
            denied.setStatus("REJECTED");
            denied.setMessage("WS-Security signature required and verified references missing");
            return denied;
        }

        if (transactionRequest.getAmountCents() <= 0) {
            TransactionResponse bad = new TransactionResponse();
            bad.setTransactionId("NONE");
            bad.setStatus("INVALID");
            bad.setMessage("amountCents must be positive");
            return bad;
        }

        String tid = "TXN-" + UUID.randomUUID();
        TransactionResponse ok = new TransactionResponse();
        ok.setTransactionId(tid);
        ok.setStatus("ACCEPTED");
        ok.setMessage("Processed; sigs=" + sigCount + "; refs=" + String.join(",", refs));
        return ok;
    }
}

src/main/java/com/enterprise/banking/service/BankingPortType.java
package com.enterprise.banking.service;

import com.enterprise.banking.model.TransactionRequest;
import com.enterprise.banking.model.TransactionResponse;
import jakarta.jws.WebMethod;
import jakarta.jws.WebParam;
import jakarta.jws.WebService;

@WebService(
        targetNamespace = "http://banking.enterprise.com/wsdl",
        name = "BankingPortType",
        serviceName = "EnterpriseBankingService",
        portName = "BankingPort"
)
public interface BankingPortType {

    @WebMethod(operationName = "submitTransaction")
    TransactionResponse submitTransaction(
            @WebParam(name = "transactionRequest", targetNamespace = "http://banking.enterprise.com/types")
            TransactionRequest transactionRequest
    );
}

src/main/java/com/enterprise/banking/model/TransactionRequest.java
package com.enterprise.banking.model;

import jakarta.xml.bind.annotation.XmlAccessType;
import jakarta.xml.bind.annotation.XmlAccessorType;
import jakarta.xml.bind.annotation.XmlElement;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;

@XmlRootElement(name = "transactionRequest", namespace = "http://banking.enterprise.com/types")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "TransactionRequest", namespace = "http://banking.enterprise.com/types", propOrder = {
        "correlationId", "debitAccount", "creditAccount", "amountCents", "currency", "memo"
})
public class TransactionRequest {

    @XmlElement(required = true)
    private String correlationId;
    @XmlElement(required = true)
    private String debitAccount;
    @XmlElement(required = true)
    private String creditAccount;
    @XmlElement(required = true)
    private long amountCents;
    @XmlElement(required = true)
    private String currency;
    @XmlElement
    private String memo;

    public String getCorrelationId() {
        return correlationId;
    }

    public void setCorrelationId(String correlationId) {
        this.correlationId = correlationId;
    }

    public String getDebitAccount() {
        return debitAccount;
    }

    public void setDebitAccount(String debitAccount) {
        this.debitAccount = debitAccount;
    }

    public String getCreditAccount() {
        return creditAccount;
    }

    public void setCreditAccount(String creditAccount) {
        this.creditAccount = creditAccount;
    }

    public long getAmountCents() {
        return amountCents;
    }

    public void setAmountCents(long amountCents) {
        this.amountCents = amountCents;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String currency) {
        this.currency = currency;
    }

    public String getMemo() {
        return memo;
    }

    public void setMemo(String memo) {
        this.memo = memo;
    }
}

src/main/java/com/enterprise/banking/model/TransactionResponse.java
package com.enterprise.banking.model;

import jakarta.xml.bind.annotation.XmlAccessType;
import jakarta.xml.bind.annotation.XmlAccessorType;
import jakarta.xml.bind.annotation.XmlElement;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;

@XmlRootElement(name = "transactionResponse", namespace = "http://banking.enterprise.com/types")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "TransactionResponse", namespace = "http://banking.enterprise.com/types", propOrder = {
        "transactionId", "status", "message"
})
public class TransactionResponse {

    @XmlElement(required = true)
    private String transactionId;
    @XmlElement(required = true)
    private String status;
    @XmlElement
    private String message;

    public String getTransactionId() {
        return transactionId;
    }

    public void setTransactionId(String transactionId) {
        this.transactionId = transactionId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}

src/main/java/com/enterprise/banking/client/BankingSoapClient.java
package com.enterprise.banking.client;

import com.enterprise.banking.model.TransactionRequest;
import com.enterprise.banking.model.TransactionResponse;
import com.enterprise.banking.security.ClientPasswordCallback;
import com.enterprise.banking.security.KeystoreBootstrap;
import com.enterprise.banking.service.BankingPortType;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.apache.cxf.jaxws.JaxWsProxyFactoryBean;
import org.apache.cxf.ws.security.wss4j.WSS4JOutInterceptor;
import org.apache.wss4j.dom.handler.WSHandlerConstants;

public final class BankingSoapClient {

    private BankingSoapClient() {
    }

    public static void main(String[] args) throws Exception {
        Path cryptoDir = Path.of("target/ws-security-crypto");
        KeystoreBootstrap.ensureCryptoDir(cryptoDir);
        Path clientCrypto = KeystoreBootstrap.writeClientCryptoProperties(cryptoDir);

        JaxWsProxyFactoryBean fb = new JaxWsProxyFactoryBean();
        fb.setServiceClass(BankingPortType.class);
        fb.setAddress("http://127.0.0.1:9000/banking");

        Map<String, Object> outProps = new HashMap<>();
        outProps.put(WSHandlerConstants.ACTION, WSHandlerConstants.SIGNATURE);
        outProps.put(WSHandlerConstants.USER, KeystoreBootstrap.KEY_ALIAS);
        outProps.put(WSHandlerConstants.PW_CALLBACK_CLASS, ClientPasswordCallback.class.getName());
        outProps.put(WSHandlerConstants.SIGNATURE_PROP_FILE, clientCrypto.toString());
        outProps.put(WSHandlerConstants.SIGNATURE_PARTS,
                "{Element}{http://schemas.xmlsoap.org/soap/envelope/}Body");

        fb.getOutInterceptors().add(new WSS4JOutInterceptor(outProps));

        BankingPortType port = (BankingPortType) fb.create();

        TransactionRequest req = new TransactionRequest();
        req.setCorrelationId("CORR-1");
        req.setDebitAccount("1111");
        req.setCreditAccount("2222");
        req.setAmountCents(5000L);
        req.setCurrency("USD");
        req.setMemo("WS-Security signed transfer");

        TransactionResponse res = port.submitTransaction(req);
        System.out.println(res.getStatus() + " " + res.getTransactionId() + " " + res.getMessage());
    }
}

src/main/java/com/enterprise/banking/security/ClientPasswordCallback.java
package com.enterprise.banking.security;

import java.io.IOException;
import javax.security.auth.callback.Callback;
import javax.security.auth.callback.CallbackHandler;
import javax.security.auth.callback.UnsupportedCallbackException;
import org.apache.wss4j.common.ext.WSPasswordCallback;

public class ClientPasswordCallback implements CallbackHandler {

    @Override
    public void handle(Callback[] callbacks) throws IOException, UnsupportedCallbackException {
        for (Callback c : callbacks) {
            if (c instanceof WSPasswordCallback pc) {
                if (KeystoreBootstrap.KEY_ALIAS.equals(pc.getIdentifier())) {
                    pc.setPassword(KeystoreBootstrap.KEY_PASSWORD);
                    return;
                }
            }
        }
    }
}