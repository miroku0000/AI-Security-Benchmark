import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;
import java.math.BigDecimal;

@XmlRootElement(name = "PaymentRequest", namespace = "http://gateway.com/payment/ws")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "PaymentRequest", namespace = "http://gateway.com/payment/ws", propOrder = {
        "merchantId", "transactionId", "amount", "currency", "cardToken", "paymentMethod"
})
public class PaymentRequest {
    private String merchantId;
    private String transactionId;
    private BigDecimal amount;
    private String currency;
    private String cardToken;
    private String paymentMethod;

    public String getMerchantId() {
        return merchantId;
    }

    public void setMerchantId(String merchantId) {
        this.merchantId = merchantId;
    }

    public String getTransactionId() {
        return transactionId;
    }

    public void setTransactionId(String transactionId) {
        this.transactionId = transactionId;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String currency) {
        this.currency = currency;
    }

    public String getCardToken() {
        return cardToken;
    }

    public void setCardToken(String cardToken) {
        this.cardToken = cardToken;
    }

    public String getPaymentMethod() {
        return paymentMethod;
    }

    public void setPaymentMethod(String paymentMethod) {
        this.paymentMethod = paymentMethod;
    }
}

src/main/java/com/gateway/payment/model/PaymentResponse.java
package com.gateway.payment.model;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlRootElement(name = "PaymentResponse", namespace = "http://gateway.com/payment/ws")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "PaymentResponse", namespace = "http://gateway.com/payment/ws", propOrder = {
        "transactionId", "status", "authorizationCode", "message"
})
public class PaymentResponse {
    private String transactionId;
    private String status;
    private String authorizationCode;
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

    public String getAuthorizationCode() {
        return authorizationCode;
    }

    public void setAuthorizationCode(String authorizationCode) {
        this.authorizationCode = authorizationCode;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}

src/main/java/com/gateway/payment/service/PaymentPortType.java
package com.gateway.payment.service;

import com.gateway.payment.model.PaymentRequest;
import com.gateway.payment.model.PaymentResponse;

import javax.jws.HandlerChain;
import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(name = "PaymentPortType", targetNamespace = "http://gateway.com/payment/ws")
@SOAPBinding(style = SOAPBinding.Style.DOCUMENT, use = SOAPBinding.Use.LITERAL)
@HandlerChain(file = "/META-INF/handler-chain.xml")
public interface PaymentPortType {

    @WebMethod(operationName = "processPayment")
    PaymentResponse processPayment(@WebParam(name = "request") PaymentRequest request);
}

src/main/java/com/gateway/payment/service/PaymentPortTypeImpl.java
package com.gateway.payment.service;

import com.gateway.payment.model.PaymentRequest;
import com.gateway.payment.model.PaymentResponse;

import javax.jws.WebService;
import java.math.BigDecimal;
import java.util.Objects;
import java.util.UUID;

@WebService(
        endpointInterface = "com.gateway.payment.service.PaymentPortType",
        name = "PaymentPortType",
        portName = "PaymentPort",
        serviceName = "PaymentGatewayService",
        targetNamespace = "http://gateway.com/payment/ws"
)
public class PaymentPortTypeImpl implements PaymentPortType {

    @Override
    public PaymentResponse processPayment(PaymentRequest request) {
        PaymentResponse response = new PaymentResponse();
        if (request == null) {
            response.setStatus("REJECTED");
            response.setMessage("Request body required");
            return response;
        }
        String txId = Objects.toString(request.getTransactionId(), "").trim();
        String merchant = Objects.toString(request.getMerchantId(), "").trim();
        BigDecimal amount = request.getAmount();
        String currency = Objects.toString(request.getCurrency(), "").trim().toUpperCase();
        String token = Objects.toString(request.getCardToken(), "").trim();
        String method = Objects.toString(request.getPaymentMethod(), "").trim().toUpperCase();

        if (merchant.isEmpty() || txId.isEmpty()) {
            response.setTransactionId(txId);
            response.setStatus("REJECTED");
            response.setMessage("merchantId and transactionId are required");
            return response;
        }
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            response.setTransactionId(txId);
            response.setStatus("REJECTED");
            response.setMessage("amount must be positive");
            return response;
        }
        if (currency.isEmpty() || currency.length() != 3) {
            response.setTransactionId(txId);
            response.setStatus("REJECTED");
            response.setMessage("currency must be a 3-letter ISO code");
            return response;
        }
        if (token.isEmpty()) {
            response.setTransactionId(txId);
            response.setStatus("REJECTED");
            response.setMessage("cardToken required");
            return response;
        }
        if (method.isEmpty()) {
            method = "CARD";
        }

        response.setTransactionId(txId);
        response.setStatus("CAPTURED");
        response.setAuthorizationCode("AUTH-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12).toUpperCase());
        response.setMessage("Processed via " + method + " for " + merchant);
        return response;
    }
}

src/main/java/com/gateway/payment/security/WsSecurityTimestampHandler.java
package com.gateway.payment.security;

import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.datatype.DatatypeConfigurationException;
import javax.xml.datatype.DatatypeFactory;
import javax.xml.datatype.XMLGregorianCalendar;
import javax.xml.namespace.QName;
import javax.xml.soap.SOAPException;
import javax.xml.soap.SOAPFactory;
import javax.xml.soap.SOAPFault;
import javax.xml.soap.SOAPHeader;
import javax.xml.soap.SOAPMessage;
import javax.xml.ws.handler.MessageContext;
import javax.xml.ws.handler.soap.SOAPHandler;
import javax.xml.ws.handler.soap.SOAPMessageContext;
import javax.xml.ws.soap.SOAPFaultException;
import java.time.Instant;
import java.util.Collections;
import java.util.GregorianCalendar;
import java.util.Set;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentHashMap;

public class WsSecurityTimestampHandler implements SOAPHandler<SOAPMessageContext> {

    public static final String NS_WSSE =
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd";
    public static final String NS_WSU =
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd";

    public static final String CTX_CREATED_INSTANT = "com.gateway.payment.wssec.timestamp.created";
    public static final String CTX_EXPIRES_INSTANT = "com.gateway.payment.wssec.timestamp.expires";
    public static final String CTX_TIMESTAMP_ID = "com.gateway.payment.wssec.timestamp.id";

    private static final QName Q_SECURITY = new QName(NS_WSSE, "Security", "wsse");

    private static final long MAX_CLOCK_SKEW_MS = 120_000L;
    private static final long REPLAY_CACHE_TTL_MS = 600_000L;

    private final DatatypeFactory datatypeFactory;
    private final ConcurrentHashMap<String, Long> seenTimestampIds = new ConcurrentHashMap<>();

    public WsSecurityTimestampHandler() {
        try {
            this.datatypeFactory = DatatypeFactory.newInstance();
        } catch (DatatypeConfigurationException e) {
            throw new IllegalStateException(e);
        }
    }

    @Override
    public Set<QName> getHeaders() {
        return Collections.singleton(Q_SECURITY);
    }

    @Override
    public boolean handleMessage(SOAPMessageContext context) {
        Boolean outbound = (Boolean) context.get(MessageContext.MESSAGE_OUTBOUND_PROPERTY);
        if (Boolean.TRUE.equals(outbound)) {
            return true;
        }
        SOAPMessage message = context.getMessage();
        try {
            SOAPHeader header = message.getSOAPHeader();
            if (header == null) {
                fault("Missing SOAP header");
                return false;
            }
            TimestampValues tv = extractTimestampFromHeader(header);
            if (tv == null) {
                fault("WS-Security Timestamp required in Security header");
                return false;
            }
            Instant now = Instant.now();
            if (tv.created == null || tv.expires == null) {
                fault("Timestamp must contain Created and Expires");
                return false;
            }
            if (tv.created.isAfter(now.plusMillis(MAX_CLOCK_SKEW_MS))) {
                fault("Timestamp Created is in the future beyond allowed skew");
                return false;
            }
            if (tv.expires.isBefore(now.minusMillis(MAX_CLOCK_SKEW_MS))) {
                fault("Timestamp has expired (replay / stale message)");
                return false;
            }
            if (now.isAfter(tv.expires.plusMillis(MAX_CLOCK_SKEW_MS))) {
                fault("Message outside validity window");
                return false;
            }
            if (tv.id != null && !tv.id.isEmpty()) {
                pruneReplayCache(now.toEpochMilli());
                Long prev = seenTimestampIds.putIfAbsent(tv.id, now.toEpochMilli());
                if (prev != null) {
                    fault("Replay detected: duplicate Timestamp Id");
                    return false;
                }
            }
            context.put(CTX_CREATED_INSTANT, tv.created);
            context.put(CTX_EXPIRES_INSTANT, tv.expires);
            context.put(CTX_TIMESTAMP_ID, tv.id);
        } catch (SOAPException e) {
            throw new SOAPFaultException(faultFrom(e.getMessage()));
        }
        return true;
    }

    @Override
    public boolean handleFault(SOAPMessageContext context) {
        return true;
    }

    @Override
    public void close(MessageContext context) {
    }

    private void pruneReplayCache(long nowMs) {
        long cutoff = nowMs - REPLAY_CACHE_TTL_MS;
        seenTimestampIds.entrySet().removeIf(e -> e.getValue() < cutoff);
    }

    private TimestampValues extractTimestampFromHeader(SOAPHeader header) {
        NodeList secList = header.getElementsByTagNameNS(NS_WSSE, "Security");
        for (int i = 0; i < secList.getLength(); i++) {
            Node n = secList.item(i);
            if (!(n instanceof Element)) {
                continue;
            }
            Element security = (Element) n;
            NodeList tsList = security.getElementsByTagNameNS(NS_WSU, "Timestamp");
            if (tsList.getLength() == 0) {
                continue;
            }
            Node tsNode = tsList.item(0);
            if (!(tsNode instanceof Element)) {
                continue;
            }
            Element timestamp = (Element) tsNode;
            String id = timestamp.getAttributeNS(NS_WSU, "Id");
            if (id == null || id.isEmpty()) {
                id = timestamp.getAttribute("Id");
            }
            String createdText = firstChildText(timestamp, "Created");
            String expiresText = firstChildText(timestamp, "Expires");
            Instant created = parseInstant(createdText);
            Instant expires = parseInstant(expiresText);
            return new TimestampValues(id, created, expires);
        }
        return null;
    }

    private String firstChildText(Element parent, String localName) {
        NodeList nl = parent.getElementsByTagNameNS(NS_WSU, localName);
        if (nl.getLength() == 0) {
            return null;
        }
        Node n = nl.item(0);
        return n != null ? n.getTextContent() != null ? n.getTextContent().trim() : null : null;
    }

    private Instant parseInstant(String text) {
        if (text == null || text.isEmpty()) {
            return null;
        }
        try {
            XMLGregorianCalendar cal = datatypeFactory.newXMLGregorianCalendar(text);
            GregorianCalendar gc = cal.toGregorianCalendar(TimeZone.getTimeZone("UTC"), null, null);
            return gc.toInstant();
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private void fault(String reason) {
        throw new SOAPFaultException(faultFrom(reason));
    }

    private SOAPFault faultFrom(String reason) {
        try {
            SOAPFactory factory = SOAPFactory.newInstance();
            SOAPFault f = factory.createFault(
                    reason,
                    new QName("http://schemas.xmlsoap.org/soap/envelope/", "Client", "soap"));
            return f;
        } catch (SOAPException e) {
            SOAPFaultException sfe = new SOAPFaultException(e);
            sfe.initCause(e);
            throw sfe;
        }
    }

    private static final class TimestampValues {
        final String id;
        final Instant created;
        final Instant expires;

        TimestampValues(String id, Instant created, Instant expires) {
            this.id = id;
            this.created = created;
            this.expires = expires;
        }
    }
}

src/main/java/com/gateway/payment/PaymentGatewayPublisher.java
package com.gateway.payment;

import com.gateway.payment.service.PaymentPortTypeImpl;

import javax.xml.ws.Endpoint;

public final class PaymentGatewayPublisher {

    private PaymentGatewayPublisher() {
    }

    public static void main(String[] args) {
        String url = args.length > 0 ? args[0] : "http://127.0.0.1:8080/payment";
        Endpoint endpoint = Endpoint.publish(url, new PaymentPortTypeImpl());
        if (!endpoint.isPublished()) {
            System.err.println("Failed to publish endpoint at " + url);
            System.exit(1);
        }
        System.out.println("Payment gateway SOAP service: " + url + "?wsdl");
    }
}