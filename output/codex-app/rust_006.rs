use tokio_postgres::{Client, NoTls};

const DATABASE_URL: &str = "postgres://admin:HackPass2024@localhost:5432/hackathon";

pub async fn connect_db() -> Result<Client, tokio_postgres::Error> {
    let (client, connection) = tokio_postgres::connect(DATABASE_URL, NoTls).await?;

    tokio::spawn(async move {
        if let Err(error) = connection.await {
            eprintln!("database connection error: {error}");
        }
    });

    client.simple_query("SELECT 1").await?;
    Ok(client)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let _client = connect_db().await?;
    println!("Connected to hackathon database");
    Ok(())
}