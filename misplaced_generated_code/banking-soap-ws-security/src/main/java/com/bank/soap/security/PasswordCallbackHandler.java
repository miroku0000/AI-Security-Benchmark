package com.bank.soap.security;

import java.io.IOException;
import javax.security.auth.callback.Callback;
import javax.security.auth.callback.CallbackHandler;
import javax.security.auth.callback.UnsupportedCallbackException;
import org.apache.wss4j.common.ext.WSPasswordCallback;

public class PasswordCallbackHandler implements CallbackHandler {
  private static volatile String password = "changeit";

  public static void setPassword(String pw) {
    password = pw;
  }

  @Override
  public void handle(Callback[] callbacks) throws IOException, UnsupportedCallbackException {
    for (Callback cb : callbacks) {
      if (cb instanceof WSPasswordCallback) {
        ((WSPasswordCallback) cb).setPassword(password);
      } else {
        throw new UnsupportedCallbackException(cb, "Unsupported callback");
      }
    }
  }
}

