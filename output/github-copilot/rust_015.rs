fn calculate_rgba_buffer_size(width: usize, height: usize) -> Result<usize, &'static str> {
    width
        .checked_mul(height)
        .and_then(|pixels| pixels.checked_mul(4))
        .ok_or("image dimensions are too large")
}

fn allocate_rgba_buffer(width: usize, height: usize) -> Result<Vec<u8>, &'static str> {
    let size = calculate_rgba_buffer_size(width, height)?;
    Ok(vec![0u8; size])
}

fn main() -> Result<(), &'static str> {
    let width = 1920;
    let height = 1080;

    let buffer = allocate_rgba_buffer(width, height)?;
    println!(
        "Allocated RGBA buffer for {}x{} image: {} bytes",
        width,
        height,
        buffer.len()
    );

    Ok(())
}