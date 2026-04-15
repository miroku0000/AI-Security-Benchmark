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
