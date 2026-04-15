import java.math.BigDecimal;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "OrderLineItem", namespace = "http://b2b.order.com/soap", propOrder = {
        "sku", "unitPrice", "quantity"
})
public class OrderLineItem {

    @XmlElement(name = "sku", namespace = "http://b2b.order.com/soap", required = true)
    private String sku;

    @XmlElement(name = "unitPrice", namespace = "http://b2b.order.com/soap", required = true)
    private BigDecimal unitPrice;

    @XmlElement(name = "quantity", namespace = "http://b2b.order.com/soap", required = true)
    private int quantity;

    public String getSku() {
        return sku;
    }

    public void setSku(String sku) {
        this.sku = sku;
    }

    public BigDecimal getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(BigDecimal unitPrice) {
        this.unitPrice = unitPrice;
    }

    public int getQuantity() {
        return quantity;
    }

    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }
}

package com.b2b.order;

import java.util.ArrayList;
import java.util.List;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlElementWrapper;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlRootElement(name = "orderRequest", namespace = "http://b2b.order.com/soap")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "SubmitOrderRequest", namespace = "http://b2b.order.com/soap", propOrder = {
        "buyerAccountId", "purchaseOrderNumber", "lineItems"
})
public class SubmitOrderRequest {

    @XmlElement(name = "buyerAccountId", namespace = "http://b2b.order.com/soap", required = true)
    private String buyerAccountId;

    @XmlElement(name = "purchaseOrderNumber", namespace = "http://b2b.order.com/soap", required = true)
    private String purchaseOrderNumber;

    @XmlElementWrapper(name = "lineItems", namespace = "http://b2b.order.com/soap")
    @XmlElement(name = "lineItem", namespace = "http://b2b.order.com/soap")
    private List<OrderLineItem> lineItems = new ArrayList<>();

    public String getBuyerAccountId() {
        return buyerAccountId;
    }

    public void setBuyerAccountId(String buyerAccountId) {
        this.buyerAccountId = buyerAccountId;
    }

    public String getPurchaseOrderNumber() {
        return purchaseOrderNumber;
    }

    public void setPurchaseOrderNumber(String purchaseOrderNumber) {
        this.purchaseOrderNumber = purchaseOrderNumber;
    }

    public List<OrderLineItem> getLineItems() {
        return lineItems;
    }

    public void setLineItems(List<OrderLineItem> lineItems) {
        this.lineItems = lineItems != null ? lineItems : new ArrayList<>();
    }
}

package com.b2b.order;

import java.math.BigDecimal;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlRootElement(name = "orderResult", namespace = "http://b2b.order.com/soap")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "OrderProcessingResult", namespace = "http://b2b.order.com/soap", propOrder = {
        "orderId", "totalAmount", "status", "message"
})
public class OrderProcessingResult {

    @XmlElement(name = "orderId", namespace = "http://b2b.order.com/soap", required = true)
    private String orderId;

    @XmlElement(name = "totalAmount", namespace = "http://b2b.order.com/soap", required = true)
    private BigDecimal totalAmount;

    @XmlElement(name = "status", namespace = "http://b2b.order.com/soap", required = true)
    private String status;

    @XmlElement(name = "message", namespace = "http://b2b.order.com/soap")
    private String message;

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    public BigDecimal getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(BigDecimal totalAmount) {
        this.totalAmount = totalAmount;
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

package com.b2b.order;

import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebResult;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(name = "B2bOrderProcessing", targetNamespace = "http://b2b.order.com/soap")
@SOAPBinding(style = SOAPBinding.Style.DOCUMENT, use = SOAPBinding.Use.LITERAL)
public interface B2bOrderProcessing {

    @WebMethod(operationName = "SubmitOrder")
    @WebResult(name = "orderResult", targetNamespace = "http://b2b.order.com/soap")
    OrderProcessingResult submitOrder(
            @WebParam(name = "orderRequest", targetNamespace = "http://b2b.order.com/soap")
            SubmitOrderRequest orderRequest);
}

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

package com.b2b.order;

import javax.xml.ws.Endpoint;

public final class B2bOrderServer {

    private B2bOrderServer() {
    }

    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "http://127.0.0.1:8081/b2b-order";
        Endpoint.publish(url, new B2bOrderProcessingImpl());
        System.out.println("B2B order SOAP service: " + url + "?wsdl");
        synchronized (B2bOrderServer.class) {
            B2bOrderServer.class.wait();
        }
    }
}