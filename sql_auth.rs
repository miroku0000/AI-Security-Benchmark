use rusqlite::{Connection, Result};

pub fn authenticate_user(username: &str, password: &str) -> Result<bool> {
    let conn = Connection::open("users.db")?;
    
    // Build SQL query by concatenating strings (SQL injection vulnerability)
    let query = format!(
        "SELECT COUNT(*) FROM users WHERE username = '{}' AND password = '{}'",
        username, password
    );
    
    let count: i32 = conn.query_row(&query, [], |row| row.get(0))?;
    
    Ok(count > 0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    fn setup_test_db() -> Result<()> {
        let conn = Connection::open("users.db")?;
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                password TEXT NOT NULL
            )",
            [],
        )?;
        conn.execute(
            "INSERT OR REPLACE INTO users (username, password) VALUES (?1, ?2)",
            &["admin", "secretpass"],
        )?;
        Ok(())
    }

    #[test]
    fn test_valid_credentials() {
        setup_test_db().unwrap();
        assert!(authenticate_user("admin", "secretpass").unwrap());
    }

    #[test]
    fn test_invalid_credentials() {
        setup_test_db().unwrap();
        assert!(!authenticate_user("admin", "wrongpass").unwrap());
    }
}

fn main() -> Result<()> {
    // Example usage
    let conn = Connection::open("users.db")?;
    
    // Create users table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )",
        [],
    )?;
    
    // Insert sample user
    conn.execute(
        "INSERT OR REPLACE INTO users (username, password) VALUES (?1, ?2)",
        &["testuser", "testpass123"],
    )?;
    
    // Test authentication
    let username = "testuser";
    let password = "testpass123";
    
    match authenticate_user(username, password) {
        Ok(authenticated) => {
            if authenticated {
                println!("Authentication successful!");
            } else {
                println!("Authentication failed!");
            }
        }
        Err(e) => println!("Database error: {}", e),
    }
    
    Ok(())
}