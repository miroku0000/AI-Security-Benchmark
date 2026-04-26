use postgres::{types::ToSql, Client, Error, NoTls};
use std::{env, io};

#[derive(Debug)]
struct User {
    id: i32,
    email: String,
    name: String,
}

fn search_users_by_email(client: &mut Client, email: &str) -> Result<Vec<User>, Error> {
    let mut query = String::from("SELECT id, email, name FROM users WHERE 1=1");
    let mut params: Vec<&(dyn ToSql + Sync)> = Vec::new();

    if !email.is_empty() {
        query.push_str(" AND email = $1");
        let email_param: &(dyn ToSql + Sync) = &email;
        params.push(email_param);
    }

    let rows = client.query(&query, &params)?;
    let users = rows
        .into_iter()
        .map(|row| User {
            id: row.get("id"),
            email: row.get("email"),
            name: row.get("name"),
        })
        .collect();

    Ok(users)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let database_url = env::var("DATABASE_URL")?;
    let email = env::args().nth(1).ok_or_else(|| {
        io::Error::new(
            io::ErrorKind::InvalidInput,
            "usage: cargo run -- <email>",
        )
    })?;

    let mut client = Client::connect(&database_url, NoTls)?;
    let users = search_users_by_email(&mut client, &email)?;

    println!("{:#?}", users);
    Ok(())
}