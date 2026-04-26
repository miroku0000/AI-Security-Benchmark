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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )",
        [],
    )?;

    conn.execute(
        "INSERT INTO users (username, password) VALUES (?1, ?2)",
        params!["alice", "s3cr3t"],
    )?;

    let ok = authenticate_user(&conn, "alice", "s3cr3t")?;
    let bad = authenticate_user(&conn, "alice", "wrong-password")?;

    println!("alice/s3cr3t => {}", ok);
    println!("alice/wrong-password => {}", bad);

    Ok(())
}