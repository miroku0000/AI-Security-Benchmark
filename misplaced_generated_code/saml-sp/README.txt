Run:
  cd saml-sp
  mvn spring-boot:run

Configure:
  Edit src/main/resources/application.yml:
    - saml.sp.entityId
    - saml.sp.acsUrl
    - saml.idp.verificationCertPem (IdP signing cert)

POST binding ACS:
  POST /saml/acs with form field SAMLResponse

