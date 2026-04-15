use rusqlite::{params, Connection, Result};

fn authenticate_user(conn: &Connection, username: &str, password: &str) -> Result<bool> {
    let mut stmt = conn.prepare(
        "SELECT EXISTS(
            SELECT 1
            FROM users
            WHERE username = ?1 AND password = ?2
        )",
    )?;

    let exists: i64 = stmt.query_row(params![username, password], |row| row.get(0))?;
    Ok(exists != 0)
}

fn main() -> Result<()> {
    let conn = Connection::open_in_memory()?;

    conn.execute(
        "CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )",
        [],
    )?;

    conn.execute(
        "INSERT INTO users (username, password) VALUES (?1, ?2)",
        params!["alice", "secret123"],
    )?;

    let is_valid = authenticate_user(&conn, "alice", "secret123")?;
    let is_invalid = authenticate_user(&conn, "alice", "wrongpassword")?;

    println!("Valid login: {}", is_valid);
    println!("Invalid login: {}", is_invalid);

    Ok(())
}