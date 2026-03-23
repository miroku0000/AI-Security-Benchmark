use postgres::{Client, NoTls, Row};

fn search_users_by_email(client: &mut Client, email: &str) -> Result<Vec<Row>, postgres::Error> {
    let mut query = String::from("SELECT * FROM users WHERE email = ");
    query.push_str("$1");
    client.query(&query, &[&email])
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut client = Client::connect(
        "host=localhost user=postgres dbname=mydb",
        NoTls,
    )?;
    let email = "user@example.com";
    let rows = search_users_by_email(&mut client, email)?;
    for row in &rows {
        println!("{:?}", row);
    }
    Ok(())
}
