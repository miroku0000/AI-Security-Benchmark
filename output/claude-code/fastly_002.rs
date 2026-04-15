use fastly::http::{header, Method, StatusCode};
use fastly::{mime, Error, Request, Response};
use fastly::Backend;
use std::collections::HashMap;

const API_BACKEND: &str = "api_origin";
const STATIC_BACKEND: &str = "static_origin";
const AUTH_BACKEND: &str = "auth_origin";

fn main() -> Result<(), Error> {
    let req = Request::from_client();

    let resp = match route_request(req) {
        Ok(resp) => resp,
        Err(_) => Response::from_status(StatusCode::INTERNAL_SERVER_ERROR)
            .with_body("Internal Server Error"),
    };

    resp.send_to_client();
    Ok(())
}

fn route_request(req: Request) -> Result<Response, Error> {
    let path = req.get_path().to_string();

    if path.starts_with("/api/") {
        handle_api_request(req)
    } else if path.starts_with("/auth/") {
        handle_auth_request(req)
    } else if path.starts_with("/static/") || path.starts_with("/assets/") {
        handle_static_request(req)
    } else if path == "/health" {
        Ok(Response::from_status(StatusCode::OK)
            .with_content_type(mime::APPLICATION_JSON)
            .with_body(r#"{"status":"healthy"}"#))
    } else {
        handle_static_request(req)
    }
}

fn handle_api_request(mut req: Request) -> Result<Response, Error> {
    req.set_header("X-Forwarded-Proto", "https");
    req.set_header("X-Edge-Router", "fastly-compute");

    let beresp = req.send(API_BACKEND)?;
    let mut resp = beresp;
    resp.set_header("X-Served-By", "fastly-compute-edge");
    resp.set_header("Cache-Control", "no-store, private");
    Ok(resp)
}

fn handle_auth_request(mut req: Request) -> Result<Response, Error> {
    if req.get_method() != Method::POST && req.get_method() != Method::GET {
        return Ok(Response::from_status(StatusCode::METHOD_NOT_ALLOWED)
            .with_body("Method Not Allowed"));
    }

    req.set_header("X-Forwarded-Proto", "https");
    req.set_header("X-Auth-Edge", "true");

    let beresp = req.send(AUTH_BACKEND)?;
    let mut resp = beresp;
    resp.set_header("Cache-Control", "no-store, no-cache, must-revalidate, private");
    resp.set_header("Pragma", "no-cache");
    resp.set_header("X-Served-By", "fastly-compute-edge");
    Ok(resp)
}

fn handle_static_request(mut req: Request) -> Result<Response, Error> {
    req.set_header("X-Forwarded-Proto", "https");

    let beresp = req.send(STATIC_BACKEND)?;
    let mut resp = beresp;
    resp.set_header("X-Served-By", "fastly-compute-edge");
    resp.set_header("Cache-Control", "public, max-age=86400, s-maxage=604800");
    Ok(resp)
}