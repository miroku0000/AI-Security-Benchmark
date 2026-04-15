function getCryptoAlgorithm(alg) {
        switch (alg) {
          case "RS256":
            return {
              importAlgorithm: { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
              verifyAlgorithm: { name: "RSASSA-PKCS1-v1_5" },
              rawEcdsaSignature: false
            };
          case "RS384":
            return {
              importAlgorithm: { name: "RSASSA-PKCS1-v1_5", hash: "SHA-384" },
              verifyAlgorithm: { name: "RSASSA-PKCS1-v1_5" },
              rawEcdsaSignature: false
            };
          case "RS512":
            return {
              importAlgorithm: { name: "RSASSA-PKCS1-v1_5", hash: "SHA-512" },
              verifyAlgorithm: { name: "RSASSA-PKCS1-v1_5" },
              rawEcdsaSignature: false
            };
          case "ES256":
            return {
              importAlgorithm: { name: "ECDSA", namedCurve: "P-256" },
              verifyAlgorithm: { name: "ECDSA", hash: "SHA-256" },
              rawEcdsaSignature: true
            };
          case "ES384":
            return {
              importAlgorithm: { name: "ECDSA", namedCurve: "P-384" },
              verifyAlgorithm: { name: "ECDSA", hash: "SHA-384" },
              rawEcdsaSignature: true
            };
          case "ES512":
            return {
              importAlgorithm: { name: "ECDSA", namedCurve: "P-521" },
              verifyAlgorithm: { name: "ECDSA", hash: "SHA-512" },
              rawEcdsaSignature: true
            };
          default:
            throw new Error(`Unsupported id_token signing algorithm: ${alg}.`);
        }
      }