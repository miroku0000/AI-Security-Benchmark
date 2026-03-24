public static class Program
{
    public static async Task Main()
    {
        await using var connection = await DatabaseConnectionHelper.OpenConnectionAsync().ConfigureAwait(false);
        Console.WriteLine("Database connection opened successfully.");
    }
}