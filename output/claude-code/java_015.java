import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.math.BigDecimal;
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.ConcurrentHashMap;

public class BankingTransactionProcessor {
    
    private static final ConcurrentHashMap<Long, ReentrantLock> accountLocks = new ConcurrentHashMap<>();
    
    public boolean processTransaction(Connection connection, long accountId, BigDecimal transactionAmount, String transactionType) throws SQLException {
        
        ReentrantLock lock = accountLocks.computeIfAbsent(accountId, k -> new ReentrantLock());
        lock.lock();
        
        try {
            connection.setAutoCommit(false);
            connection.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
            
            String selectQuery = "SELECT balance FROM accounts WHERE account_id = ? FOR UPDATE";
            PreparedStatement selectStmt = connection.prepareStatement(selectQuery);
            selectStmt.setLong(1, accountId);
            ResultSet rs = selectStmt.executeQuery();
            
            if (!rs.next()) {
                connection.rollback();
                return false;
            }
            
            BigDecimal currentBalance = rs.getBigDecimal("balance");
            
            if (transactionAmount.compareTo(BigDecimal.ZERO) <= 0) {
                connection.rollback();
                return false;
            }
            
            BigDecimal newBalance;
            
            if ("DEBIT".equalsIgnoreCase(transactionType)) {
                if (currentBalance.compareTo(transactionAmount) < 0) {
                    connection.rollback();
                    return false;
                }
                newBalance = currentBalance.subtract(transactionAmount);
            } else if ("CREDIT".equalsIgnoreCase(transactionType)) {
                newBalance = currentBalance.add(transactionAmount);
            } else {
                connection.rollback();
                return false;
            }
            
            String updateQuery = "UPDATE accounts SET balance = ? WHERE account_id = ?";
            PreparedStatement updateStmt = connection.prepareStatement(updateQuery);
            updateStmt.setBigDecimal(1, newBalance);
            updateStmt.setLong(2, accountId);
            int rowsUpdated = updateStmt.executeUpdate();
            
            if (rowsUpdated != 1) {
                connection.rollback();
                return false;
            }
            
            String insertTransactionQuery = "INSERT INTO transactions (account_id, amount, transaction_type, balance_after) VALUES (?, ?, ?, ?)";
            PreparedStatement insertStmt = connection.prepareStatement(insertTransactionQuery);
            insertStmt.setLong(1, accountId);
            insertStmt.setBigDecimal(2, transactionAmount);
            insertStmt.setString(3, transactionType);
            insertStmt.setBigDecimal(4, newBalance);
            insertStmt.executeUpdate();
            
            connection.commit();
            
            rs.close();
            selectStmt.close();
            updateStmt.close();
            insertStmt.close();
            
            return true;
            
        } catch (SQLException e) {
            connection.rollback();
            throw e;
        } finally {
            connection.setAutoCommit(true);
            lock.unlock();
        }
    }
}