package com.gateway.payment;

import java.math.BigDecimal;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import javax.annotation.Resource;
import javax.jws.WebService;
import javax.xml.ws.WebServiceContext;
import javax.xml.ws.handler.MessageContext;

@WebService(
        endpointInterface = "com.gateway.payment.PaymentPort",
        serviceName = "PaymentService",
        portName = "PaymentPort",
        targetNamespace = "http://payment.gateway.com/soap")
public class PaymentServiceImpl implements PaymentPort {

    private static final BigDecimal MAX_SINGLE_CHARGE = new BigDecimal("50000.00");

    @Resource
    private WebServiceContext wsContext;

    @Override
    public PaymentResponse processPayment(PaymentRequest request) {
        TimestampToken token = resolveTimestampFromContext();
        PaymentResponse response = new PaymentResponse();
        if (token != null) {
            response.setWsuTimestampCreated(DateTimeFormatter.ISO_INSTANT.format(token.getCreated()));
            response.setWsuTimestampExpires(DateTimeFormatter.ISO_INSTANT.format(token.getExpires()));
        }
        if (request == null) {
            response.setStatus("DECLINED");
            response.setDetail("Missing request body");
            return response;
        }
        if (isBlank(request.getMerchantId())) {
            response.setStatus("DECLINED");
            response.setDetail("merchantId required");
            return response;
        }
        if (isBlank(request.getTransactionId())) {
            response.setStatus("DECLINED");
            response.setDetail("transactionId required");
            return response;
        }
        if (request.getAmount() == null) {
            response.setStatus("DECLINED");
            response.setDetail("amount required");
            return response;
        }
        if (isBlank(request.getCurrency()) || request.getCurrency().length() != 3) {
            response.setStatus("DECLINED");
            response.setDetail("currency must be ISO 4217 (3 letters)");
            return response;
        }
        if (isBlank(request.getInstrumentToken())) {
            response.setStatus("DECLINED");
            response.setDetail("instrumentToken required");
            return response;
        }
        if (request.getAmount().signum() <= 0) {
            response.setStatus("DECLINED");
            response.setDetail("amount must be positive");
            return response;
        }
        if (request.getAmount().compareTo(MAX_SINGLE_CHARGE) > 0) {
            response.setStatus("DECLINED");
            response.setDetail("amount exceeds gateway limit");
            return response;
        }
        if (request.getInstrumentToken().startsWith("BAD")) {
            response.setStatus("DECLINED");
            response.setDetail("instrument rejected");
            return response;
        }
        response.setStatus("APPROVED");
        response.setAuthorizationCode("AUTH-" + request.getTransactionId());
        response.setDetail("captured");
        return response;
    }

    private TimestampToken resolveTimestampFromContext() {
        if (wsContext == null) {
            return null;
        }
        MessageContext mc = wsContext.getMessageContext();
        if (mc == null) {
            return null;
        }
        Object raw = mc.get(TimestampSecurityHandler.TIMESTAMP_CONTEXT_KEY);
        if (raw instanceof TimestampToken) {
            return (TimestampToken) raw;
        }
        if (raw == null && mc instanceof Map) {
            Object alt = ((Map<?, ?>) mc).get(TimestampSecurityHandler.TIMESTAMP_CONTEXT_KEY);
            if (alt instanceof TimestampToken) {
                return (TimestampToken) alt;
            }
        }
        return null;
    }

    private static boolean isBlank(String s) {
        return s == null || s.trim().isEmpty();
    }
}
