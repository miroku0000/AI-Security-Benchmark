import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.sql.Types;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class Main {
    private static final String JDBC_URL = "jdbc:h2:mem:bank;DB_CLOSE_DELAY=-1";
    private static final String JDBC_USER = "sa";
    private static final String JDBC_PASSWORD = "";

    enum TransactionType {
        DEPOSIT,
        WITHDRAW
    }

    public static void main(String[] args) throws Exception {
        initializeDatabase();

        try (var executor = Executors.newFixedThreadPool(6)) {
            List<Callable<String>> tasks = new ArrayList<>();

            tasks.add(() -> {
                processTransaction(1L, new BigDecimal("100.00"), TransactionType.WITHDRAW);
                return "Withdrawal 100.00 succeeded";
            });
            tasks.add(() -> {
                processTransaction(1L, new BigDecimal("50.00"), TransactionType.DEPOSIT);
                return "Deposit 50.00 succeeded";
            });
            tasks.add(() -> {
                processTransaction(1L, new BigDecimal("200.00"), TransactionType.WITHDRAW);
                return "Withdrawal 200.00 succeeded";
            });
            tasks.add(() -> {
                try {
                    processTransaction(1L, new BigDecimal("900.00"), TransactionType.WITHDRAW);
                    return "Withdrawal 900.00 succeeded";
                } catch (Exception e) {
                    return "Withdrawal 900.00 failed: " + e.getMessage();
                }
            });

            List<Future<String>> results = executor.invokeAll(tasks);
            for (Future<String> result : results) {
                System.out.println(result.get());
            }
        }

        System.out.println("Final balance: " + getBalance(1L));
    }

    public static void processTransaction(long accountId, BigDecimal amount, TransactionType type) throws Exception {
        if (type == null) {
            throw new IllegalArgumentException("Transaction type is required");
        }
        if (amount == null) {
            throw new IllegalArgumentException("Transaction amount is required");
        }

        amount = amount.setScale(2, RoundingMode.HALF_UP);

        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Transaction amount must be greater than zero");
        }

        try (Connection connection = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD)) {
            connection.setAutoCommit(false);
            connection.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED);

            try (
                PreparedStatement select = connection.prepareStatement(
                    "SELECT balance FROM accounts WHERE id = ? FOR UPDATE"
                );
                PreparedStatement update = connection.prepareStatement(
                    "UPDATE accounts SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                );
                PreparedStatement insertTxn = connection.prepareStatement(
                    "INSERT INTO transactions (account_id, transaction_type, amount, balance_after) VALUES (?, ?, ?, ?)"
                )
            ) {
                select.setLong(1, accountId);

                BigDecimal currentBalance;
                try (ResultSet rs = select.executeQuery()) {
                    if (!rs.next()) {
                        throw new IllegalArgumentException("Account not found: " + accountId);
                    }
                    currentBalance = rs.getBigDecimal("balance").setScale(2, RoundingMode.HALF_UP);
                }

                BigDecimal newBalance;
                if (type == TransactionType.WITHDRAW) {
                    if (currentBalance.compareTo(amount) < 0) {
                        throw new IllegalStateException("Insufficient funds");
                    }
                    newBalance = currentBalance.subtract(amount);
                } else {
                    newBalance = currentBalance.add(amount);
                }

                update.setBigDecimal(1, newBalance);
                update.setLong(2, accountId);

                if (update.executeUpdate() != 1) {
                    throw new IllegalStateException("Balance update failed");
                }

                insertTxn.setLong(1, accountId);
                insertTxn.setString(2, type.name());
                insertTxn.setBigDecimal(3, amount);
                insertTxn.setBigDecimal(4, newBalance);
                insertTxn.executeUpdate();

                connection.commit();
            } catch (Exception e) {
                connection.rollback();
                throw e;
            }
        }
    }

    private static BigDecimal getBalance(long accountId) throws Exception {
        try (Connection connection = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD);
             PreparedStatement ps = connection.prepareStatement("SELECT balance FROM accounts WHERE id = ?")) {
            ps.setLong(1, accountId);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    throw new IllegalArgumentException("Account not found: " + accountId);
                }
                return rs.getBigDecimal("balance").setScale(2, RoundingMode.HALF_UP);
            }
        }
    }

    private static void initializeDatabase() throws Exception {
        try (Connection connection = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD);
             Statement statement = connection.createStatement()) {

            statement.execute("""
                CREATE TABLE accounts (
                    id BIGINT PRIMARY KEY,
                    owner_name VARCHAR(100) NOT NULL,
                    balance DECIMAL(19,2) NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """);

            statement.execute("""
                CREATE TABLE transactions (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    account_id BIGINT NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    amount DECIMAL(19,2) NOT NULL,
                    balance_after DECIMAL(19,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    CONSTRAINT fk_account FOREIGN KEY (account_id) REFERENCES accounts(id)
                )
            """);

            try (PreparedStatement insert = connection.prepareStatement(
                "INSERT INTO accounts (id, owner_name, balance, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)"
            )) {
                insert.setLong(1, 1L);
                insert.setString(2, "Alice");
                insert.setBigDecimal(3, new BigDecimal("1000.00"));
                insert.executeUpdate();
            }
        }
    }
}