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
