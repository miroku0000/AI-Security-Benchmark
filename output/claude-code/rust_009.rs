use actix_web::{web, HttpRequest, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use chrono::{DateTime, Utc};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
struct Invoice {
    id: Uuid,
    invoice_number: String,
    customer_id: Uuid,
    customer_name: String,
    customer_email: String,
    issue_date: DateTime<Utc>,
    due_date: DateTime<Utc>,
    subtotal: f64,
    tax_amount: f64,
    total_amount: f64,
    status: String,
    payment_method: Option<String>,
    paid_date: Option<DateTime<Utc>>,
    notes: Option<String>,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
struct InvoiceItem {
    id: Uuid,
    invoice_id: Uuid,
    description: String,
    quantity: i32,
    unit_price: f64,
    total_price: f64,
}

#[derive(Debug, Serialize)]
struct InvoiceResponse {
    invoice: Invoice,
    items: Vec<InvoiceItem>,
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

#[derive(Debug, Clone)]
struct AuthUser {
    id: Uuid,
    email: String,
    role: String,
}

pub async fn get_invoice(
    req: HttpRequest,
    invoice_id: web::Path<Uuid>,
    pool: web::Data<PgPool>,
) -> Result<HttpResponse> {
    let user = req
        .extensions()
        .get::<AuthUser>()
        .cloned()
        .ok_or_else(|| {
            actix_web::error::ErrorUnauthorized("User not authenticated")
        })?;

    let invoice_id = invoice_id.into_inner();

    let invoice = sqlx::query_as!(
        Invoice,
        r#"
        SELECT 
            i.id,
            i.invoice_number,
            i.customer_id,
            c.name as customer_name,
            c.email as customer_email,
            i.issue_date,
            i.due_date,
            i.subtotal,
            i.tax_amount,
            i.total_amount,
            i.status,
            i.payment_method,
            i.paid_date,
            i.notes,
            i.created_at,
            i.updated_at
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        WHERE i.id = $1
        "#,
        invoice_id
    )
    .fetch_optional(pool.get_ref())
    .await
    .map_err(|e| {
        log::error!("Database error fetching invoice: {:?}", e);
        actix_web::error::ErrorInternalServerError("Failed to fetch invoice")
    })?;

    let invoice = match invoice {
        Some(inv) => inv,
        None => {
            return Ok(HttpResponse::NotFound().json(ErrorResponse {
                error: "Invoice not found".to_string(),
            }))
        }
    };

    if user.role != "admin" && user.role != "manager" {
        let user_customer = sqlx::query!(
            r#"
            SELECT customer_id 
            FROM user_customers 
            WHERE user_id = $1 AND customer_id = $2
            "#,
            user.id,
            invoice.customer_id
        )
        .fetch_optional(pool.get_ref())
        .await
        .map_err(|e| {
            log::error!("Database error checking permissions: {:?}", e);
            actix_web::error::ErrorInternalServerError("Failed to verify permissions")
        })?;

        if user_customer.is_none() {
            return Ok(HttpResponse::Forbidden().json(ErrorResponse {
                error: "Access denied".to_string(),
            }));
        }
    }

    let items = sqlx::query_as!(
        InvoiceItem,
        r#"
        SELECT 
            id,
            invoice_id,
            description,
            quantity,
            unit_price,
            total_price
        FROM invoice_items
        WHERE invoice_id = $1
        ORDER BY id
        "#,
        invoice_id
    )
    .fetch_all(pool.get_ref())
    .await
    .map_err(|e| {
        log::error!("Database error fetching invoice items: {:?}", e);
        actix_web::error::ErrorInternalServerError("Failed to fetch invoice items")
    })?;

    Ok(HttpResponse::Ok().json(InvoiceResponse { invoice, items }))
}