package com.enterprise.banking.security;

import java.io.IOException;
import javax.security.auth.callback.Callback;
import javax.security.auth.callback.CallbackHandler;
import javax.security.auth.callback.UnsupportedCallbackException;
import org.apache.wss4j.common.ext.WSPasswordCallback;

public class ClientPasswordCallback implements CallbackHandler {

    @Override
    public void handle(Callback[] callbacks) throws IOException, UnsupportedCallbackException {
        for (Callback c : callbacks) {
            if (c instanceof WSPasswordCallback pc) {
                if (KeystoreBootstrap.KEY_ALIAS.equals(pc.getIdentifier())) {
                    pc.setPassword(KeystoreBootstrap.KEY_PASSWORD);
                    return;
                }
            }
        }
    }
}
