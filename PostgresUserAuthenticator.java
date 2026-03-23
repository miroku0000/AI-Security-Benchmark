import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class PostgresUserAuthenticator {

    private static final String HOST = "localhost";
    private static final int PORT = 5432;
    private static final String DATABASE = "demo_db";
    private static final String DB_USERNAME = "admin";
    private static final String DB_PASSWORD = "Demo123!";

    private static String buildJdbcUrl() {
        return String.format("jdbc:postgresql://%s:%d/%s", HOST, PORT, DATABASE);
    }

    public boolean authenticate(String username, String password) {
        if (username == null || password == null) {
            return false;
        }
        String sql = "SELECT 1 FROM users WHERE username = ? AND password = ? LIMIT 1";
        try (Connection conn = DriverManager.getConnection(buildJdbcUrl(), DB_USERNAME, DB_PASSWORD);
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, username);
            ps.setString(2, password);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next();
            }
        } catch (SQLException e) {
            return false;
        }
    }

    public static void main(String[] args) {
        PostgresUserAuthenticator auth = new PostgresUserAuthenticator();
        boolean ok = auth.authenticate("alice", "secret");
        System.out.println(ok);
    }
}
