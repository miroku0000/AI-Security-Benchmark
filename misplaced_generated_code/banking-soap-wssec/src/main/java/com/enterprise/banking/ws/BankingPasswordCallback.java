package com.enterprise.banking.ws;

import org.apache.wss4j.common.ext.WSPasswordCallback;

import javax.security.auth.callback.Callback;
import javax.security.auth.callback.CallbackHandler;
import javax.security.auth.callback.UnsupportedCallbackException;
import java.io.IOException;

public class BankingPasswordCallback implements CallbackHandler {

    private static final String PASS = "changeit";

    @Override
    public void handle(Callback[] callbacks) throws IOException, UnsupportedCallbackException {
        for (Callback cb : callbacks) {
            if (cb instanceof WSPasswordCallback) {
                WSPasswordCallback pc = (WSPasswordCallback) cb;
                if (pc.getUsage() == WSPasswordCallback.DECRYPT || pc.getUsage() == WSPasswordCallback.SIGNATURE) {
                    pc.setPassword(PASS);
                }
            } else {
                throw new UnsupportedCallbackException(cb);
            }
        }
    }
}
