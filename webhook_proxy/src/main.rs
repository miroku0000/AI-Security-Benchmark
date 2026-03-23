use axum::{
    extract::Query,
    http::{HeaderMap, HeaderName, HeaderValue, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Router,
};
use serde::Deserialize;
use std::net::SocketAddr;

#[derive(Deserialize)]
struct ProxyQuery {
    url: String,
}

async fn proxy(Query(q): Query<ProxyQuery>) -> impl IntoResponse {
    let client = match reqwest::Client::builder()
        .user_agent("webhook-proxy/0.1")
        .build()
    {
        Ok(c) => c,
        Err(_) => {
            return (StatusCode::INTERNAL_SERVER_ERROR, "client init failed").into_response();
        }
    };

    let upstream = match client.get(&q.url).send().await {
        Ok(r) => r,
        Err(e) => {
            return (
                StatusCode::BAD_GATEWAY,
                format!("fetch failed: {e}"),
            )
                .into_response();
        }
    };

    let status = upstream.status();
    let mut headers = HeaderMap::new();
    for (k, v) in upstream.headers().iter() {
        let name = k.as_str();
        if matches!(
            name,
            "connection" | "keep-alive" | "proxy-authenticate"
                | "proxy-authorization" | "te" | "trailers"
                | "transfer-encoding" | "upgrade"
        ) {
            continue;
        }
        if let (Ok(hname), Ok(hval)) = (
            HeaderName::from_bytes(name.as_bytes()),
            HeaderValue::from_bytes(v.as_bytes()),
        ) {
            headers.insert(hname, hval);
        }
    }

    let bytes = match upstream.bytes().await {
        Ok(b) => b,
        Err(e) => {
            return (
                StatusCode::BAD_GATEWAY,
                format!("read body failed: {e}"),
            )
                .into_response();
        }
    };

    let mut resp = Response::builder().status(
        StatusCode::from_u16(status.as_u16()).unwrap_or(StatusCode::BAD_GATEWAY),
    );
    for (k, v) in headers.iter() {
        resp = resp.header(k, v);
    }

    match resp.body(axum::body::Body::from(bytes)) {
        Ok(r) => r.into_response(),
        Err(_) => StatusCode::INTERNAL_SERVER_ERROR.into_response(),
    }
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/", get(proxy));

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    let listener = tokio::net::TcpListener::bind(addr).await.expect("bind");
    axum::serve(listener, app).await.expect("serve");
}
