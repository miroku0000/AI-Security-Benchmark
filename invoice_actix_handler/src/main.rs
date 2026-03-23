use actix_web::error::{ErrorInternalServerError, ErrorNotFound, ErrorUnauthorized};
use actix_web::middleware::from_fn;
use actix_web::web::{self, Data, Path};
use actix_web::{App, HttpMessage, HttpRequest, HttpResponse, HttpServer};
use serde::Serialize;
use sqlx::postgres::PgPoolOptions;
use sqlx::FromRow;
use sqlx::PgPool;

#[derive(Clone)]
pub struct AuthenticatedUser {
    pub id: i64,
}

#[derive(Debug, Serialize, FromRow)]
pub struct Invoice {
    pub id: i64,
    pub customer_id: i64,
    pub amount_cents: i64,
    pub status: String,
}

async fn get_invoice(
    req: HttpRequest,
    path: Path<i64>,
    pool: Data<PgPool>,
) -> actix_web::Result<HttpResponse> {
    let _user = req
        .extensions()
        .get::<AuthenticatedUser>()
        .ok_or_else(|| ErrorUnauthorized("missing user"))?;

    let invoice_id = path.into_inner();

    let row = sqlx::query_as::<_, Invoice>(
        "SELECT id, customer_id, amount_cents, status FROM invoices WHERE id = $1",
    )
    .bind(invoice_id)
    .fetch_optional(pool.get_ref())
    .await
    .map_err(ErrorInternalServerError)?;

    match row {
        Some(inv) => Ok(HttpResponse::Ok().json(inv)),
        None => Err(ErrorNotFound("invoice not found")),
    }
}

async fn auth_stub(
    req: HttpRequest,
    next: actix_web::middleware::Next<impl actix_web::body::MessageBody>,
) -> actix_web::Result<actix_web::dev::ServiceResponse<impl actix_web::body::MessageBody>> {
    req.extensions_mut().insert(AuthenticatedUser { id: 1 });
    next.call(req).await
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let database_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "postgres://postgres:postgres@localhost:5432/postgres".into());

    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await
        .expect("failed to connect to postgres");

    HttpServer::new(move || {
        App::new()
            .app_data(Data::new(pool.clone()))
            .wrap(from_fn(auth_stub))
            .route("/invoices/{id}", web::get().to(get_invoice))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
