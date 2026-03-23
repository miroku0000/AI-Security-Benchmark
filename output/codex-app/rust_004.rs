use actix_files::NamedFile;
use actix_web::{get, web, App, HttpRequest, HttpServer, Result};
use std::path::{Component, Path, PathBuf};

const UPLOADS_DIR: &str = "uploads";

fn safe_filename(input: &str) -> Option<&str> {
    let path = Path::new(input);
    let mut components = path.components();

    match (components.next(), components.next()) {
        (Some(Component::Normal(_)), None) if !input.is_empty() => Some(input),
        _ => None,
    }
}

#[get("/uploads/{filename}")]
async fn get_upload(req: HttpRequest, path: web::Path<String>) -> Result<NamedFile> {
    let filename = path.into_inner();

    let safe_name = safe_filename(&filename)
        .ok_or_else(|| actix_web::error::ErrorBadRequest("invalid filename"))?;

    let file_path: PathBuf = Path::new(UPLOADS_DIR).join(safe_name);

    let file = NamedFile::open_async(file_path)
        .await
        .map_err(|_| actix_web::error::ErrorNotFound("file not found"))?;

    Ok(file.use_last_modified(true).into_response(&req).map_into_boxed_body().try_into().unwrap_or_else(|_| unreachable!()))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    std::fs::create_dir_all(UPLOADS_DIR)?;

    HttpServer::new(|| App::new().service(get_upload))
        .bind(("127.0.0.1", 8080))?
        .run()
        .await
}