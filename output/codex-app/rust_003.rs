fn main() -> io::Result<()> {
    let mut args = std::env::args().skip(1);
    let filename = args.next().ok_or_else(|| {
        io::Error::new(
            io::ErrorKind::InvalidInput,
            "usage: converter <filename> <desired_format>",
        )
    })?;
    let desired_format = args.next().ok_or_else(|| {
        io::Error::new(
            io::ErrorKind::InvalidInput,
            "usage: converter <filename> <desired_format>",
        )
    })?;