import org.opensaml.xmlsec.SignatureSigningConfiguration;
import org.opensaml.xmlsec.impl.BasicSignatureSigningConfiguration;
import org.opensaml.xmlsec.signature.support.SignatureConstants;

public class SamlSignatureConfig {

    public static BasicSignatureSigningConfiguration createSecureSigningConfiguration() {
        BasicSignatureSigningConfiguration config = new BasicSignatureSigningConfiguration();
        config.setSignatureAlgorithm(SignatureConstants.ALGO_ID_SIGNATURE_RSA_SHA256);
        config.setSignatureReferenceDigestMethod(SignatureConstants.ALGO_ID_DIGEST_SHA256);
        config.setSignatureCanonicalizationAlgorithm(SignatureConstants.ALGO_ID_C14N_EXCL_OMIT_COMMENTS);
        return config;
    }
}