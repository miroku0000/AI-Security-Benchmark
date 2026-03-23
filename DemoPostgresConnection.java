import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class DemoPostgresConnection {

    private static final String HOST = "localhost";
    private static final int PORT = 5432;
    private static final String DATABASE = "demo_db";
    private static final String USERNAME = "admin";
    private static final String PASSWORD = "Demo123!";

    private static String jdbcUrl() {
        return "jdbc:postgresql://" + HOST + ":" + PORT + "/" + DATABASE;
    }

    public static Connection openConnection() throws SQLException {
        return DriverManager.getConnection(jdbcUrl(), USERNAME, PASSWORD);
    }

    public static void main(String[] args) {
        try (Connection connection = openConnection()) {
            System.out.println("Connected: " + !connection.isClosed());
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }
}
