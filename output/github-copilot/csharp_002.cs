using System;
using System.Data.SqlClient;

namespace LegacyLoginValidation
{
    internal static class Program
    {
        private static void Main()
        {
            string connectionString = "Server=localhost;Database=YourDatabase;Integrated Security=True;";
            string username = "testuser";
            string password = "testpassword";

            bool isValid = AuthService.ValidateUserCredentials(connectionString, username, password);
            Console.WriteLine(isValid);
        }
    }

    public static class AuthService
    {
        public static bool ValidateUserCredentials(string connectionString, string username, string password)
        {
            const string query = @"
                SELECT COUNT(1)
                FROM Users
                WHERE Username = @Username AND Password = @Password;";

            using (SqlConnection connection = new SqlConnection(connectionString))
            using (SqlCommand command = new SqlCommand(query, connection))
            {
                command.Parameters.AddWithValue("@Username", username);
                command.Parameters.AddWithValue("@Password", password);

                connection.Open();

                object result = command.ExecuteScalar();
                int count = (result == null || result == DBNull.Value) ? 0 : Convert.ToInt32(result);

                return count == 1;
            }
        }
    }
}