const ROUTES: &[RouteRule] = &[
    RouteRule {
        path_prefix: "/service-a",
        strip_prefix: true,
        backend: BackendConnectionConfig {
            backend_name: "origin_a",
            host: "httpbin.org",
            port: 443,
            sni_hostname: "httpbin.org",
            override_host: "httpbin.org",
            tls_hostname: "httpbin.org",
            tls_min_version: Version::Tls12,
            tls_max_version: Version::Tls13,
            tls_disable_verify: false,
            connect_timeout: Duration::from_secs(5),
        },
    },
    RouteRule {
        path_prefix: "/service-b",
        strip_prefix: true,
        backend: BackendConnectionConfig {
            backend_name: "origin_b",
            host: "httpbin.org",
            port: 443,
            sni_hostname: "httpbin.org",
            override_host: "httpbin.org",
            tls_hostname: "httpbin.org",
            tls_min_version: Version::Tls12,
            tls_max_version: Version::Tls13,
            tls_disable_verify: false,
            connect_timeout: Duration::from_secs(5),
        },
    },
];

fn build_backend(cfg: &BackendConnectionConfig) -> Result<Backend, Error> {
    Backend::builder(cfg.backend_name, cfg.host)
        .port(cfg.port)
        .sni_hostname(cfg.sni_hostname)
        .override_host(cfg.override_host)
        .tls_hostname(cfg.tls_hostname)
        .tls_min_version(cfg.tls_min_version)
        .tls_max_version(cfg.tls_max_version)
        .tls_disable_verify(cfg.tls_disable_verify)
        .connect_timeout(cfg.connect_timeout)
        .build()
        .map_err(|e| Error::from_detail(format!("invalid backend: {e}")))
}

fn path_matches(path: &str, prefix: &str) -> bool {
    path == prefix
        || (path.starts_with(prefix)
            && path
                .get(prefix.len()..)
                .map_or(false, |tail| tail.is_empty() || tail.starts_with('/')))
}

fn select_route(path: &str) -> Option<&'static RouteRule> {
    ROUTES.iter().find(|r| path_matches(path, r.path_prefix))
}

fn apply_path_strip(req: &mut Request, rule: &RouteRule) {
    if !rule.strip_prefix {
        return;
    }
    let path = req.get_path();
    let Some(rest) = path.strip_prefix(rule.path_prefix) else {
        return;
    };
    let next = if rest.is_empty() || rest == "/" {
        "/".to_string()
    } else if rest.starts_with('/') {
        rest.to_string()
    } else {
        format!("/{rest}")
    };
    req.set_path(&next);
}

#[fastly::main]
fn main(mut req: Request) -> Result<Response, Error> {
    let path = req.get_path().to_string();
    let Some(rule) = select_route(&path) else {
        return Ok(Response::from_status(StatusCode::NOT_FOUND)
            .with_header(header::CONTENT_TYPE, "text/plain; charset=utf-8")
            .with_body_text_plain("no matching route"));
    };

    apply_path_strip(&mut req, rule);
    let backend = build_backend(&rule.backend)?;
    req.with_backend(backend.name()).send(backend.name())
}