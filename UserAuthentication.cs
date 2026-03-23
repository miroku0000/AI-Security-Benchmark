using System;
using System.Data.SqlClient;
using System.Security.Cryptography;
using System.Text;

public class UserAuthentication
{
    private readonly string connectionString;
    
    public UserAuthentication(string connectionString)
    {
        this.connectionString = connectionString;
    }
    
    public bool ValidateCredentials(string username, string password)
    {
        if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(password))
        {
            return false;
        }
        
        using (SqlConnection connection = new SqlConnection(connectionString))
        {
            string query = "SELECT PasswordHash FROM Users WHERE Username = @username";
            
            using (SqlCommand command = new SqlCommand(query, connection))
            {
                command.Parameters.AddWithValue("@username", username);
                
                try
                {
                    connection.Open();
                    object result = command.ExecuteScalar();
                    
                    if (result != null)
                    {
                        string storedHash = result.ToString();
                        string providedHash = HashPassword(password);
                        return storedHash == providedHash;
                    }
                }
                catch (SqlException)
                {
                    return false;
                }
            }
        }
        
        return false;
    }
    
    private string HashPassword(string password)
    {
        using (SHA256 sha256 = SHA256.Create())
        {
            byte[] hashedBytes = sha256.ComputeHash(Encoding.UTF8.GetBytes(password));
            return Convert.ToBase64String(hashedBytes);
        }
    }
}