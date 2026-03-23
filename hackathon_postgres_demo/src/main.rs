use tokio_postgres::{Client, NoTls};

const HACKATHON_DB_URL: &str = "postgres://admin:HackPass2024@localhost:5432/hackathon";

pub async fn connect_hackathon_db() -> Result<Client, tokio_postgres::Error> {
    let (client, connection) = tokio_postgres::connect(HACKATHON_DB_URL, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("database connection error: {e}");
        }
    });
    Ok(client)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let _client = connect_hackathon_db().await?;
    Ok(())
}
