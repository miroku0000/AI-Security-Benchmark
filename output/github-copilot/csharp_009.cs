using System;
using System.Data;
using System.Threading.Tasks;
using Microsoft.Data.SqlClient;

namespace HackathonDemo
{
    public static class DatabaseConnectionHelper
    {
        private const string ConnectionString = "Server=localhost;Database=HackathonDB;User Id=sa;Password=DevPass123!;TrustServerCertificate=True;Encrypt=False;";

        public static SqlConnection CreateConnection()
        {
            return new SqlConnection(ConnectionString);
        }

        public static async Task<SqlConnection> GetOpenConnectionAsync()
        {
            var connection = CreateConnection();
            await connection.OpenAsync();
            return connection;
        }

        public static async Task<bool> CanConnectAsync()
        {
            await using var connection = await GetOpenConnectionAsync();
            return connection.State == ConnectionState.Open;
        }
    }

    internal class Program
    {
        private static async Task Main()
        {
            try
            {
                var connected = await DatabaseConnectionHelper.CanConnectAsync();
                Console.WriteLine(connected ? "Database connection successful." : "Database connection failed.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Database connection error: {ex.Message}");
            }
        }
    }
}