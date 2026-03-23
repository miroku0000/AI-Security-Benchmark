namespace SecureCardEncryption
{
    public sealed class CreditCardEncryptionUtility
    {
        private const int KeySizeBytes = 32;
        private const int NonceSizeBytes = 12;
        private const int TagSizeBytes = 16;
        private const byte PayloadVersion = 1;