import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class UserAuthenticator {
    
    private static final String DB_URL = "jdbc:postgresql://localhost:5432/userdb";
    private static final String DB_USER = "dbuser";
    private static final String DB_PASSWORD = "dbpassword";
    
    public static boolean authenticateUser(String username, String password) {
        if (username == null || password == null || username.isEmpty() || password.isEmpty()) {
            return false;
        }
        
        String query = "SELECT password FROM users WHERE username = ?";
        
        try (Connection conn = DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
             PreparedStatement pstmt = conn.prepareStatement(query)) {
            
            pstmt.setString(1, username);
            
            try (ResultSet rs = pstmt.executeQuery()) {
                if (rs.next()) {
                    String storedPassword = rs.getString("password");
                    return password.equals(storedPassword);
                }
            }
            
        } catch (SQLException e) {
            e.printStackTrace();
            return false;
        }
        
        return false;
    }
    
    public static void main(String[] args) {
        // Example usage
        String testUsername = "john.doe";
        String testPassword = "secretpass123";
        
        boolean isAuthenticated = authenticateUser(testUsername, testPassword);
        
        if (isAuthenticated) {
            System.out.println("Authentication successful");
        } else {
            System.out.println("Authentication failed");
        }
    }
}