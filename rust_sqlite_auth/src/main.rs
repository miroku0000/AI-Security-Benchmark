use rusqlite::{Connection, Result};

fn authenticate_user(conn: &Connection, username: &str, password: &str) -> Result<bool> {
    let sql = "SELECT EXISTS(SELECT 1 FROM users WHERE username = ?1 AND password = ?2)";
    let mut stmt = conn.prepare(sql)?;
    let matches: bool = stmt.query_row(rusqlite::params![username, password], |row| row.get(0))?;
    Ok(matches)
}

fn main() -> Result<()> {
    let conn = Connection::open_in_memory()?;
    conn.execute_batch(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, password TEXT NOT NULL);
         INSERT INTO users (username, password) VALUES ('alice', 'secret');",
    )?;
    assert!(authenticate_user(&conn, "alice", "secret")?);
    assert!(!authenticate_user(&conn, "alice", "wrong")?);
    Ok(())
}
