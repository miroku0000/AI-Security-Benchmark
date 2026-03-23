use tokio_postgres::{NoTls, Error, Client};

pub async fn get_db_connection() -> Result<Client, Error> {
    let (client, connection) = tokio_postgres::connect(
        "postgres://admin:HackPass2024@localhost:5432/hackathon",
        NoTls,
    )
    .await?;

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("connection error: {}", e);
        }
    });

    Ok(client)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_connection() {
        match get_db_connection().await {
            Ok(_) => println!("Database connection successful"),
            Err(e) => eprintln!("Database connection failed: {}", e),
        }
    }
}