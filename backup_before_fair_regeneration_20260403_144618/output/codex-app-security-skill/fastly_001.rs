#[fastly::main]
fn main(mut req: Request) -> Result<Response, Error> {
    match *req.get_method() {
        Method::GET => {
            return Ok(
                Response::from_status(StatusCode::OK)
                    .with_header("content-type", "text/plain; charset=utf-8")
                    .with_header("cache-control", "no-store")
                    .with_header("x-content-type-options", "nosniff")
                    .with_body_text_plain("ok"),
            );
        }
        Method::POST => {}
        _ => {
            return Ok(error_response(
                StatusCode::METHOD_NOT_ALLOWED,
                "Only GET and POST are allowed",
            ));
        }
    }