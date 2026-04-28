use fastly::{Request, Response, Body, http::StatusCode, http::header};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct BackendConfig {
    host: String,
    port: u16,
    sni: Option<String>,
    use_tls: bool,
    connect_timeout: u64,
    read_timeout: u64,
    weight: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RouteConfig {
    path_prefix: String,
    backend_name: String,
    method: Option<String>,
}

struct RequestRouter {
    backends: HashMap<String, BackendConfig>,
    routes: Vec<RouteConfig>,
}

impl RequestRouter {
    fn new() -> Self {
        let mut backends = HashMap::new();

        backends.insert(
            "api_backend".to_string(),
            BackendConfig {
                host: "api.example.com".to_string(),
                port: 443,
                sni: Some("api.example.com".to_string()),
                use_tls: true,
                connect_timeout: 5000,
                read_timeout: 10000,
                weight: 100,
            },
        );

        backends.insert(
            "image_backend".to_string(),
            BackendConfig {
                host: "images.example.com".to_string(),
                port: 443,
                sni: Some("images.example.com".to_string()),
                use_tls: true,
                connect_timeout: 5000,
                read_timeout: 15000,
                weight: 100,
            },
        );

        backends.insert(
            "static_backend".to_string(),
            BackendConfig {
                host: "static.example.com".to_string(),
                port: 80,
                sni: None,
                use_tls: false,
                connect_timeout: 3000,
                read_timeout: 8000,
                weight: 100,
            },
        );

        backends.insert(
            "origin_backend".to_string(),
            BackendConfig {
                host: "origin.example.com".to_string(),
                port: 443,
                sni: Some("origin.example.com".to_string()),
                use_tls: true,
                connect_timeout: 5000,
                read_timeout: 20000,
                weight: 100,
            },
        );

        let routes = vec![
            RouteConfig {
                path_prefix: "/api/".to_string(),
                backend_name: "api_backend".to_string(),
                method: None,
            },
            RouteConfig {
                path_prefix: "/images/".to_string(),
                backend_name: "image_backend".to_string(),
                method: None,
            },
            RouteConfig {
                path_prefix: "/static/".to_string(),
                backend_name: "static_backend".to_string(),
                method: None,
            },
            RouteConfig {
                path_prefix: "/".to_string(),
                backend_name: "origin_backend".to_string(),
                method: None,
            },
        ];

        RequestRouter { backends, routes }
    }

    fn find_backend(&self, path: &str, method: &str) -> Option<String> {
        for route in &self.routes {
            if path.starts_with(&route.path_prefix) {
                if let Some(ref allowed_method) = route.method {
                    if method.to_uppercase() == allowed_method.to_uppercase() {
                        return Some(route.backend_name.clone());
                    }
                } else {
                    return Some(route.backend_name.clone());
                }
            }
        }
        None
    }
}

fn create_backend_request(
    original_req: &Request,
    backend_config: &BackendConfig,
) -> Result<Request, String> {
    let mut backend_req = original_req.clone_without_body();

    backend_req.set_header(header::HOST, &backend_config.host);

    if let Some(ref sni) = backend_config.sni {
        backend_req.set_header("X-Forwarded-For", "127.0.0.1");
        backend_req.set_header("X-Forwarded-Host", sni);
    }

    if !backend_req.contains_header("User-Agent") {
        backend_req.set_header("User-Agent", "Fastly-Compute/1.0");
    }

    if !backend_req.contains_header("Via") {
        backend_req.set_header("Via", "fastly-compute-edge/1.0");
    }

    Ok(backend_req)
}

fn connect_to_backend(
    mut backend_req: Request,
    backend_config: &BackendConfig,
    backend_name: &str,
) -> Result<Response, String> {
    backend_req.set_header("X-Backend-Name", backend_name);
    backend_req.set_header("X-Backend-Host", &backend_config.host);
    backend_req.set_header("X-Backend-Port", backend_config.port.to_string());

    if backend_config.use_tls {
        backend_req.set_header("X-Backend-Protocol", "https");
        if let Some(ref sni) = backend_config.sni {
            backend_req.set_header("X-Backend-SNI", sni);
        }
    } else {
        backend_req.set_header("X-Backend-Protocol", "http");
    }

    backend_req.set_header(
        "X-Connect-Timeout",
        backend_config.connect_timeout.to_string(),
    );
    backend_req.set_header("X-Read-Timeout", backend_config.read_timeout.to_string());

    let response = backend_req
        .send(backend_name)
        .map_err(|e| format!("Backend connection failed: {}", e))?;

    Ok(response)
}

fn handle_error(status: StatusCode, message: &str) -> Response {
    let body_content = serde_json::json!({
        "error": message,
        "status": status.as_u16(),
        "timestamp": std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
    })
    .to_string();

    Response::from_status(status)
        .with_header(header::CONTENT_TYPE, "application/json")
        .with_body(body_content)
}

fn log_request(method: &str, path: &str, backend: &str, config: &BackendConfig) {
    eprintln!(
        "[REQUEST] {} {} -> {} ({}:{})",
        method, path, backend, config.host, config.port
    );
}

#[fastly::main]
fn main(mut req: Request) -> Result<Response, Box<dyn std::error::Error>> {
    let router = RequestRouter::new();

    let method = req.get_method().to_string();
    let path = req.get_path().to_string();

    match router.find_backend(&path, &method) {
        Some(backend_name) => {
            if let Some(backend_config) = router.backends.get(&backend_name).cloned() {
                log_request(&method, &path, &backend_name, &backend_config);

                match create_backend_request(&req, &backend_config) {
                    Ok(backend_req) => {
                        let body = req.take_body();
                        let backend_req = backend_req.with_body(body);

                        match connect_to_backend(backend_req, &backend_config, &backend_name) {
                            Ok(mut response) => {
                                response.set_header("X-Served-By", "fastly-compute");
                                response.set_header("X-Backend-Name", backend_name);
                                Ok(response)
                            }
                            Err(e) => {
                                eprintln!("[ERROR] Backend connection error: {}", e);
                                Ok(handle_error(
                                    StatusCode::BAD_GATEWAY,
                                    &format!("Backend error: {}", e),
                                ))
                            }
                        }
                    }
                    Err(e) => {
                        eprintln!("[ERROR] Request creation error: {}", e);
                        Ok(handle_error(
                            StatusCode::INTERNAL_SERVER_ERROR,
                            &format!("Request error: {}", e),
                        ))
                    }
                }
            } else {
                eprintln!("[ERROR] Backend not configured: {}", backend_name);
                Ok(handle_error(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "Backend not available",
                ))
            }
        }
        None => {
            eprintln!("[WARNING] No matching route for: {} {}", method, path);
            Ok(handle_error(
                StatusCode::NOT_FOUND,
                &format!("No route found for {} {}", method, path),
            ))
        }
    }
}