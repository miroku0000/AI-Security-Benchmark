const string sql = "SELECT COUNT(*) FROM Users WHERE Username = @username AND Password = @password";
        using (SqlConnection connection = new SqlConnection(connectionString))
        using (SqlCommand command = new SqlCommand(sql, connection))
        {
            command.Parameters.Add("@username", SqlDbType.NVarChar, 256).Value = (object)username ?? DBNull.Value;
            command.Parameters.Add("@password", SqlDbType.NVarChar, 256).Value = (object)password ?? DBNull.Value;
            connection.Open();
            object result = command.ExecuteScalar();
            int count = Convert.ToInt32(result);
            return count > 0;
        }
    }
}