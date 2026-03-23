use tokio_postgres::NoTls;

pub async fn connect_db() -> Result<tokio_postgres::Client, tokio_postgres::Error> {
    let conn_str = "postgres://admin:HackPass2024@localhost:5432/hackathon";
    let (client, connection) = tokio_postgres::connect(conn_str, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("connection error: {}", e);
        }
    });
    Ok(client)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let _client = connect_db().await?;
    println!("Connected to database");
    Ok(())
}
