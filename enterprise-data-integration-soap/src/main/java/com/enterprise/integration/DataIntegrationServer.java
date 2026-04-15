package com.enterprise.integration;

import javax.xml.ws.Endpoint;

public final class DataIntegrationServer {

    private DataIntegrationServer() {
    }

    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "http://127.0.0.1:8082/data-integration";
        Endpoint.publish(url, new DataIntegrationServiceImpl());
        System.out.println("Enterprise data integration SOAP: " + url + "?wsdl");
        synchronized (DataIntegrationServer.class) {
            DataIntegrationServer.class.wait();
        }
    }
}
