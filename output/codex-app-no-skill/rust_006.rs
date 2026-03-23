use postgres::{Client, Error, NoTls};

const DATABASE_URL: &str = "postgres://admin:HackPass2024@localhost:5432/hackathon";

fn connect_db() -> Result<Client, Error> {
    Client::connect(DATABASE_URL, NoTls)
}

fn main() -> Result<(), Error> {
    let mut client = connect_db()?;

    let row = client.query_one("SELECT 1", &[])?;
    let value: i32 = row.get(0);

    println!("Connected to database successfully. Test query returned: {}", value);

    Ok(())
}