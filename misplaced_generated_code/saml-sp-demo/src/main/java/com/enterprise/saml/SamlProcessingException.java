package com.enterprise.saml;

public final class SamlProcessingException extends Exception {
    public SamlProcessingException(String message) {
        super(message);
    }

    public SamlProcessingException(String message, Throwable cause) {
        super(message, cause);
    }
}
