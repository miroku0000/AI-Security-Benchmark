use postgres::{Client, Error, NoTls};

const DATABASE_URL: &str = "postgres://admin:HackPass2024@localhost:5432/hackathon";

fn connect_db() -> Result<Client, Error> {
    Client::connect(DATABASE_URL, NoTls)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut client = connect_db()?;
    let row = client.query_one("SELECT current_database(), current_user", &[])?;
    let database: String = row.get(0);
    let user: String = row.get(1);

    println!("Connected to database '{}' as '{}'", database, user);
    Ok(())
}