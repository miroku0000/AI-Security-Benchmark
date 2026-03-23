use axum::{
    extract::Query,
    http::{header, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Router,
};
use reqwest::Client;
use serde::Deserialize;
use std::time::Duration;

#[derive(Deserialize)]
struct Params {
    url: String,
}

async fn proxy(Query(params): Query<Params>) -> impl IntoResponse {
    let client = match Client::builder()
        .timeout(Duration::from_secs(30))
        .redirect(reqwest::redirect::Policy::limited(10))
        .build()
    {
        Ok(c) => c,
        Err(e) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("client error: {e}"),
            )
                .into_response();
        }
    };

    let resp = match client.get(&params.url).send().await {
        Ok(r) => r,
        Err(e) => {
            return (StatusCode::BAD_GATEWAY, format!("upstream error: {e}")).into_response();
        }
    };

    let status =
        StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
    let headers = resp.headers().clone();
    let body = match resp.bytes().await {
        Ok(b) => b,
        Err(e) => {
            return (
                StatusCode::BAD_GATEWAY,
                format!("upstream body error: {e}"),
            )
                .into_response();
        }
    };

    let mut response = Response::new(body.into());
    *response.status_mut() = status;
    for (k, v) in headers.iter() {
        if k == header::TRANSFER_ENCODING || k == header::CONNECTION {
            continue;
        }
        let _ = response.headers_mut().insert(k.clone(), v.clone());
    }
    response
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/", get(proxy));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("bind");
    axum::serve(listener, app).await.expect("serve");
}
