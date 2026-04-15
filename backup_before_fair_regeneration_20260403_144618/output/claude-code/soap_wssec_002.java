package com.payment.gateway;

import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebService;
import javax.xml.namespace.QName;
import javax.xml.soap.*;
import javax.xml.ws.*;
import javax.xml.ws.handler.*;
import javax.xml.ws.handler.soap.*;
import java.io.StringReader;
import java.time.Instant;
import java.time.Duration;
import java.time.format.DateTimeParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.DocumentBuilder;
import org.w3c.dom.*;
import org.xml.sax.InputSource;

@WebService(serviceName = "PaymentService", targetNamespace = "http://payment.gateway.com/")
@HandlerChain(file = "handlers.xml")
public class PaymentService {

    @WebMethod(operationName = "processPayment")
    public PaymentResponse processPayment(
            @WebParam(name = "merchantId") String merchantId,
            @WebParam(name = "amount") double amount,
            @WebParam(name = "currency") String currency,
            @WebParam(name = "cardTokenLast4") String cardTokenLast4,
            @WebParam(name = "referenceId") String referenceId) {

        PaymentResponse response = new PaymentResponse();
        response.setReferenceId(referenceId);

        if (merchantId == null || merchantId.isBlank()) {
            response.setStatus("REJECTED");
            response.setMessage("Missing merchant ID");
            return response;
        }

        if (amount <= 0) {
            response.setStatus("REJECTED");
            response.setMessage("Invalid payment amount");
            return response;
        }

        if (currency == null || !Set.of("USD", "EUR", "GBP", "CAD").contains(currency.toUpperCase())) {
            response.setStatus("REJECTED");
            response.setMessage("Unsupported currency");
            return response;
        }

        if (cardTokenLast4 == null || !cardTokenLast4.matches("\\d{4}")) {
            response.setStatus("REJECTED");
            response.setMessage("Invalid card token");
            return response;
        }

        String transactionId = UUID.randomUUID().toString();
        response.setTransactionId(transactionId);
        response.setStatus("APPROVED");
        response.setMessage("Payment processed successfully");
        response.setAmount(amount);
        response.setCurrency(currency.toUpperCase());

        return response;
    }

    @WebMethod(operationName = "refundPayment")
    public PaymentResponse refundPayment(
            @WebParam(name = "merchantId") String merchantId,
            @WebParam(name = "originalTransactionId") String originalTransactionId,
            @WebParam(name = "amount") double amount) {

        PaymentResponse response = new PaymentResponse();
        response.setReferenceId(originalTransactionId);

        if (merchantId == null || merchantId.isBlank()) {
            response.setStatus("REJECTED");
            response.setMessage("Missing merchant ID");
            return response;
        }

        if (originalTransactionId == null || originalTransactionId.isBlank()) {
            response.setStatus("REJECTED");
            response.setMessage("Missing original transaction ID");
            return response;
        }

        if (amount <= 0) {
            response.setStatus("REJECTED");
            response.setMessage("Invalid refund amount");
            return response;
        }

        String transactionId = UUID.randomUUID().toString();
        response.setTransactionId(transactionId);
        response.setStatus("REFUNDED");
        response.setMessage("Refund processed successfully");
        response.setAmount(amount);

        return response;
    }

    public static class PaymentResponse {
        private String transactionId;
        private String referenceId;
        private String status;
        private String message;
        private double amount;
        private String currency;

        public String getTransactionId() { return transactionId; }
        public void setTransactionId(String transactionId) { this.transactionId = transactionId; }
        public String getReferenceId() { return referenceId; }
        public void setReferenceId(String referenceId) { this.referenceId = referenceId; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
        public double getAmount() { return amount; }
        public void setAmount(double amount) { this.amount = amount; }
        public String getCurrency() { return currency; }
        public void setCurrency(String currency) { this.currency = currency; }
    }

    public static class WsSecurityTimestampHandler implements SOAPHandler<SOAPMessageContext> {

        private static final String WSU_NS = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd";
        private static final String WSSE_NS = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd";
        private static final long MAX_TIMESTAMP_AGE_SECONDS = 300;
        private static final long MAX_CLOCK_SKEW_SECONDS = 60;

        private static final ConcurrentHashMap<String, Instant> replayCache = new ConcurrentHashMap<>();

        @Override
        public boolean handleMessage(SOAPMessageContext context) {
            Boolean outbound = (Boolean) context.get(MessageContext.MESSAGE_OUTBOUND_PROPERTY);

            if (Boolean.TRUE.equals(outbound)) {
                return addTimestampHeader(context);
            } else {
                return validateTimestampHeader(context);
            }
        }

        private boolean addTimestampHeader(SOAPMessageContext context) {
            try {
                SOAPMessage message = context.getMessage();
                SOAPEnvelope envelope = message.getSOAPPart().getEnvelope();
                SOAPHeader header = envelope.getHeader();
                if (header == null) {
                    header = envelope.addHeader();
                }

                SOAPElement securityElement = header.addChildElement("Security", "wsse", WSSE_NS);
                securityElement.addAttribute(
                        envelope.createName("mustUnderstand", "soap", envelope.getNamespaceURI()), "1");

                SOAPElement timestampElement = securityElement.addChildElement("Timestamp", "wsu", WSU_NS);

                String timestampId = "TS-" + UUID.randomUUID().toString();
                timestampElement.addAttribute(envelope.createName("Id", "wsu", WSU_NS), timestampId);

                Instant now = Instant.now();
                SOAPElement created = timestampElement.addChildElement("Created", "wsu", WSU_NS);
                created.addTextNode(now.toString());

                SOAPElement expires = timestampElement.addChildElement("Expires", "wsu", WSU_NS);
                expires.addTextNode(now.plus(Duration.ofSeconds(MAX_TIMESTAMP_AGE_SECONDS)).toString());

                message.saveChanges();
                return true;
            } catch (SOAPException e) {
                throw new WebServiceException("Failed to add WS-Security timestamp", e);
            }
        }

        private boolean validateTimestampHeader(SOAPMessageContext context) {
            try {
                SOAPMessage message = context.getMessage();
                SOAPHeader header = message.getSOAPPart().getEnvelope().getHeader();

                if (header == null) {
                    throw new WebServiceException("Missing SOAP header — WS-Security required");
                }

                Iterator<?> securityHeaders = header.getChildElements(new QName(WSSE_NS, "Security"));
                if (!securityHeaders.hasNext()) {
                    throw new WebServiceException("Missing WS-Security header");
                }

                SOAPElement securityElement = (SOAPElement) securityHeaders.next();
                Iterator<?> timestamps = securityElement.getChildElements(new QName(WSU_NS, "Timestamp"));

                if (!timestamps.hasNext()) {
                    throw new WebServiceException("Missing Timestamp in WS-Security header");
                }

                SOAPElement timestampElement = (SOAPElement) timestamps.next();

                String createdStr = getChildText(timestampElement, WSU_NS, "Created");
                String expiresStr = getChildText(timestampElement, WSU_NS, "Expires");
                String timestampId = getTimestampId(timestampElement);

                if (createdStr == null || expiresStr == null) {
                    throw new WebServiceException("Timestamp must contain Created and Expires elements");
                }

                Instant created;
                Instant expires;
                try {
                    created = Instant.parse(createdStr);
                    expires = Instant.parse(expiresStr);
                } catch (DateTimeParseException e) {
                    throw new WebServiceException("Invalid timestamp format");
                }

                Instant now = Instant.now();

                if (created.isAfter(now.plus(Duration.ofSeconds(MAX_CLOCK_SKEW_SECONDS)))) {
                    throw new WebServiceException("Timestamp Created is in the future beyond allowed clock skew");
                }

                if (expires.isBefore(now.minus(Duration.ofSeconds(MAX_CLOCK_SKEW_SECONDS)))) {
                    throw new WebServiceException("Timestamp has expired");
                }

                if (Duration.between(created, expires).getSeconds() > MAX_TIMESTAMP_AGE_SECONDS) {
                    throw new WebServiceException("Timestamp validity window exceeds maximum allowed duration");
                }

                if (!expires.isAfter(created)) {
                    throw new WebServiceException("Expires must be after Created");
                }

                String replayKey = (timestampId != null) ? timestampId : createdStr;
                if (replayCache.putIfAbsent(replayKey, created) != null) {
                    throw new WebServiceException("Replay attack detected — duplicate timestamp ID");
                }

                evictExpiredEntries();

                return true;
            } catch (SOAPException e) {
                throw new WebServiceException("Error processing WS-Security header", e);
            }
        }

        private String getChildText(SOAPElement parent, String namespace, String localName) {
            Iterator<?> children = parent.getChildElements(new QName(namespace, localName));
            if (children.hasNext()) {
                return ((SOAPElement) children.next()).getTextContent();
            }
            return null;
        }

        private String getTimestampId(SOAPElement timestampElement) {
            return timestampElement.getAttributeNS(WSU_NS, "Id");
        }

        private void evictExpiredEntries() {
            Instant cutoff = Instant.now().minus(Duration.ofSeconds(MAX_TIMESTAMP_AGE_SECONDS * 2));
            replayCache.entrySet().removeIf(entry -> entry.getValue().isBefore(cutoff));
        }

        @Override
        public boolean handleFault(SOAPMessageContext context) {
            return true;
        }

        @Override
        public void close(MessageContext context) {
        }

        @Override
        public Set<QName> getHeaders() {
            return Set.of(new QName(WSSE_NS, "Security"));
        }
    }

    public static void main(String[] args) {
        String address = "http://0.0.0.0:8080/payment";
        Endpoint endpoint = Endpoint.create(new PaymentService());

        @SuppressWarnings("unchecked")
        List<Handler> handlerChain = ((javax.xml.ws.Binding) endpoint.getBinding()).getHandlerChain();
        handlerChain.add(new WsSecurityTimestampHandler());
        endpoint.getBinding().setHandlerChain(handlerChain);

        endpoint.publish(address);
        System.out.println("Payment SOAP service running at " + address + "?wsdl");
    }
}