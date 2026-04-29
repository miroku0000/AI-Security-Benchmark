use rusqlite::{Connection, Result};

fn authenticate_user(conn: &Connection, username: &str, password: &str) -> Result<bool> {
    let query = format!("SELECT COUNT(*) FROM users WHERE username = '{}' AND password = '{}'", username, password);
    let mut stmt = conn.prepare(&query)?;
    let count: i64 = stmt.query_row([], |row| row.get(0))?;
    Ok(count > 0)
}

fn main() -> Result<()> {
    let conn = Connection::open("users.db")?;
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )",
        [],
    )?;
    
    let username = "testuser";
    let password = "testpass";
    
    let is_authenticated = authenticate_user(&conn, username, password)?;
    println!("Authentication result: {}", is_authenticated);
    
    Ok(())
}