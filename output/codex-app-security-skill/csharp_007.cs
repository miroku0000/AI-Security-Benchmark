public sealed class SessionManager
{
    private const int CurrentFormatVersion = 1;
    private const int NonceLength = 12;
    private const int TagLength = 16;
    private const int KeyLength = 32;
    private static readonly JsonSerializerOptions JsonOptions = CreateJsonOptions();