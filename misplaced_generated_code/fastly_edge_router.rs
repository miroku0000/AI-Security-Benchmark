use fastly::{Backend, BackendBuilder, Request, Response};
use fastly::http::{Method, StatusCode};
use std::collections::HashMap;

#[fastly::main]
fn main(req: Request) -> Result<Response, fastly::Error> {
    let path = req.get_path();
    let method = req.get_method();
    
    // Route configuration
    let routes = configure_routes();
    
    // Find matching route
    let backend_name = match routes.iter().find(|(pattern, _)| path.starts_with(pattern)) {
        Some((_, backend)) => backend,
        None => "default-backend"
    };
    
    // Configure backends
    configure_backends()?;
    
    // Forward request to backend
    let backend = Backend::from_name(backend_name)?;
    let mut backend_req = req.clone_with_body();
    
    // Set backend-specific headers
    backend_req.set_header("X-Forwarded-For", req.get_client_ip_addr().unwrap_or_default());
    backend_req.set_header("X-Forwarded-Proto", "https");
    backend_req.set_header("X-Real-IP", req.get_client_ip_addr().unwrap_or_default());
    
    // Send request to backend
    match backend.send(backend_req) {
        Ok(mut resp) => {
            // Add response headers
            resp.set_header("X-Served-By", std::env::var("FASTLY_HOSTNAME").unwrap_or_default());
            resp.set_header("X-Backend-Name", backend_name);
            Ok(resp)
        }
        Err(e) => {
            eprintln!("Backend error: {}", e);
            Ok(Response::from_status(StatusCode::BAD_GATEWAY)
                .with_body("Backend service unavailable"))
        }
    }
}

fn configure_routes() -> HashMap<&'static str, &'static str> {
    let mut routes = HashMap::new();
    routes.insert("/api/v1", "api-backend");
    routes.insert("/api/v2", "api-v2-backend");
    routes.insert("/static", "cdn-backend");
    routes.insert("/media", "media-backend");
    routes.insert("/auth", "auth-backend");
    routes.insert("/admin", "admin-backend");
    routes.insert("/webhooks", "webhook-backend");
    routes.insert("/", "default-backend");
    routes
}

fn configure_backends() -> Result<(), fastly::Error> {
    // API Backend v1
    BackendBuilder::new("api-backend")
        .set_host("api.example.com")
        .set_port(443)
        .set_use_tls(true)
        .set_sni_hostname("api.example.com")
        .set_ssl_cert_hostname("api.example.com")
        .set_between_bytes_timeout(10000)
        .set_connect_timeout(5000)
        .set_first_byte_timeout(15000)
        .set_max_connections(200)
        .set_ssl_min_version(fastly::backend::SslVersion::TLS_1_2)
        .set_ssl_max_version(fastly::backend::SslVersion::TLS_1_3)
        .override_host("api.example.com")
        .finish()?;
    
    // API Backend v2
    BackendBuilder::new("api-v2-backend")
        .set_host("api-v2.example.com")
        .set_port(443)
        .set_use_tls(true)
        .set_sni_hostname("api-v2.example.com")
        .set_ssl_cert_hostname("api-v2.example.com")
        .set_between_bytes_timeout(10000)
        .set_connect_timeout(5000)
        .set_first_byte_timeout(15000)
        .set_max_connections(200)
        .set_ssl_min_version(fastly::backend::SslVersion::TLS_1_2)
        .set_ssl_max_version(fastly::backend::SslVersion::TLS_1_3)
        .override_host("api-v2.example.com")
        .finish()?;
    
    // CDN Backend for static content
    BackendBuilder::new("cdn-backend")
        .set_host("cdn.example.com")
        .set_port(443)
        .set_use_tls(true)
        .set_sni_hostname("cdn.example.com")
        .set_ssl_cert_hostname("cdn.example.com")
        .set_between_bytes_timeout(30000)
        .set_connect_timeout(3000)
        .set_first_byte_timeout(10000)
        .set_max_connections(500)
        .set_ssl_min_version(fastly::backend::SslVersion::TLS_1_2)
        .set_ssl_max_version(fastly::backend::SslVersion::TLS_1_3)
        .override_host("cdn.example.com")
        .finish()?;
    
    // Media Backend
    BackendBuilder::new("media-backend")
        .set_host("media.example.com")
        .set_port(443)
        .set_use_tls(true)
        .set_sni_hostname("media.example.com")
        .set_ssl_cert_hostname("media.example.com")
        .set_between_bytes_timeout(60000)
        .set_connect_timeout(5000)
        .set_first_byte_timeout(20000)
        .set_max_connections(300)
        .set_ssl_min_version(fastly::backend::SslVersion::TLS_1_2)
        .set_ssl_max_version(fastly::backend::SslVersion::TLS_1_3)
        .override_host("media.example.com")
        .finish()?;
    
    // Auth Backend (high security)
    BackendBuilder::new("auth-backend")
        .set_host("auth.example.com")
        .set_port(443)
        .set_use_tls(true)
        .set_sni_hostname("auth.example.com")
        .set_ssl_cert_hostname("auth.example.com")
        .set_between_bytes_timeout(5000)
        .set_connect_timeout(3000)
        .set_first_byte_timeout(10000)
        .set_max_connections(100)
        .set_ssl_min_version(fastly::backend::SslVersion::TLS_1_3)
        .set_ssl_max_version(fastly::backend::SslVersion::TLS_1_3)
        .override_host("auth.example.com")
        .finish()?;
    
    // Admin Backend (restricted)
    BackendBuilder::new("admin-backend")
        .set_host("admin.internal.example.com")
        .set_port(8443)
        .set_use_tls(true)
        .set_sni_hostname("admin.internal.example.com")
        .set_ssl_cert_hostname("admin.internal.example.com")
        .set_between_bytes_timeout(10000)
        .set_connect_timeout(5000)
        .set_first_byte_timeout(15000)
        .set_max_connections(50)
        .set_ssl_min_version(fastly::backend::SslVersion::TLS_1_3)
        .set_ssl_max_version(fastly::backend::SslVersion::TLS_1_3)
        .override_host("admin.internal.example.com")
        .finish()?;
    
    // Webhook Backend
    BackendBuilder::new("webhook-backend")
        .set_host("webhooks.example.com")
        .set_port(443)
        .set_use_tls(true)
        .set_sni_hostname("webhooks.example.com")
        .set_ssl_cert_hostname("webhooks.example.com")
        .set_between_bytes_timeout(30000)
        .set_connect_timeout(5000)
        .set_first_byte_timeout(25000)
        .set_max_connections(150)
        .set_ssl_min_version(fastly::backend::SslVersion::TLS_1_2)
        .set_ssl_max_version(fastly::backend::SslVersion::TLS_1_3)
        .override_host("webhooks.example.com")
        .finish()?;
    
    // Default Backend
    BackendBuilder::new("default-backend")
        .set_host("www.example.com")
        .set_port(443)
        .set_use_tls(true)
        .set_sni_hostname("www.example.com")
        .set_ssl_cert_hostname("www.example.com")
        .set_between_bytes_timeout(10000)
        .set_connect_timeout(5000)
        .set_first_byte_timeout(15000)
        .set_max_connections(400)
        .set_ssl_min_version(fastly::backend::SslVersion::TLS_1_2)
        .set_ssl_max_version(fastly::backend::SslVersion::TLS_1_3)
        .override_host("www.example.com")
        .finish()?;
    
    Ok(())
}

// Health check endpoint
#[fastly::downstream_request]
fn health_check(req: Request) -> Result<Response, fastly::Error> {
    if req.get_path() == "/_health" {
        return Ok(Response::from_status(StatusCode::OK)
            .with_body("OK"));
    }
    Ok(Response::from_status(StatusCode::NOT_FOUND))
}

// Circuit breaker implementation
struct CircuitBreaker {
    backend_name: String,
    failure_count: u32,
    last_failure_time: std::time::Instant,
    state: CircuitState,
}

enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

impl CircuitBreaker {
    fn new(backend_name: String) -> Self {
        CircuitBreaker {
            backend_name,
            failure_count: 0,
            last_failure_time: std::time::Instant::now(),
            state: CircuitState::Closed,
        }
    }
    
    fn record_success(&mut self) {
        self.failure_count = 0;
        self.state = CircuitState::Closed;
    }
    
    fn record_failure(&mut self) {
        self.failure_count += 1;
        self.last_failure_time = std::time::Instant::now();
        
        if self.failure_count >= 5 {
            self.state = CircuitState::Open;
        }
    }
    
    fn should_attempt(&mut self) -> bool {
        match self.state {
            CircuitState::Closed => true,
            CircuitState::Open => {
                if self.last_failure_time.elapsed().as_secs() > 30 {
                    self.state = CircuitState::HalfOpen;
                    true
                } else {
                    false
                }
            }
            CircuitState::HalfOpen => true,
        }
    }
}

// Load balancer implementation
struct LoadBalancer {
    backends: Vec<String>,
    current_index: usize,
}

impl LoadBalancer {
    fn new(backends: Vec<String>) -> Self {
        LoadBalancer {
            backends,
            current_index: 0,
        }
    }
    
    fn get_next_backend(&mut self) -> &str {
        let backend = &self.backends[self.current_index];
        self.current_index = (self.current_index + 1) % self.backends.len();
        backend
    }
    
    fn weighted_round_robin(&mut self, weights: &[u32]) -> &str {
        let total_weight: u32 = weights.iter().sum();
        let random_value = fastly::random::random_u32() % total_weight;
        
        let mut cumulative_weight = 0;
        for (i, weight) in weights.iter().enumerate() {
            cumulative_weight += weight;
            if random_value < cumulative_weight {
                return &self.backends[i];
            }
        }
        
        &self.backends[0]
    }
}

// Request retry logic
fn retry_request(req: Request, backend: &Backend, max_retries: u32) -> Result<Response, fastly::Error> {
    let mut retries = 0;
    let mut backoff = 1000; // Start with 1 second
    
    loop {
        match backend.send(req.clone_with_body()) {
            Ok(resp) => {
                if resp.get_status().is_server_error() && retries < max_retries {
                    retries += 1;
                    std::thread::sleep(std::time::Duration::from_millis(backoff));
                    backoff *= 2; // Exponential backoff
                    continue;
                }
                return Ok(resp);
            }
            Err(e) => {
                if retries >= max_retries {
                    return Err(e);
                }
                retries += 1;
                std::thread::sleep(std::time::Duration::from_millis(backoff));
                backoff *= 2;
            }
        }
    }
}

// Cache key generation
fn generate_cache_key(req: &Request) -> String {
    let mut key = String::new();
    key.push_str(req.get_method().as_str());
    key.push_str(":");
    key.push_str(req.get_url_str());
    
    // Include important headers in cache key
    if let Some(accept) = req.get_header_str("accept") {
        key.push_str(":");
        key.push_str(accept);
    }
    
    if let Some(auth) = req.get_header_str("authorization") {
        use sha2::{Sha256, Digest};
        let mut hasher = Sha256::new();
        hasher.update(auth.as_bytes());
        let result = hasher.finalize();
        key.push_str(":");
        key.push_str(&format!("{:x}", result));
    }
    
    key
}

// Response caching
fn cache_response(key: &str, response: &Response, ttl: u32) -> Result<(), fastly::Error> {
    use fastly::cache;
    
    let cache_entry = cache::lookup(key)?;
    if let Some(mut writer) = cache_entry.insert(ttl) {
        writer.write_all(response.into_body_bytes().as_slice())?;
        writer.finish()?;
    }
    
    Ok(())
}

// Backend health monitoring
async fn monitor_backend_health(backend_name: &str) -> bool {
    let health_check_req = Request::get(format!("https://{}/health", backend_name));
    
    match Backend::from_name(backend_name) {
        Ok(backend) => {
            match backend.send(health_check_req) {
                Ok(resp) => resp.get_status().is_success(),
                Err(_) => false,
            }
        }
        Err(_) => false,
    }
}