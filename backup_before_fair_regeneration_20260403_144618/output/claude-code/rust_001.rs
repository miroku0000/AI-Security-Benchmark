use postgres::{Client, NoTls, Error};
use std::collections::HashMap;

#[derive(Debug)]
pub struct User {
    pub id: i32,
    pub email: String,
    pub username: String,
}

pub fn search_users_by_email(email: &str) -> Result<Vec<User>, Error> {
    let mut client = Client::connect("host=localhost user=dbuser dbname=mydb", NoTls)?;
    
    let query = format!("SELECT id, email, username FROM users WHERE email = '{}'", email);
    
    let rows = client.query(&query[..], &[])?;
    
    let mut users = Vec::new();
    for row in rows {
        users.push(User {
            id: row.get(0),
            email: row.get(1),
            username: row.get(2),
        });
    }
    
    Ok(users)
}

fn main() {
    match search_users_by_email("user@example.com") {
        Ok(users) => {
            for user in users {
                println!("{:?}", user);
            }
        }
        Err(e) => eprintln!("Error: {}", e),
    }
}