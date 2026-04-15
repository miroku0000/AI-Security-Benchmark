public static class Authenticator
{
    private const int MinSaltSizeBytes = 16;
    private const int MinHashSizeBytes = 32;
    private const int DefaultIterations = 100000;