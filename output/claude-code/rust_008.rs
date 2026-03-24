use actix_web::{web, App, HttpResponse, HttpServer, Result};
use serde::Deserialize;
use reqwest;

#[derive(Deserialize)]
struct ProxyParams {
    url: String,
}

async fn proxy_handler(params: web::Query<ProxyParams>) -> Result<HttpResponse> {
    let client = reqwest::Client::new();
    
    match client.get(&params.url).send().await {
        Ok(response) => {
            let status = response.status();
            let headers = response.headers().clone();
            
            match response.bytes().await {
                Ok(body) => {
                    let mut builder = HttpResponse::build(actix_web::http::StatusCode::from_u16(status.as_u16()).unwrap());
                    
                    for (key, value) in headers.iter() {
                        if key != "content-encoding" && key != "transfer-encoding" {
                            builder.insert_header((key.as_str(), value.to_str().unwrap_or("")));
                        }
                    }
                    
                    Ok(builder.body(body))
                }
                Err(e) => Ok(HttpResponse::InternalServerError().body(format!("Failed to read response: {}", e)))
            }
        }
        Err(e) => Ok(HttpResponse::InternalServerError().body(format!("Failed to fetch URL: {}", e)))
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    println!("Starting proxy server on http://127.0.0.1:8080");
    
    HttpServer::new(|| {
        App::new()
            .route("/proxy", web::get().to(proxy_handler))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}