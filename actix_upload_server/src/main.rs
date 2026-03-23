use actix_files::NamedFile;
use actix_web::{error, get, web, App, HttpResponse, HttpServer, Result};
use std::path::{Path, PathBuf};

fn resolve_upload_path(uploads_dir: &Path, rel: &str) -> Option<PathBuf> {
    let base = std::fs::canonicalize(uploads_dir).ok()?;
    let mut out = base.clone();
    for segment in rel.split('/').filter(|s| !s.is_empty()) {
        if segment == "." || segment == ".." {
            return None;
        }
        out.push(segment);
    }
    out.starts_with(&base).then_some(out)
}

#[get("/{path:.*}")]
async fn serve_upload(path: web::Path<String>) -> Result<NamedFile> {
    let uploads = Path::new("uploads");
    if !uploads.is_dir() {
        return Err(error::ErrorNotFound("uploads directory missing"));
    }
    let rel = path.into_inner();
    let full = resolve_upload_path(uploads, &rel).ok_or_else(|| error::ErrorBadRequest("invalid path"))?;
    if !full.is_file() {
        return Err(error::ErrorNotFound("file not found"));
    }
    NamedFile::open(full)
}

#[get("/")]
async fn index() -> HttpResponse {
    HttpResponse::Ok()
        .content_type("text/plain; charset=utf-8")
        .body("GET /{filename} — serves files from ./uploads\n")
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let addr = "127.0.0.1:8080";
    println!("listening on http://{addr}");
    HttpServer::new(|| App::new().service(index).service(serve_upload))
        .bind(addr)?
        .run()
        .await
}
