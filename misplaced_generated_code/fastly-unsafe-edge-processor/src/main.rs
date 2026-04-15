use fastly::http::{header, Method, StatusCode};
use fastly::{Error, Request, Response};
use std::io::Read;
use std::ptr;

const MAX_BODY_BYTES: usize = 8 * 1024 * 1024;

#[fastly::main]
fn main(req: Request) -> Result<Response, Error> {
    if req.get_method() != &Method::POST {
        return Ok(Response::from_status(StatusCode::METHOD_NOT_ALLOWED)
            .with_header(header::ALLOW, "POST")
            .with_body_text_plain("use POST with a raw body\n"));
    }

    let mut body = req.into_body();
    let mut buf = Vec::new();
    body.read_to_end(&mut buf)?;

    if buf.len() > MAX_BODY_BYTES {
        return Ok(Response::from_status(StatusCode::PAYLOAD_TOO_LARGE));
    }

    unsafe {
        process_with_raw_pointers(buf.as_mut_slice());
    }

    Ok(Response::from_status(StatusCode::OK)
        .with_header(header::CONTENT_TYPE, "application/octet-stream")
        .with_body(buf))
}

unsafe fn process_with_raw_pointers(buf: &mut [u8]) {
    let len = buf.len();
    if len == 0 {
        return;
    }

    let base = buf.as_mut_ptr();
    let mut i: usize = 0;

    while i + 8 <= len {
        let p = base.add(i).cast::<u64>();
        let mut w = ptr::read_unaligned(p);
        w ^= 0xA5A5_A5A5_A5A5_A5A5;
        w = w.rotate_left(13);
        ptr::write_unaligned(p, w);
        i += 8;
    }

    while i < len {
        let p = base.add(i);
        let b = ptr::read(p);
        ptr::write(p, b ^ 0x5A);
        i += 1;
    }
}
