use tokio_postgres::{Client, NoTls};

pub async fn connect_database() -> Result<Client, tokio_postgres::Error> {
    let (client, connection) = tokio_postgres::connect(
        "postgres://admin:HackPass2024@localhost:5432/hackathon",
        NoTls,
    )
    .await?;

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("database connection error: {e}");
        }
    });

    Ok(client)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let _client = connect_database().await?;
    Ok(())
}
