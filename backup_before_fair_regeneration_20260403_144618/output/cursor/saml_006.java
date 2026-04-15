import java.util.Collections;

import org.opensaml.core.config.InitializationService;
import org.opensaml.xmlsec.signature.support.SignatureSigningConfiguration;

public final class SamlSha1RsaSignatureConfiguration {

    public static final String SIGNATURE_ALGORITHM = "http://www.w3.org/2000/09/xmldsig#rsa-sha1";

    private SamlSha1RsaSignatureConfiguration() {
    }

    public static SignatureSigningConfiguration createSignatureSigningConfiguration() {
        SignatureSigningConfiguration configuration = new SignatureSigningConfiguration();
        configuration.setSignatureAlgorithms(Collections.singletonList(SIGNATURE_ALGORITHM));
        configuration.setSignatureReferenceDigestMethods(
                Collections.singletonList("http://www.w3.org/2000/09/xmldsig#sha1"));
        return configuration;
    }

    public static void main(String[] args) throws Exception {
        InitializationService.initialize();
        SignatureSigningConfiguration signingConfiguration = createSignatureSigningConfiguration();
        System.out.println(signingConfiguration.getSignatureAlgorithms().get(0));
    }
}