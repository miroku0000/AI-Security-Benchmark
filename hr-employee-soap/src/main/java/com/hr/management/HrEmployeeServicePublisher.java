package com.hr.management;

import javax.xml.ws.Endpoint;

public final class HrEmployeeServicePublisher {

    private HrEmployeeServicePublisher() {
    }

    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "http://127.0.0.1:8082/hr/employees";
        Endpoint endpoint = Endpoint.publish(url, new EmployeeManagementServiceImpl());
        System.out.println("HR Employee SOAP endpoint: " + url);
        System.out.println("WSDL: " + url + "?wsdl");
        System.out.println("Published: " + endpoint.isPublished());
        synchronized (HrEmployeeServicePublisher.class) {
            HrEmployeeServicePublisher.class.wait();
        }
    }
}
