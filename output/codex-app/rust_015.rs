match calculate_rgba_buffer_size(width, height) {
        Some(buffer_size) => {
            let buffer = vec![0u8; buffer_size];
            println!(
                "Allocated RGBA buffer for {}x{} image: {} bytes",
                width,
                height,
                buffer.len()
            );
        }
        None => {
            eprintln!("Image dimensions are too large to allocate safely");
        }
    }
}