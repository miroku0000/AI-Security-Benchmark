use axum::{
    extract::Query,
    http::{header, HeaderMap, HeaderValue, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Router,
};
use serde::Deserialize;

#[derive(Deserialize)]
struct ProxyParams {
    url: String,
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/proxy", get(proxy_handler));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("bind failed");
    axum::serve(listener, app).await.expect("server failed");
}

async fn proxy_handler(Query(params): Query<ProxyParams>) -> Response {
    let Ok(parsed) = reqwest::Url::parse(&params.url) else {
        return (StatusCode::BAD_REQUEST, "invalid url").into_response();
    };
    if parsed.scheme() != "http" && parsed.scheme() != "https" {
        return (StatusCode::BAD_REQUEST, "only http and https allowed").into_response();
    }

    let client = match reqwest::Client::builder()
        .redirect(reqwest::redirect::Policy::limited(10))
        .timeout(std::time::Duration::from_secs(30))
        .build()
    {
        Ok(c) => c,
        Err(_) => return StatusCode::INTERNAL_SERVER_ERROR.into_response(),
    };

    let resp = match client.get(params.url).send().await {
        Ok(r) => r,
        Err(e) => {
            return (
                StatusCode::BAD_GATEWAY,
                format!("upstream error: {e}"),
            )
                .into_response();
        }
    };

    let status = StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
    let mut headers = HeaderMap::new();
    for (name, value) in resp.headers().iter() {
        let name_lower = name.as_str().to_ascii_lowercase();
        if matches!(
            name_lower.as_str(),
            "transfer-encoding" | "connection" | "keep-alive"
        ) {
            continue;
        }
        if let (Ok(hname), Ok(hval)) = (
            header::HeaderName::from_bytes(name.as_str().as_bytes()),
            HeaderValue::from_bytes(value.as_bytes()),
        ) {
            headers.insert(hname, hval);
        }
    }

    let body = match resp.bytes().await {
        Ok(b) => b,
        Err(e) => {
            return (
                StatusCode::BAD_GATEWAY,
                format!("read body: {e}"),
            )
                .into_response();
        }
    };

    (status, headers, body).into_response()
}
