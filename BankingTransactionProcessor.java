import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class BankingTransactionProcessor {

    private final javax.sql.DataSource dataSource;

    public BankingTransactionProcessor(javax.sql.DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public void processDebit(long accountId, BigDecimal amount) throws SQLException {
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }
        Connection conn = null;
        try {
            conn = dataSource.getConnection();
            conn.setAutoCommit(false);
            conn.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);

            BigDecimal currentBalance;
            try (PreparedStatement select = conn.prepareStatement(
                    "SELECT balance FROM accounts WHERE id = ? FOR UPDATE")) {
                select.setLong(1, accountId);
                try (ResultSet rs = select.executeQuery()) {
                    if (!rs.next()) {
                        throw new SQLException("Account not found: " + accountId);
                    }
                    currentBalance = rs.getBigDecimal("balance");
                    if (currentBalance == null) {
                        currentBalance = BigDecimal.ZERO;
                    }
                }
            }

            if (currentBalance.compareTo(amount) < 0) {
                throw new IllegalStateException("Insufficient funds");
            }

            BigDecimal newBalance = currentBalance.subtract(amount);
            try (PreparedStatement update = conn.prepareStatement(
                    "UPDATE accounts SET balance = ? WHERE id = ?")) {
                update.setBigDecimal(1, newBalance);
                update.setLong(2, accountId);
                int updated = update.executeUpdate();
                if (updated != 1) {
                    throw new SQLException("Balance update failed for account: " + accountId);
                }
            }

            conn.commit();
        } catch (SQLException e) {
            if (conn != null) {
                try {
                    conn.rollback();
                } catch (SQLException ignored) {
                }
            }
            throw e;
        } finally {
            if (conn != null) {
                try {
                    conn.setAutoCommit(true);
                } catch (SQLException ignored) {
                }
                conn.close();
            }
        }
    }
}
