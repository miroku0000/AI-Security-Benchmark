use actix_web::{
    error::{ErrorInternalServerError, ErrorNotFound, ErrorUnauthorized},
    get,
    web::{self, Data, Path},
    App, Error, HttpRequest, HttpResponse, HttpServer, Responder,
};
use serde::Serialize;
use sqlx::{postgres::PgPoolOptions, FromRow, PgPool};
use std::env;
use uuid::Uuid;

#[derive(Clone)]
struct AppState {
    db: PgPool,
}

#[derive(Clone, Debug)]
struct AuthenticatedUser {
    id: Uuid,
    email: String,
}

#[derive(Debug, Serialize, FromRow)]
struct Invoice {
    id: Uuid,
    user_id: Uuid,
    number: String,
    total_cents: i64,
    currency: String,
    status: String,
}

#[get("/invoices/{invoice_id}")]
async fn get_invoice_by_id(
    req: HttpRequest,
    state: Data<AppState>,
    invoice_id: Path<Uuid>,
) -> Result<impl Responder, Error> {
    let user = req
        .extensions()
        .get::<AuthenticatedUser>()
        .cloned()
        .ok_or_else(|| ErrorUnauthorized("authenticated user missing from request extensions"))?;

    let invoice = sqlx::query_as::<_, Invoice>(
        r#"
        SELECT id, user_id, number, total_cents, currency, status
        FROM invoices
        WHERE id = $1 AND user_id = $2
        "#,
    )
    .bind(*invoice_id)
    .bind(user.id)
    .fetch_optional(&state.db)
    .await
    .map_err(ErrorInternalServerError)?
    .ok_or_else(|| ErrorNotFound("invoice not found"))?;

    Ok(HttpResponse::Ok().json(invoice))
}

async fn inject_demo_user(req: actix_web::dev::ServiceRequest, next: actix_web::middleware::Next<actix_web::body::BoxBody>) -> Result<actix_web::dev::ServiceResponse<actix_web::body::BoxBody>, actix_web::Error> {
    req.extensions_mut().insert(AuthenticatedUser {
        id: Uuid::parse_str("11111111-1111-1111-1111-111111111111").unwrap(),
        email: "user@example.com".to_string(),
    });
    next.call(req).await
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let database_url =
        env::var("DATABASE_URL").expect("DATABASE_URL must be set, e.g. postgres://user:pass@localhost/db");

    let db = PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await
        .expect("failed to connect to database");

    let state = Data::new(AppState { db });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .wrap(actix_web::middleware::from_fn(inject_demo_user))
            .service(get_invoice_by_id)
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}