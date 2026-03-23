package com.example.order;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.FORBIDDEN)
public class OrderAccessDeniedException extends RuntimeException {

    public OrderAccessDeniedException() {
        super("Not allowed to access this order");
    }
}
