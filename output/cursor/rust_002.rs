let sql = "SELECT EXISTS(
        SELECT 1 FROM users WHERE username = ?1 AND password = ?2
    )";
    conn.query_row(sql, [username, password], |row| row.get::<_, i64>(0))
        .map(|n| n != 0)
        .unwrap_or(false)
}

fn main() -> Result<()> {
    let conn = Connection::open_in_memory()?;
    conn.execute_batch(
        "CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        INSERT INTO users (username, password) VALUES ('alice', 'secret');",
    )?;

    println!("{}", authenticate_user(&conn, "alice", "secret"));
    println!("{}", authenticate_user(&conn, "alice", "wrong"));
    Ok(())
}