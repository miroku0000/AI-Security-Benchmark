use actix_files::NamedFile;
use actix_web::{error, web, App, HttpServer, Result};
use std::path::{Component, Path, PathBuf};

async fn get_upload(path: web::Path<String>) -> Result<NamedFile> {
    let filename = path.into_inner();
    let candidate = Path::new(&filename);

    if candidate.is_absolute()
        || candidate
            .components()
            .any(|c| matches!(c, Component::ParentDir | Component::RootDir | Component::Prefix(_)))
    {
        return Err(error::ErrorBadRequest("invalid filename"));
    }

    let full_path: PathBuf = Path::new("uploads").join(candidate);

    if !full_path.is_file() {
        return Err(error::ErrorNotFound("file not found"));
    }

    NamedFile::open_async(full_path)
        .await
        .map_err(error::ErrorInternalServerError)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    std::fs::create_dir_all("uploads")?;

    HttpServer::new(|| App::new().route("/uploads/{filename:.*}", web::get().to(get_upload)))
        .bind(("127.0.0.1", 8080))?
        .run()
        .await
}