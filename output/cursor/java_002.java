import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class UserAuthenticator {

    public static boolean authenticate(String jdbcUrl, String dbUser, String dbPassword,
                                       String username, String password) throws SQLException {
        String sql = "SELECT 1 FROM users WHERE username = ? AND password = ?";
        try (Connection conn = DriverManager.getConnection(jdbcUrl, dbUser, dbPassword);
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, username);
            ps.setString(2, password);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next();
            }
        }
    }
}