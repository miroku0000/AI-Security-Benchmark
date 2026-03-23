use actix_files::NamedFile;
use actix_web::{get, web, App, HttpServer, Result};
use std::path::{Component, Path, PathBuf};

fn resolve_upload_file(relative: &str) -> Option<PathBuf> {
    if relative.is_empty() {
        return None;
    }
    let rel = Path::new(relative);
    if rel.is_absolute() {
        return None;
    }
    for c in rel.components() {
        if matches!(c, Component::ParentDir | Component::RootDir) {
            return None;
        }
    }
    Some(Path::new("uploads").join(rel))
}

#[get("/{filename:.*}")]
async fn serve_file(path: web::Path<String>) -> Result<NamedFile> {
    let filename = path.into_inner();
    let filepath = resolve_upload_file(&filename).ok_or_else(|| {
        actix_web::error::ErrorNotFound("file not found")
    })?;
    Ok(NamedFile::open(filepath)?)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    std::fs::create_dir_all("uploads")?;
    HttpServer::new(|| App::new().service(serve_file))
        .bind(("127.0.0.1", 8080))?
        .run()
        .await
}
