use actix_web::error::{ErrorInternalServerError, ErrorNotFound, ErrorUnauthorized};
use actix_web::web::{self, Data};
use actix_web::{App, HttpRequest, HttpResponse, HttpServer};
use chrono::{DateTime, Utc};
use serde::Deserialize;
use serde::Serialize;
use sqlx::postgres::PgPoolOptions;
use sqlx::FromRow;
use sqlx::PgPool;
use std::env;
use uuid::Uuid;

#[derive(Clone)]
struct AppState {
    pool: PgPool,
}

#[derive(Clone)]
pub struct AuthenticatedUser {
    pub user_id: Uuid,
}

#[derive(Serialize, FromRow)]
struct Invoice {
    id: Uuid,
    invoice_number: String,
    amount_cents: i64,
    status: String,
    created_at: DateTime<Utc>,
}

#[derive(Deserialize)]
struct InvoicePath {
    invoice_id: Uuid,
}

async fn get_invoice(
    path: web::Path<InvoicePath>,
    req: HttpRequest,
    state: Data<AppState>,
) -> actix_web::Result<HttpResponse> {
    let user = req
        .extensions()
        .get::<AuthenticatedUser>()
        .cloned()
        .ok_or_else(|| ErrorUnauthorized("missing authenticated user"))?;

    let invoice_id = path.into_inner().invoice_id;

    let invoice = sqlx::query_as::<_, Invoice>(
        r#"
        SELECT id, invoice_number, amount_cents, status, created_at
        FROM invoices
        WHERE id = $1 AND user_id = $2
        "#,
    )
    .bind(invoice_id)
    .bind(user.user_id)
    .fetch_optional(&state.pool)
    .await
    .map_err(ErrorInternalServerError)?;

    match invoice {
        Some(inv) => Ok(HttpResponse::Ok().json(inv)),
        None => Err(ErrorNotFound("invoice not found")),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await
        .expect("failed to connect to database");

    let state = AppState { pool };

    HttpServer::new(move || {
        App::new()
            .app_data(Data::new(state.clone()))
            .route("/invoices/{invoice_id}", web::get().to(get_invoice))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
