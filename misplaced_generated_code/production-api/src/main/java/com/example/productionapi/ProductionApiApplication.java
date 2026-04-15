package com.example.productionapi;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;

@SpringBootApplication
public class ProductionApiApplication {

    private static final Logger log = LoggerFactory.getLogger(ProductionApiApplication.class);

    public static void main(String[] args) {
        log.info("Starting production API application");
        SpringApplication.run(ProductionApiApplication.class, args);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        log.info("Application startup complete; ready to accept traffic");
    }
}
