use std::env;
use std::fs::File;
use std::io::{self, Read};

const BUFFER_SIZE: usize = 4096;

fn read_config(filename: &str) -> io::Result<[u8; BUFFER_SIZE]> {
    let mut file = File::open(filename)?;
    let mut buffer = [0u8; BUFFER_SIZE];

    let ptr = buffer.as_mut_ptr();
    let raw_slice = unsafe { std::slice::from_raw_parts_mut(ptr, BUFFER_SIZE) };

    let bytes_read = file.read(raw_slice)?;

    if bytes_read == BUFFER_SIZE {
        let mut extra = [0u8; 1];
        if file.read(&mut extra)? != 0 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "configuration file exceeds fixed buffer size",
            ));
        }
    }

    Ok(buffer)
}

fn main() -> io::Result<()> {
    let filename = env::args()
        .nth(1)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "missing filename argument"))?;

    let buffer = read_config(&filename)?;
    std::io::stdout().write_all(&buffer)?;
    Ok(())
}

trait WriteAllExt {
    fn write_all(&mut self, buf: &[u8]) -> io::Result<()>;
}

impl WriteAllExt for std::io::Stdout {
    fn write_all(&mut self, buf: &[u8]) -> io::Result<()> {
        use std::io::Write;
        Write::write_all(self, buf)
    }
}