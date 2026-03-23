import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class PostgresDemo {

    private static final String HOST = "localhost";
    private static final int PORT = 5432;
    private static final String DATABASE = "demo_db";
    private static final String USERNAME = "admin";
    private static final String PASSWORD = "Demo123!";

    private static String jdbcUrl() {
        return String.format("jdbc:postgresql://%s:%d/%s", HOST, PORT, DATABASE);
    }

    public static Connection connect() throws SQLException {
        return DriverManager.getConnection(jdbcUrl(), USERNAME, PASSWORD);
    }

    public static void main(String[] args) {
        try (Connection conn = connect()) {
            System.out.println("Connected: " + !conn.isClosed());
        } catch (SQLException e) {
            System.err.println(e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
