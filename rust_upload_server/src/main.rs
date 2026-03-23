use actix_files::NamedFile;
use actix_web::{
    error::{ErrorForbidden, ErrorNotFound},
    web::{self, Data},
    App, HttpServer,
};
use std::path::{Component, Path, PathBuf};

fn safe_upload_path(uploads_dir: &Path, tail: &str) -> Result<PathBuf, actix_web::Error> {
    let tail = tail.trim_start_matches('/');
    if tail.is_empty() || tail.contains("..") {
        return Err(ErrorNotFound("not found"));
    }
    let mut out = uploads_dir.to_path_buf();
    for comp in Path::new(tail).components() {
        match comp {
            Component::Normal(c) => out.push(c),
            Component::CurDir => {}
            _ => return Err(ErrorForbidden("invalid path")),
        }
    }
    if !out.starts_with(uploads_dir) {
        return Err(ErrorForbidden("invalid path"));
    }
    Ok(out)
}

async fn serve_upload(
    path: web::Path<String>,
    uploads_dir: Data<PathBuf>,
) -> Result<NamedFile, actix_web::Error> {
    let file_path = safe_upload_path(uploads_dir.get_ref(), &path.into_inner())?;
    Ok(NamedFile::open(file_path)?)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let uploads_dir = std::env::var("UPLOADS_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("uploads"));
    std::fs::create_dir_all(&uploads_dir)?;
    let uploads_dir = uploads_dir
        .canonicalize()
        .expect("uploads directory");

    let bind = std::env::var("BIND").unwrap_or_else(|_| "127.0.0.1:8080".to_string());
    println!("listening on http://{bind}  (UPLOADS_DIR={})", uploads_dir.display());

    HttpServer::new(move || {
        App::new()
            .app_data(Data::new(uploads_dir.clone()))
            .route("/{filename:.*}", web::get().to(serve_upload))
    })
    .bind(&bind)?
    .run()
    .await
}
