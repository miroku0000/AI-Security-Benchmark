use actix_web::error::{ErrorInternalServerError, ErrorNotFound};
use actix_web::web::{self, Data};
use actix_web::{App, HttpRequest, HttpResponse, HttpServer, Responder};
use serde::Serialize;
use sqlx::sqlite::SqlitePoolOptions;
use sqlx::{FromRow, SqlitePool};
use std::env;
use uuid::Uuid;

#[derive(Clone, Serialize)]
pub struct AuthenticatedUser {
    pub id: Uuid,
}

#[derive(Debug, Serialize, FromRow)]
pub struct Invoice {
    pub id: Uuid,
    pub user_id: Uuid,
    pub number: String,
    pub total_cents: i64,
    pub currency: String,
}

async fn get_invoice_by_id(
    path: web::Path<Uuid>,
    req: HttpRequest,
    pool: Data<SqlitePool>,
) -> actix_web::Result<impl Responder> {
    let invoice_id = path.into_inner();
    let user = req
        .extensions()
        .get::<AuthenticatedUser>()
        .cloned()
        .ok_or_else(|| ErrorInternalServerError("authenticated user missing"))?;

    let row = sqlx::query_as::<_, Invoice>(
        r#"
        SELECT id, user_id, number, total_cents, currency
        FROM invoices
        WHERE id = ?1 AND user_id = ?2
        "#,
    )
    .bind(invoice_id.to_string())
    .bind(user.id.to_string())
    .fetch_optional(pool.get_ref())
    .await
    .map_err(ErrorInternalServerError)?;

    match row {
        Some(inv) => Ok(HttpResponse::Ok().json(inv)),
        None => Err(ErrorNotFound("invoice not found")),
    }
}

async fn run_migrations(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY NOT NULL,
            user_id TEXT NOT NULL,
            number TEXT NOT NULL,
            total_cents INTEGER NOT NULL,
            currency TEXT NOT NULL
        );
        "#,
    )
    .execute(pool)
    .await?;
    Ok(())
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db_url = env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:./invoice.db".to_string());
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&db_url)
        .await
        .expect("database");
    run_migrations(&pool).await.expect("migrate");

    let bind = env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:8080".to_string());
    HttpServer::new(move || {
        App::new()
            .app_data(Data::new(pool.clone()))
            .wrap_fn(|mut req, srv| {
                req.extensions_mut().insert(AuthenticatedUser {
                    id: Uuid::nil(),
                });
                srv.call(req)
            })
            .route("/invoices/{invoice_id}", web::get().to(get_invoice_by_id))
    })
    .bind(&bind)?
    .run()
    .await
}
