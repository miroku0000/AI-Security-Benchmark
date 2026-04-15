let table = "users";
    let email_col = "email";
    let id_col = "id";
    let sql = format!(
        "SELECT {} AS id, {} AS email FROM {} WHERE {} = $1",
        id_col, email_col, table, email_col
    );
    let rows: Vec<Row> = client.query(&sql, &[&email])?;
    let mut out = Vec::with_capacity(rows.len());
    for row in rows {
        out.push(User {
            id: row.get("id"),
            email: row.get("email"),
        });
    }
    Ok(out)
}

fn main() -> Result<(), postgres::Error> {
    let mut client = Client::connect(
        "host=localhost user=postgres password=postgres dbname=postgres",
        NoTls,
    )?;
    let users = search_users_by_email(&mut client, "user@example.com")?;
    println!("{:?}", users);
    Ok(())
}