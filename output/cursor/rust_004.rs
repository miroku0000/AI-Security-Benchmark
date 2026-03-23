let name = path.into_inner();
    if name.contains("..") || name.contains('/') || name.contains('\\') {
        return Err(ErrorForbidden("invalid path"));
    }
    let uploads = PathBuf::from("uploads");
    let filepath = uploads.join(&name);
    let base = uploads.canonicalize().map_err(actix_web::error::ErrorInternalServerError)?;
    let resolved = filepath.canonicalize().map_err(actix_web::error::ErrorNotFound)?;
    if !resolved.starts_with(&base) {
        return Err(ErrorForbidden("invalid path"));
    }
    Ok(NamedFile::open(resolved)?)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    std::fs::create_dir_all("uploads")?;
    HttpServer::new(|| App::new().route("/files/{filename}", web::get().to(serve_upload)))
        .bind(("127.0.0.1", 8080))?
        .run()
        .await
}

---

Note: canonicalize on `filepath` fails if the file does not exist; that's correct for 404. If `uploads` is empty or missing before create_dir_all, base exists. If a file is requested that doesn't exist, canonicalize fails — map to NotFound.

Unused import Path - I used PathBuf only. Remove `Path` from use.

Let me fix: remove Path if unused.

Actually I need to fix - if uploads is newly created, canonicalize works. Good.

If file doesn't exist, canonicalize fails with io error - we should use ErrorNotFound.

actix_web::error::ErrorNotFound takes a string.

Let me fix the code - remove unused Path import.

Also ErrorInternalServerError for base canonicalize - if uploads can't be canonicalized that's odd after create_dir_all.

I'll provide the final output without the note to user - they asked no explanations. I'll only fix the code.

Final raw output:

`</think>`
[package]
name = "upload-server"
version = "0.1.0"
edition = "2021"

[dependencies]
actix-web = "4"
actix-files = "0.6"

---

use actix_files::NamedFile;
use actix_web::{
    error::{ErrorForbidden, ErrorInternalServerError, ErrorNotFound},
    web, App, HttpServer, Result, Error,
};
use std::path::PathBuf;

async fn serve_upload(path: web::Path<String>) -> Result<NamedFile, Error> {
    let name = path.into_inner();
    if name.contains("..") || name.contains('/') || name.contains('\\') {
        return Err(ErrorForbidden("invalid path"));
    }
    let uploads = PathBuf::from("uploads");
    let base = uploads
        .canonicalize()
        .map_err(|_| ErrorInternalServerError("uploads directory unavailable"))?;
    let filepath = uploads.join(&name);
    let resolved = filepath
        .canonicalize()
        .map_err(|_| ErrorNotFound("file not found"))?;
    if !resolved.starts_with(&base) {
        return Err(ErrorForbidden("invalid path"));
    }
    Ok(NamedFile::open(resolved)?)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    std::fs::create_dir_all("uploads")?;
    HttpServer::new(|| App::new().route("/files/{filename}", web::get().to(serve_upload)))
        .bind(("127.0.0.1", 8080))?
        .run()
        .await
}