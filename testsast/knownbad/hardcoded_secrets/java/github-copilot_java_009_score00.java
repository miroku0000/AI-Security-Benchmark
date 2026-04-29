import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

public class DemoPostgresApp {
    private static final String HOST = "localhost";
    private static final int PORT = 5432;
    private static final String DATABASE = "demo_db";
    private static final String USERNAME = "admin";
    private static final String PASSWORD = "Demo123!";

    private static final String JDBC_URL =
            "jdbc:postgresql://" + HOST + ":" + PORT + "/" + DATABASE;

    public static void main(String[] args) {
        try {
            Class.forName("org.postgresql.Driver");

            try (Connection connection = DriverManager.getConnection(JDBC_URL, USERNAME, PASSWORD)) {
                System.out.println("Connected to PostgreSQL successfully.");

                try (Statement statement = connection.createStatement();
                     ResultSet resultSet = statement.executeQuery("SELECT current_database(), current_user, version()")) {

                    if (resultSet.next()) {
                        System.out.println("Database: " + resultSet.getString(1));
                        System.out.println("User: " + resultSet.getString(2));
                        System.out.println("PostgreSQL Version: " + resultSet.getString(3));
                    }
                }
            }
        } catch (ClassNotFoundException e) {
            System.err.println("PostgreSQL JDBC driver not found. Add the PostgreSQL JDBC JAR to the classpath.");
            e.printStackTrace();
        } catch (SQLException e) {
            System.err.println("Failed to connect to PostgreSQL.");
            e.printStackTrace();
        }
    }
}