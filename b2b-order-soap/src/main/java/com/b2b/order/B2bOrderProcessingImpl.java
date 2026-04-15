package com.b2b.order;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Iterator;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;
import javax.annotation.Resource;
import javax.jws.WebService;
import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBException;
import javax.xml.bind.Unmarshaller;
import javax.xml.soap.SOAPBody;
import javax.xml.soap.SOAPElement;
import javax.xml.soap.SOAPException;
import javax.xml.ws.WebServiceContext;
import javax.xml.ws.WebServiceException;

@WebService(
        serviceName = "B2bOrderProcessingService",
        portName = "B2bOrderProcessingPort",
        name = "B2bOrderProcessing",
        targetNamespace = "http://b2b.order.com/soap",
        endpointInterface = "com.b2b.order.B2bOrderProcessing"
)
public class B2bOrderProcessingImpl implements B2bOrderProcessing {

    private static final AtomicLong SEQUENCE = new AtomicLong();

    @Resource
    private WebServiceContext webServiceContext;

    @Override
    public OrderProcessingResult submitOrder(SubmitOrderRequest orderRequest) {
        SubmitOrderRequest request = parseOrderRequestFromSoapBody();
        if (request == null) {
            request = orderRequest;
        }
        if (request == null) {
            throw new WebServiceException("Missing or invalid orderRequest in SOAP body");
        }
        if (request.getLineItems() == null || request.getLineItems().isEmpty()) {
            OrderProcessingResult err = new OrderProcessingResult();
            err.setOrderId("");
            err.setTotalAmount(BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP));
            err.setStatus("REJECTED");
            err.setMessage("At least one line item is required");
            return err;
        }
        BigDecimal total = BigDecimal.ZERO;
        for (OrderLineItem line : request.getLineItems()) {
            if (line.getSku() == null || line.getSku().trim().isEmpty()) {
                return reject("Each line item must include a SKU");
            }
            if (line.getQuantity() <= 0) {
                return reject("Quantity must be positive for SKU " + line.getSku());
            }
            if (line.getUnitPrice() == null || line.getUnitPrice().signum() < 0) {
                return reject("Unit price must be non-negative for SKU " + line.getSku());
            }
            BigDecimal lineTotal = line.getUnitPrice().multiply(BigDecimal.valueOf(line.getQuantity()));
            total = total.add(lineTotal);
        }
        total = total.setScale(2, RoundingMode.HALF_UP);
        String orderId = "B2B-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase()
                + "-" + SEQUENCE.incrementAndGet();
        OrderProcessingResult result = new OrderProcessingResult();
        result.setOrderId(orderId);
        result.setTotalAmount(total);
        result.setStatus("ACCEPTED");
        result.setMessage("Order processed for PO " + request.getPurchaseOrderNumber()
                + " (buyer " + request.getBuyerAccountId() + ")");
        return result;
    }

    private static OrderProcessingResult reject(String message) {
        OrderProcessingResult err = new OrderProcessingResult();
        err.setOrderId("");
        err.setTotalAmount(BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP));
        err.setStatus("REJECTED");
        err.setMessage(message);
        return err;
    }

    private SubmitOrderRequest parseOrderRequestFromSoapBody() {
        try {
            if (webServiceContext == null) {
                return null;
            }
            javax.xml.ws.handler.MessageContext mc = webServiceContext.getMessageContext();
            if (mc == null) {
                return null;
            }
            javax.xml.ws.soap.SOAPMessageContext smc = (javax.xml.ws.soap.SOAPMessageContext) mc;
            SOAPBody body = smc.getMessage().getSOAPBody();
            if (body == null) {
                return null;
            }
            JAXBContext jc = JAXBContext.newInstance(SubmitOrderRequest.class);
            Unmarshaller unmarshaller = jc.createUnmarshaller();
            return unmarshalOrderRequest(body, unmarshaller);
        } catch (SOAPException | JAXBException e) {
            throw new WebServiceException("Failed to parse SOAP body", e);
        }
    }

    private SubmitOrderRequest unmarshalOrderRequest(SOAPBody body, Unmarshaller unmarshaller)
            throws JAXBException {
        Iterator<?> it = body.getChildElements();
        while (it.hasNext()) {
            Object node = it.next();
            if (!(node instanceof SOAPElement)) {
                continue;
            }
            SOAPElement root = (SOAPElement) node;
            SubmitOrderRequest direct = tryUnmarshal(unmarshaller, root);
            if (direct != null) {
                return direct;
            }
            Iterator<?> inner = root.getChildElements();
            while (inner.hasNext()) {
                Object child = inner.next();
                if (child instanceof SOAPElement) {
                    SubmitOrderRequest nested = tryUnmarshal(unmarshaller, (SOAPElement) child);
                    if (nested != null) {
                        return nested;
                    }
                }
            }
        }
        return null;
    }

    private SubmitOrderRequest tryUnmarshal(Unmarshaller unmarshaller, SOAPElement element)
            throws JAXBException {
        if ("orderRequest".equals(element.getLocalName())) {
            Object o = unmarshaller.unmarshal(element);
            if (o instanceof SubmitOrderRequest) {
                return (SubmitOrderRequest) o;
            }
        }
        return null;
    }
}
