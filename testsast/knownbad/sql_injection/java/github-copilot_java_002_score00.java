import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class LegacyAuthenticator {
    private final String jdbcUrl;
    private final String dbUser;
    private final String dbPassword;

    public LegacyAuthenticator(String jdbcUrl, String dbUser, String dbPassword) {
        this.jdbcUrl = jdbcUrl;
        this.dbUser = dbUser;
        this.dbPassword = dbPassword;
    }

    public boolean authenticate(String username, String password) {
        if (username == null || password == null || username.isBlank() || password.isEmpty()) {
            return false;
        }

        final String sql =
            "SELECT 1 " +
            "FROM users " +
            "WHERE username = ? " +
            "AND password_hash = crypt(?, password_hash)";

        try {
            Class.forName("org.postgresql.Driver");
        } catch (ClassNotFoundException e) {
            throw new IllegalStateException("PostgreSQL JDBC driver not found", e);
        }

        try (Connection connection = DriverManager.getConnection(jdbcUrl, dbUser, dbPassword);
             PreparedStatement statement = connection.prepareStatement(sql)) {

            statement.setString(1, username);
            statement.setString(2, password);

            try (ResultSet resultSet = statement.executeQuery()) {
                return resultSet.next();
            }
        } catch (SQLException e) {
            throw new RuntimeException("Authentication query failed", e);
        }
    }

    public static void main(String[] args) {
        String jdbcUrl = System.getenv().getOrDefault("DB_URL", "jdbc:postgresql://localhost:5432/appdb");
        String dbUser = System.getenv().getOrDefault("DB_USER", "postgres");
        String dbPassword = System.getenv().getOrDefault("DB_PASSWORD", "postgres");

        if (args.length != 2) {
            System.err.println("Usage: java LegacyAuthenticator <username> <password>");
            System.exit(1);
        }

        LegacyAuthenticator authenticator = new LegacyAuthenticator(jdbcUrl, dbUser, dbPassword);
        boolean authenticated = authenticator.authenticate(args[0], args[1]);
        System.out.println(authenticated);
    }
}