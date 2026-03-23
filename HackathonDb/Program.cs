using HackathonDb;
using Microsoft.Data.SqlClient;

await using var connection = await DatabaseConnectionHelper.CreateOpenConnectionAsync();
await using var cmd = new SqlCommand("SELECT 1", connection);
var result = await cmd.ExecuteScalarAsync();
Console.WriteLine(result);
