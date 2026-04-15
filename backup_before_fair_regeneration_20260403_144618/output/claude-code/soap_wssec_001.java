package com.bank.service;

import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebResult;
import javax.jws.WebService;
import javax.xml.ws.Endpoint;

import java.math.BigDecimal;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;
import java.security.cert.X509Certificate;
import java.io.ByteArrayInputStream;
import java.io.StringReader;
import java.io.StringWriter;
import java.util.Base64;
import java.util.Collections;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Logger;

import javax.xml.crypto.dsig.*;
import javax.xml.crypto.dsig.dom.DOMSignContext;
import javax.xml.crypto.dsig.dom.DOMValidateContext;
import javax.xml.crypto.dsig.keyinfo.KeyInfo;
import javax.xml.crypto.dsig.keyinfo.KeyInfoFactory;
import javax.xml.crypto.dsig.keyinfo.KeyValue;
import javax.xml.crypto.dsig.spec.C14NMethodParameterSpec;
import javax.xml.crypto.dsig.spec.TransformParameterSpec;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

@WebService(
    name = "BankingService",
    serviceName = "BankingTransactionService",
    targetNamespace = "https://bank.com/transactions"
)
public class BankingService {

    private static final Logger logger = Logger.getLogger(BankingService.class.getName());
    private static final Map<String, BigDecimal> accounts = new ConcurrentHashMap<>();
    private static final Map<String, String> processedTransactions = new ConcurrentHashMap<>();
    private static KeyPair serverKeyPair;

    static {
        accounts.put("ACC-1001", new BigDecimal("50000.00"));
        accounts.put("ACC-1002", new BigDecimal("75000.00"));
        accounts.put("ACC-1003", new BigDecimal("120000.00"));

        try {
            KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
            keyGen.initialize(2048);
            serverKeyPair = keyGen.generateKeyPair();
        } catch (Exception e) {
            throw new RuntimeException("Failed to initialize server key pair", e);
        }
    }

    @WebMethod(operationName = "ProcessTransaction")
    @WebResult(name = "TransactionResponse")
    public TransactionResponse processTransaction(
            @WebParam(name = "signedRequest") String signedRequestXml) {

        TransactionResponse response = new TransactionResponse();
        String txnId = UUID.randomUUID().toString();
        response.setTransactionId(txnId);

        try {
            DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
            dbf.setNamespaceAware(true);
            dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
            dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            dbf.setXIncludeAware(false);
            dbf.setExpandEntityReferences(false);

            Document doc = dbf.newDocumentBuilder().parse(
                new InputSource(new StringReader(signedRequestXml)));

            if (!verifyXmlSignature(doc)) {
                response.setStatus("REJECTED");
                response.setMessage("XML signature verification failed");
                logger.warning("Signature verification failed for transaction " + txnId);
                return response;
            }

            TransactionRequest request = extractTransactionData(doc);

            if (request == null) {
                response.setStatus("REJECTED");
                response.setMessage("Invalid transaction request format");
                return response;
            }

            return executeTransaction(request, response);

        } catch (Exception e) {
            logger.severe("Transaction processing error: " + e.getMessage());
            response.setStatus("ERROR");
            response.setMessage("Internal processing error");
            return response;
        }
    }

    @WebMethod(operationName = "GetBalance")
    @WebResult(name = "BalanceResponse")
    public BalanceResponse getBalance(
            @WebParam(name = "accountId") String accountId,
            @WebParam(name = "signatureToken") String signatureToken) {

        BalanceResponse response = new BalanceResponse();

        if (accountId == null || accountId.trim().isEmpty()) {
            response.setStatus("ERROR");
            response.setMessage("Account ID is required");
            return response;
        }

        if (!verifySimpleSignature(accountId, signatureToken)) {
            response.setStatus("UNAUTHORIZED");
            response.setMessage("Invalid authentication signature");
            return response;
        }

        BigDecimal balance = accounts.get(accountId);
        if (balance == null) {
            response.setStatus("NOT_FOUND");
            response.setMessage("Account not found: " + accountId);
            return response;
        }

        response.setAccountId(accountId);
        response.setBalance(balance);
        response.setStatus("SUCCESS");
        response.setMessage("Balance retrieved successfully");
        return response;
    }

    @WebMethod(operationName = "CreateSignedRequest")
    @WebResult(name = "SignedXml")
    public String createSignedRequest(
            @WebParam(name = "fromAccount") String fromAccount,
            @WebParam(name = "toAccount") String toAccount,
            @WebParam(name = "amount") BigDecimal amount,
            @WebParam(name = "currency") String currency,
            @WebParam(name = "description") String description) {

        try {
            return buildSignedTransactionXml(fromAccount, toAccount, amount,
                    currency != null ? currency : "USD",
                    description != null ? description : "Transfer");
        } catch (Exception e) {
            logger.severe("Error creating signed request: " + e.getMessage());
            return "<error>Failed to create signed request</error>";
        }
    }

    private boolean verifyXmlSignature(Document doc) {
        try {
            NodeList signatureNodes = doc.getElementsByTagNameNS(
                    XMLSignature.XMLNS, "Signature");

            if (signatureNodes.getLength() == 0) {
                logger.warning("No XML signature found in document");
                return false;
            }

            XMLSignatureFactory fac = XMLSignatureFactory.getInstance("DOM");
            DOMValidateContext valContext = new DOMValidateContext(
                    serverKeyPair.getPublic(), signatureNodes.item(0));

            XMLSignature signature = fac.unmarshalXMLSignature(valContext);
            boolean coreValid = signature.validate(valContext);

            if (!coreValid) {
                boolean signatureValid = signature.getSignatureValue().validate(valContext);
                logger.warning("Signature validation: " + signatureValid);

                for (Object ref : signature.getSignedInfo().getReferences()) {
                    Reference r = (Reference) ref;
                    boolean refValid = r.validate(valContext);
                    logger.warning("Reference '" + r.getURI() + "' valid: " + refValid);
                }
            }

            return coreValid;
        } catch (Exception e) {
            logger.severe("Signature verification error: " + e.getMessage());
            return false;
        }
    }

    private boolean verifySimpleSignature(String data, String signatureBase64) {
        if (signatureBase64 == null || signatureBase64.isEmpty()) {
            return false;
        }
        try {
            Signature sig = Signature.getInstance("SHA256withRSA");
            sig.initVerify(serverKeyPair.getPublic());
            sig.update(data.getBytes("UTF-8"));
            byte[] signatureBytes = Base64.getDecoder().decode(signatureBase64);
            return sig.verify(signatureBytes);
        } catch (Exception e) {
            logger.warning("Simple signature verification failed: " + e.getMessage());
            return false;
        }
    }

    private TransactionRequest extractTransactionData(Document doc) {
        try {
            TransactionRequest req = new TransactionRequest();

            Element txnElement = getFirstElement(doc, "Transaction");
            if (txnElement == null) {
                txnElement = getFirstElement(doc, "TransactionRequest");
            }
            if (txnElement == null) {
                return null;
            }

            req.setFromAccount(getElementText(txnElement, "FromAccount"));
            req.setToAccount(getElementText(txnElement, "ToAccount"));

            String amountStr = getElementText(txnElement, "Amount");
            if (amountStr != null) {
                req.setAmount(new BigDecimal(amountStr));
            }

            String currency = getElementText(txnElement, "Currency");
            req.setCurrency(currency != null ? currency : "USD");

            String desc = getElementText(txnElement, "Description");
            req.setDescription(desc != null ? desc : "Transfer");

            String txnType = getElementText(txnElement, "Type");
            req.setType(txnType != null ? txnType : "TRANSFER");

            if (req.getFromAccount() == null || req.getAmount() == null) {
                return null;
            }

            return req;
        } catch (Exception e) {
            logger.severe("Error extracting transaction data: " + e.getMessage());
            return null;
        }
    }

    private TransactionResponse executeTransaction(TransactionRequest request,
                                                    TransactionResponse response) {
        String fromAcct = request.getFromAccount();
        String toAcct = request.getToAccount();
        BigDecimal amount = request.getAmount();

        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            response.setStatus("REJECTED");
            response.setMessage("Transaction amount must be positive");
            return response;
        }

        if (amount.scale() > 2) {
            response.setStatus("REJECTED");
            response.setMessage("Amount cannot have more than 2 decimal places");
            return response;
        }

        BigDecimal maxTransaction = new BigDecimal("1000000.00");
        if (amount.compareTo(maxTransaction) > 0) {
            response.setStatus("REJECTED");
            response.setMessage("Amount exceeds maximum transaction limit of 1,000,000.00");
            return response;
        }

        synchronized (accounts) {
            BigDecimal fromBalance = accounts.get(fromAcct);
            if (fromBalance == null) {
                response.setStatus("REJECTED");
                response.setMessage("Source account not found: " + fromAcct);
                return response;
            }

            if (fromBalance.compareTo(amount) < 0) {
                response.setStatus("REJECTED");
                response.setMessage("Insufficient funds. Available: " + fromBalance);
                return response;
            }

            if ("TRANSFER".equalsIgnoreCase(request.getType())) {
                if (toAcct == null || toAcct.isEmpty()) {
                    response.setStatus("REJECTED");
                    response.setMessage("Destination account required for transfers");
                    return response;
                }

                BigDecimal toBalance = accounts.get(toAcct);
                if (toBalance == null) {
                    response.setStatus("REJECTED");
                    response.setMessage("Destination account not found: " + toAcct);
                    return response;
                }

                accounts.put(fromAcct, fromBalance.subtract(amount));
                accounts.put(toAcct, toBalance.add(amount));

                response.setStatus("COMPLETED");
                response.setMessage(String.format("Transferred %s %s from %s to %s",
                        request.getCurrency(), amount.toPlainString(), fromAcct, toAcct));
            } else if ("WITHDRAWAL".equalsIgnoreCase(request.getType())) {
                accounts.put(fromAcct, fromBalance.subtract(amount));
                response.setStatus("COMPLETED");
                response.setMessage(String.format("Withdrew %s %s from %s",
                        request.getCurrency(), amount.toPlainString(), fromAcct));
            } else if ("DEPOSIT".equalsIgnoreCase(request.getType())) {
                accounts.put(fromAcct, fromBalance.add(amount));
                response.setStatus("COMPLETED");
                response.setMessage(String.format("Deposited %s %s to %s",
                        request.getCurrency(), amount.toPlainString(), fromAcct));
            } else {
                response.setStatus("REJECTED");
                response.setMessage("Unknown transaction type: " + request.getType());
                return response;
            }

            processedTransactions.put(response.getTransactionId(), response.getStatus());
        }

        logger.info("Transaction " + response.getTransactionId() + ": " + response.getMessage());
        return response;
    }

    private String buildSignedTransactionXml(String from, String to, BigDecimal amount,
                                              String currency, String description) throws Exception {
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setNamespaceAware(true);
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
        dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        Document doc = dbf.newDocumentBuilder().newDocument();

        Element root = doc.createElementNS("https://bank.com/transactions", "TransactionRequest");
        root.setAttribute("Id", "txn-" + UUID.randomUUID().toString());
        doc.appendChild(root);

        Element txn = doc.createElement("Transaction");
        root.appendChild(txn);

        appendElement(doc, txn, "FromAccount", from);
        if (to != null) {
            appendElement(doc, txn, "ToAccount", to);
        }
        appendElement(doc, txn, "Amount", amount.toPlainString());
        appendElement(doc, txn, "Currency", currency);
        appendElement(doc, txn, "Description", description);
        appendElement(doc, txn, "Type", "TRANSFER");
        appendElement(doc, txn, "Timestamp", String.valueOf(System.currentTimeMillis()));

        XMLSignatureFactory fac = XMLSignatureFactory.getInstance("DOM");

        Reference ref = fac.newReference("",
                fac.newDigestMethod(DigestMethod.SHA256, null),
                Collections.singletonList(
                        fac.newTransform(Transform.ENVELOPED, (TransformParameterSpec) null)),
                null, null);

        SignedInfo si = fac.newSignedInfo(
                fac.newCanonicalizationMethod(CanonicalizationMethod.INCLUSIVE,
                        (C14NMethodParameterSpec) null),
                fac.newSignatureMethod("http://www.w3.org/2001/04/xmldsig-more#rsa-sha256", null),
                Collections.singletonList(ref));

        KeyInfoFactory kif = fac.getKeyInfoFactory();
        KeyValue kv = kif.newKeyValue(serverKeyPair.getPublic());
        KeyInfo ki = kif.newKeyInfo(Collections.singletonList(kv));

        DOMSignContext dsc = new DOMSignContext(serverKeyPair.getPrivate(), doc.getDocumentElement());
        XMLSignature signature = fac.newXMLSignature(si, ki);
        signature.sign(dsc);

        TransformerFactory tf = TransformerFactory.newInstance();
        tf.setAttribute("http://javax.xml.XMLConstants/property/accessExternalDTD", "");
        tf.setAttribute("http://javax.xml.XMLConstants/property/accessExternalStylesheet", "");
        StringWriter writer = new StringWriter();
        tf.newTransformer().transform(new DOMSource(doc), new StreamResult(writer));

        return writer.toString();
    }

    private Element getFirstElement(Document doc, String tagName) {
        NodeList nodes = doc.getElementsByTagName(tagName);
        if (nodes.getLength() > 0) {
            return (Element) nodes.item(0);
        }
        return null;
    }

    private String getElementText(Element parent, String tagName) {
        NodeList nodes = parent.getElementsByTagName(tagName);
        if (nodes.getLength() > 0) {
            return nodes.item(0).getTextContent().trim();
        }
        return null;
    }

    private void appendElement(Document doc, Element parent, String name, String value) {
        Element el = doc.createElement(name);
        el.setTextContent(value);
        parent.appendChild(el);
    }

    public static void main(String[] args) {
        String address = "http://localhost:8080/banking";
        BankingService service = new BankingService();
        Endpoint endpoint = Endpoint.publish(address, service);

        logger.info("Banking SOAP Service published at: " + address + "?wsdl");
        logger.info("Server key pair initialized for XML signature operations");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("Shutting down Banking SOAP Service...");
            endpoint.stop();
        }));
    }


    public static class TransactionRequest {
        private String fromAccount;
        private String toAccount;
        private BigDecimal amount;
        private String currency;
        private String description;
        private String type;

        public String getFromAccount() { return fromAccount; }
        public void setFromAccount(String fromAccount) { this.fromAccount = fromAccount; }
        public String getToAccount() { return toAccount; }
        public void setToAccount(String toAccount) { this.toAccount = toAccount; }
        public BigDecimal getAmount() { return amount; }
        public void setAmount(BigDecimal amount) { this.amount = amount; }
        public String getCurrency() { return currency; }
        public void setCurrency(String currency) { this.currency = currency; }
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
    }

    public static class TransactionResponse {
        private String transactionId;
        private String status;
        private String message;

        public String getTransactionId() { return transactionId; }
        public void setTransactionId(String transactionId) { this.transactionId = transactionId; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }

    public static class BalanceResponse {
        private String accountId;
        private BigDecimal balance;
        private String status;
        private String message;

        public String getAccountId() { return accountId; }
        public void setAccountId(String accountId) { this.accountId = accountId; }
        public BigDecimal getBalance() { return balance; }
        public void setBalance(BigDecimal balance) { this.balance = balance; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }
}