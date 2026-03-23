using HackathonDbHelper;

await using var connection = DatabaseConnectionHelper.CreateConnection();
await connection.OpenAsync();
Console.WriteLine("Connected.");
