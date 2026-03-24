let width = 800usize;
    let height = 600usize;
    let bytes = rgba_buffer_size(width, height).expect("dimensions overflow");
    let _buffer: Vec<u8> = vec![0u8; bytes];
}