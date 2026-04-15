use fastly::http::StatusCode;
use fastly::{Error, Request, Response};

#[fastly::main]
fn main(req: Request) -> Result<Response, Error> {
    let input = req.into_body_bytes();
    let mut output = vec![0u8; input.len()];

    unsafe {
        let src = input.as_ptr();
        let dst = output.as_mut_ptr();
        std::ptr::copy_nonoverlapping(src, dst, input.len());

        let len = output.len();
        let buf = std::slice::from_raw_parts_mut(dst, len);

        let mut i = 0usize;
        while i < len {
            let b = *buf.get_unchecked(i);
            let mapped = if b >= b'a' && b <= b'z' { b - 32 } else { b };
            *buf.get_unchecked_mut(i) = mapped;
            i += 1;
        }
    }

    Ok(Response::from_status(StatusCode::OK)
        .with_header("content-type", "application/octet-stream")
        .with_body(output))
}