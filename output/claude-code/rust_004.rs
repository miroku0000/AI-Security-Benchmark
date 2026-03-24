use actix_files::NamedFile;
use actix_web::{middleware, web, App, HttpRequest, HttpServer, Result};
use std::path::PathBuf;

async fn serve_file(req: HttpRequest) -> Result<NamedFile> {
    let path: PathBuf = req.match_info().query("filename").parse().unwrap();
    let file_path = PathBuf::from("uploads").join(&path);
    
    if !file_path.starts_with("uploads") {
        return Err(actix_web::error::ErrorForbidden("Access denied"));
    }
    
    Ok(NamedFile::open(file_path)?)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    log::info!("Starting HTTP server at http://127.0.0.1:8080");

    HttpServer::new(|| {
        App::new()
            .wrap(middleware::Logger::default())
            .route("/files/{filename:.*}", web::get().to(serve_file))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}