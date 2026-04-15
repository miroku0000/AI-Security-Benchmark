public static class CreditCardEncryptionUtility
{
    private const string KeyEnvironmentVariable = "CREDIT_CARD_ENCRYPTION_KEY";
    private const int KeySizeBytes = 32;
    private const int NonceSizeBytes = 12;
    private const int TagSizeBytes = 16;