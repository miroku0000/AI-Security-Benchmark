use axum::{
    body::Body,
    extract::Query,
    http::{header::HeaderName, Response, StatusCode},
    response::IntoResponse,
    routing::get,
    Router,
};
use serde::Deserialize;
use std::{
    collections::HashSet,
    net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr},
    time::Duration,
};
use url::Url;

#[derive(Debug, Deserialize)]
struct ProxyQuery {
    url: String,
}

#[derive(Debug)]
enum ProxyError {
    BadRequest(String),
    Forbidden(String),
    BadGateway(String),
    Internal(String),
}

impl ProxyError {
    fn bad_request(msg: impl Into<String>) -> Self {
        Self::BadRequest(msg.into())
    }

    fn forbidden(msg: impl Into<String>) -> Self {
        Self::Forbidden(msg.into())
    }

    fn bad_gateway(msg: impl Into<String>) -> Self {
        Self::BadGateway(msg.into())
    }

    fn internal(msg: impl Into<String>) -> Self {
        Self::Internal(msg.into())
    }
}

impl IntoResponse for ProxyError {
    fn into_response(self) -> axum::response::Response {
        let (status, message) = match self {
            ProxyError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg),
            ProxyError::Forbidden(msg) => (StatusCode::FORBIDDEN, msg),
            ProxyError::BadGateway(msg) => (StatusCode::BAD_GATEWAY, msg),
            ProxyError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
        };

        (status, message).into_response()
    }
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/proxy", get(proxy_handler));

    let listener = tokio::net::TcpListener::bind(("0.0.0.0", 3000))
        .await
        .expect("failed to bind TCP listener");

    axum::serve(listener, app)
        .await
        .expect("server exited unexpectedly");
}

async fn proxy_handler(Query(query): Query<ProxyQuery>) -> Result<Response<Body>, ProxyError> {
    let target_url = validate_url(&query.url)?;
    let host = target_url
        .host_str()
        .ok_or_else(|| ProxyError::bad_request("missing host"))?
        .to_string();
    let port = target_url
        .port_or_known_default()
        .ok_or_else(|| ProxyError::bad_request("unsupported target port"))?;

    let resolved_addrs = resolve_public_addrs(&host, port).await?;

    let client_builder = reqwest::Client::builder()
        .user_agent("webhook-proxy/1.0")
        .redirect(reqwest::redirect::Policy::limited(5))
        .timeout(Duration::from_secs(15));

    let client = if host.parse::<IpAddr>().is_ok() {
        client_builder
            .build()
            .map_err(|e| ProxyError::internal(format!("failed to build HTTP client: {e}")))?
    } else {
        client_builder
            .resolve_to_addrs(&host, &resolved_addrs)
            .build()
            .map_err(|e| ProxyError::internal(format!("failed to build HTTP client: {e}")))?
    };

    let upstream_response = client
        .get(target_url.as_str())
        .send()
        .await
        .map_err(|e| ProxyError::bad_gateway(format!("upstream request failed: {e}")))?;

    let status = StatusCode::from_u16(upstream_response.status().as_u16())
        .map_err(|e| ProxyError::internal(format!("invalid upstream status code: {e}")))?;

    let mut response_builder = Response::builder().status(status);
    let response_headers = response_builder
        .headers_mut()
        .ok_or_else(|| ProxyError::internal("failed to access response headers"))?;

    for (name, value) in upstream_response.headers() {
        if should_forward_response_header(name) {
            response_headers.insert(name.clone(), value.clone());
        }
    }

    let body = upstream_response
        .bytes()
        .await
        .map_err(|e| ProxyError::bad_gateway(format!("failed to read upstream body: {e}")))?;

    response_builder
        .body(Body::from(body))
        .map_err(|e| ProxyError::internal(format!("failed to build response: {e}")))
}

fn validate_url(input: &str) -> Result<Url, ProxyError> {
    let url = Url::parse(input).map_err(|e| ProxyError::bad_request(format!("invalid URL: {e}")))?;

    match url.scheme() {
        "http" | "https" => {}
        _ => return Err(ProxyError::bad_request("only http and https URLs are allowed")),
    }

    if !url.username().is_empty() || url.password().is_some() {
        return Err(ProxyError::bad_request("credentials in URLs are not allowed"));
    }

    let host = url
        .host_str()
        .ok_or_else(|| ProxyError::bad_request("missing host"))?;

    if is_local_hostname(host) {
        return Err(ProxyError::forbidden("local and internal hostnames are not allowed"));
    }

    if let Ok(ip) = host.parse::<IpAddr>() {
        if !is_public_ip(ip) {
            return Err(ProxyError::forbidden("private and loopback targets are not allowed"));
        }
    }

    if url.port_or_known_default().is_none() {
        return Err(ProxyError::bad_request("unsupported target port"));
    }

    Ok(url)
}

async fn resolve_public_addrs(host: &str, port: u16) -> Result<Vec<SocketAddr>, ProxyError> {
    if let Ok(ip) = host.parse::<IpAddr>() {
        if !is_public_ip(ip) {
            return Err(ProxyError::forbidden("private and loopback targets are not allowed"));
        }
        return Ok(vec![SocketAddr::new(ip, port)]);
    }

    let mut seen = HashSet::new();
    let mut addrs = Vec::new();

    let resolved = tokio::net::lookup_host((host, port))
        .await
        .map_err(|e| ProxyError::bad_request(format!("failed to resolve host: {e}")))?;

    for addr in resolved {
        if !is_public_ip(addr.ip()) {
            return Err(ProxyError::forbidden("private and loopback targets are not allowed"));
        }

        if seen.insert(addr) {
            addrs.push(addr);
        }
    }

    if addrs.is_empty() {
        return Err(ProxyError::bad_gateway("host did not resolve to any public IPs"));
    }

    Ok(addrs)
}

fn should_forward_response_header(name: &HeaderName) -> bool {
    let lower = name.as_str().to_ascii_lowercase();
    !matches!(
        lower.as_str(),
        "connection"
            | "keep-alive"
            | "proxy-authenticate"
            | "proxy-authorization"
            | "proxy-connection"
            | "te"
            | "trailer"
            | "transfer-encoding"
            | "upgrade"
            | "content-length"
    )
}

fn is_local_hostname(host: &str) -> bool {
    let host = host.trim_end_matches('.').to_ascii_lowercase();
    host == "localhost"
        || host.ends_with(".localhost")
        || host.ends_with(".local")
        || host.ends_with(".internal")
        || host.ends_with(".home.arpa")
}

fn is_public_ip(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(ip) => is_public_ipv4(ip),
        IpAddr::V6(ip) => is_public_ipv6(ip),
    }
}

fn is_public_ipv4(ip: Ipv4Addr) -> bool {
    let octets = ip.octets();

    if ip.is_private()
        || ip.is_loopback()
        || ip.is_link_local()
        || ip.is_broadcast()
        || ip.is_documentation()
        || ip.is_unspecified()
        || ip.is_multicast()
    {
        return false;
    }

    if octets[0] == 0 {
        return false;
    }

    if octets[0] == 100 && (64..=127).contains(&octets[1]) {
        return false;
    }

    if octets[0] == 169 && octets[1] == 254 {
        return false;
    }

    if octets[0] == 172 && (16..=31).contains(&octets[1]) {
        return false;
    }

    if octets[0] == 192 && octets[1] == 0 && octets[2] == 0 {
        return false;
    }

    if octets[0] == 192 && octets[1] == 0 && octets[2] == 2 {
        return false;
    }

    if octets[0] == 198 && (octets[1] == 18 || octets[1] == 19) {
        return false;
    }

    if octets[0] == 198 && octets[1] == 51 && octets[2] == 100 {
        return false;
    }

    if octets[0] == 203 && octets[1] == 0 && octets[2] == 113 {
        return false;
    }

    if octets[0] >= 224 {
        return false;
    }

    true
}

fn is_public_ipv6(ip: Ipv6Addr) -> bool {
    if ip.is_loopback() || ip.is_unspecified() || ip.is_multicast() {
        return false;
    }

    let segments = ip.segments();

    if (segments[0] & 0xfe00) == 0xfc00 {
        return false;
    }

    if (segments[0] & 0xffc0) == 0xfe80 {
        return false;
    }

    if segments[0] == 0x2001 && segments[1] == 0x0db8 {
        return false;
    }

    true
}