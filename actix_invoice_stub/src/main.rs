use actix_web::{web, App, HttpRequest, HttpResponse, HttpServer, Result};
use serde::Serialize;
use sqlx::{sqlite::SqlitePool, FromRow};

#[derive(Clone)]
pub struct AuthenticatedUser {
    pub id: i64,
}

#[derive(Serialize, FromRow)]
struct InvoiceDetail {
    id: i64,
    invoice_number: String,
    amount_cents: i64,
    status: String,
}

async fn get_invoice(
    req: HttpRequest,
    path: web::Path<i64>,
    pool: web::Data<SqlitePool>,
) -> Result<HttpResponse> {
    let invoice_id = path.into_inner();

    let _user = req
        .extensions()
        .get::<AuthenticatedUser>()
        .ok_or_else(|| actix_web::error::ErrorUnauthorized("missing user"))?;

    let row: Option<InvoiceDetail> = sqlx::query_as(
        "SELECT id, invoice_number, amount_cents, status FROM invoices WHERE id = ?1",
    )
    .bind(invoice_id)
    .fetch_optional(&**pool)
    .await
    .map_err(actix_web::error::ErrorInternalServerError)?;

    match row {
        Some(inv) => Ok(HttpResponse::Ok().json(inv)),
        None => Ok(HttpResponse::NotFound().finish()),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let pool = SqlitePool::connect("sqlite::memory:").await.expect("db");
    sqlx::query(
        r#"CREATE TABLE invoices (id INTEGER PRIMARY KEY, invoice_number TEXT NOT NULL, amount_cents INTEGER NOT NULL, status TEXT NOT NULL);"#,
    )
    .execute(&pool)
    .await
    .unwrap();
    sqlx::query(
        r#"INSERT INTO invoices (id, invoice_number, amount_cents, status) VALUES (1, 'INV-001', 10000, 'paid');"#,
    )
    .execute(&pool)
    .await
    .unwrap();

    let pool = web::Data::new(pool);

    HttpServer::new(move || {
        App::new()
            .app_data(pool.clone())
            .wrap_fn(|mut req, srv| {
                req.extensions_mut().insert(AuthenticatedUser { id: 1 });
                srv.call(req)
            })
            .route("/invoices/{invoice_id}", web::get().to(get_invoice))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
