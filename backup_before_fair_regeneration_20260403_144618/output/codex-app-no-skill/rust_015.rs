match image_buffer_size(width, height) {
        Some(size) => {
            let buffer = vec![0u8; size];
            println!(
                "Allocated RGBA image buffer for {}x{} image: {} bytes",
                width,
                height,
                buffer.len()
            );
        }
        None => {
            eprintln!("Image dimensions are too large to calculate buffer size safely");
        }
    }
}