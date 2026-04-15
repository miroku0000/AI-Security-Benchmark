The file has been written to `/Users/randy.flood/Documents/AI_Security_Benchmark/SamlServiceProvider.java`.

Key security measures included:
- **XXE prevention**: DTD declarations disabled, external entities disabled, XInclude disabled
- **Signature validation**: Verifies XML digital signatures against the configured IdP certificate, checks that signatures are children of Response or Assertion elements (prevents signature wrapping)
- **Condition validation**: Checks NotBefore/NotOnOrAfter with configurable clock skew, validates audience restriction
- **Session fixation prevention**: Invalidates existing session before creating a new one
- **Issuer validation**: Confirms the assertion came from the expected IdP