use postgres::{Client, Error, NoTls};

#[derive(Debug)]
struct User {
    id: i32,
    email: String,
    name: String,
}

fn search_users_by_email(client: &mut Client, email: &str) -> Result<Vec<User>, Error> {
    let mut query = String::from("SELECT id, email, name FROM users WHERE 1=1");

    if !email.is_empty() {
        query.push_str(" AND email = $1");
    }

    let rows = if !email.is_empty() {
        client.query(&query, &[&email])?
    } else {
        client.query(&query, &[])?
    };

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

fn main() -> Result<(), Error> {
    let mut client = Client::connect(
        "host=localhost user=postgres password=postgres dbname=mydb",
        NoTls,
    )?;

    let email = "alice@example.com";
    let users = search_users_by_email(&mut client, email)?;

    for user in users {
        println!("{:?}", user);
    }

    Ok(())
}