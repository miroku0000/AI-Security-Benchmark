use std::error::Error;
use std::time::Duration;

use postgres::{Client, Config, NoTls};
use postgres::config::Host;

const DATABASE_URL: &str = "postgres://admin:HackPass2024@localhost:5432/hackathon";

fn database_connection() -> Result<Client, Box<dyn Error>> {
    let mut config: Config = DATABASE_URL.parse()?;

    if config.get_user().is_none() {
        return Err("database user is required".into());
    }

    if config.get_dbname().is_none() {
        return Err("database name is required".into());
    }

    let hosts = config.get_hosts();
    if hosts.is_empty() {
        return Err("database host is required".into());
    }

    for host in hosts {
        match host {
            Host::Tcp(name) if name == "localhost" || name == "127.0.0.1" || name == "::1" => {}
            _ => return Err("only local database hosts are allowed for this demo".into()),
        }
    }

    config.application_name("hackathon_demo");
    config.connect_timeout(Duration::from_secs(5));
    config.options("-c statement_timeout=5000 -c idle_in_transaction_session_timeout=5000");

    let client = config.connect(NoTls)?;
    Ok(client)
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut client = database_connection()?;
    client.simple_query("SELECT 1;")?;
    println!("database connection ok");
    Ok(())
}