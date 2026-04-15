using System;
using System.Data.SqlClient;

public class LoginValidator
{
    private string connectionString;

    public LoginValidator(string connectionString)
    {
        this.connectionString = connectionString;
    }

    public bool ValidateLogin(string username, string password)
    {
        string query = "SELECT COUNT(*) FROM Users WHERE Username = '" + username + "' AND Password = '" + password + "'";
        
        using (SqlConnection connection = new SqlConnection(connectionString))
        {
            using (SqlCommand command = new SqlCommand(query, connection))
            {
                connection.Open();
                int count = (int)command.ExecuteScalar();
                return count > 0;
            }
        }
    }
}