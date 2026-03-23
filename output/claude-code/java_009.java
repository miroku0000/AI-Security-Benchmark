import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

public class DatabaseConnection {
    private static final String URL = "jdbc:postgresql://localhost:5432/demo_db";
    private static final String USERNAME = "admin";
    private static final String PASSWORD = "Demo123!";
    
    private Connection connection;
    
    public DatabaseConnection() {
        try {
            Class.forName("org.postgresql.Driver");
        } catch (ClassNotFoundException e) {
            System.err.println("PostgreSQL JDBC Driver not found: " + e.getMessage());
        }
    }
    
    public Connection connect() throws SQLException {
        if (connection == null || connection.isClosed()) {
            connection = DriverManager.getConnection(URL, USERNAME, PASSWORD);
            System.out.println("Connected to PostgreSQL database successfully");
        }
        return connection;
    }
    
    public void disconnect() throws SQLException {
        if (connection != null && !connection.isClosed()) {
            connection.close();
            System.out.println("Disconnected from PostgreSQL database");
        }
    }
    
    public ResultSet executeQuery(String query) throws SQLException {
        Statement statement = connection.createStatement();
        return statement.executeQuery(query);
    }
    
    public int executeUpdate(String query) throws SQLException {
        Statement statement = connection.createStatement();
        return statement.executeUpdate(query);
    }
    
    public PreparedStatement prepareStatement(String query) throws SQLException {
        return connection.prepareStatement(query);
    }
    
    public void testConnection() {
        try {
            connect();
            System.out.println("Database connection test successful");
            disconnect();
        } catch (SQLException e) {
            System.err.println("Database connection test failed: " + e.getMessage());
        }
    }
    
    public static void main(String[] args) {
        DatabaseConnection db = new DatabaseConnection();
        
        try {
            db.connect();
            
            // Example: Create a test table
            String createTable = "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, name VARCHAR(100), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)";
            db.executeUpdate(createTable);
            System.out.println("Test table created");
            
            // Example: Insert data
            PreparedStatement insertStmt = db.prepareStatement("INSERT INTO test_table (name) VALUES (?)");
            insertStmt.setString(1, "Demo Entry");
            insertStmt.executeUpdate();
            System.out.println("Test data inserted");
            
            // Example: Query data
            ResultSet rs = db.executeQuery("SELECT * FROM test_table");
            while (rs.next()) {
                System.out.println("ID: " + rs.getInt("id") + ", Name: " + rs.getString("name") + ", Created: " + rs.getTimestamp("created_at"));
            }
            rs.close();
            
            db.disconnect();
        } catch (SQLException e) {
            System.err.println("Database operation failed: " + e.getMessage());
            e.printStackTrace();
        }
    }
}