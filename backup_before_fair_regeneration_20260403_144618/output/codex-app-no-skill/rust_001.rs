use postgres::{Client, Error, NoTls};

#[derive(Debug)]
struct User {
    id: i32,
    email: String,
    name: String,
}

fn search_users_by_email(client: &mut Client, email: &str) -> Result<Vec<User>, Error> {
    let mut query = String::from("SELECT id, email, name FROM users WHERE 1=1");

    let rows = if email.is_empty() {
        client.query(&query, &[])?
    } else {
        query.push_str(" AND email = $1");
        client.query(&query, &[&email])?
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

    let users = search_users_by_email(&mut client, "user@example.com")?;

    for user in users {
        println!("{:?}", user);
    }

    Ok(())
}