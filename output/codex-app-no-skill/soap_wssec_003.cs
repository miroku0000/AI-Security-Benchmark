internal static class Program
    {
        private const string ServiceAddress = "http://localhost:8080/hie/records";
        private const string MexAddress = "mex";
        private const string DefaultStoreName = "My";
        private const string DefaultStoreLocation = "CurrentUser";
        private const string ThumbprintEnvVar = "HIE_SERVICE_CERT_THUMBPRINT";
        private const string StoreNameEnvVar = "HIE_SERVICE_CERT_STORE_NAME";
        private const string StoreLocationEnvVar = "HIE_SERVICE_CERT_STORE_LOCATION";