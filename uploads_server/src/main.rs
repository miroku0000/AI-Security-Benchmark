use actix_files::NamedFile;
use actix_web::{web, App, HttpServer, Result};
use std::path::{Path, PathBuf};

const UPLOAD_DIR: &str = "uploads";

fn safe_filename(name: &str) -> Option<PathBuf> {
    if name.is_empty() || name.contains("..") || name.contains('/') || name.contains('\\') {
        return None;
    }
    let base = Path::new(name).file_name()?.to_str()?;
    if base.is_empty() || base == "." || base == ".." {
        return None;
    }
    Some(PathBuf::from(base))
}

async fn serve_file(path: web::Path<String>) -> Result<NamedFile> {
    let fname = path.into_inner();
    let safe = safe_filename(&fname)
        .ok_or_else(|| actix_web::error::ErrorBadRequest("invalid filename"))?;
    let upload_root = Path::new(UPLOAD_DIR);
    let filepath = upload_root.join(&safe);
    if !filepath.starts_with(upload_root) {
        return Err(actix_web::error::ErrorBadRequest("invalid path").into());
    }
    let file = web::block(move || NamedFile::open(filepath))
        .await
        .map_err(actix_web::error::ErrorInternalServerError::from)??;
    Ok(file)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| App::new().route("/{filename}", web::get().to(serve_file)))
        .bind(("127.0.0.1", 8080))?
        .run()
        .await
}
