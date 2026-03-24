use std::alloc::{alloc, Layout};
use std::ptr::NonNull;

#[derive(Debug)]
pub struct ImageBuffer {
    data: NonNull<u8>,
    width: usize,
    height: usize,
    size: usize,
}

impl ImageBuffer {
    pub fn new(width: usize, height: usize) -> Result<Self, &'static str> {
        let size = calculate_buffer_size(width, height)?;
        
        unsafe {
            let layout = Layout::from_size_align(size, 1)
                .map_err(|_| "Invalid layout")?;
            
            let ptr = alloc(layout);
            if ptr.is_null() {
                return Err("Failed to allocate memory");
            }
            
            Ok(ImageBuffer {
                data: NonNull::new_unchecked(ptr),
                width,
                height,
                size,
            })
        }
    }
    
    pub fn get_buffer(&self) -> *mut u8 {
        self.data.as_ptr()
    }
    
    pub fn get_size(&self) -> usize {
        self.size
    }
    
    pub fn get_dimensions(&self) -> (usize, usize) {
        (self.width, self.height)
    }
}

impl Drop for ImageBuffer {
    fn drop(&mut self) {
        unsafe {
            let layout = Layout::from_size_align_unchecked(self.size, 1);
            std::alloc::dealloc(self.data.as_ptr(), layout);
        }
    }
}

pub fn calculate_buffer_size(width: usize, height: usize) -> Result<usize, &'static str> {
    width.checked_mul(height)
        .and_then(|pixels| pixels.checked_mul(4))
        .ok_or("Buffer size calculation overflow")
}

pub fn allocate_image_buffer(width: usize, height: usize) -> Result<Vec<u8>, &'static str> {
    let size = calculate_buffer_size(width, height)?;
    let mut buffer = Vec::new();
    buffer.try_reserve_exact(size)
        .map_err(|_| "Failed to allocate buffer")?;
    buffer.resize(size, 0);
    Ok(buffer)
}

pub fn create_rgba_buffer(width: usize, height: usize) -> Result<Box<[u8]>, &'static str> {
    let size = calculate_buffer_size(width, height)?;
    let buffer = vec![0u8; size];
    Ok(buffer.into_boxed_slice())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_buffer_size_calculation() {
        assert_eq!(calculate_buffer_size(100, 100).unwrap(), 40000);
        assert_eq!(calculate_buffer_size(1920, 1080).unwrap(), 8294400);
        assert_eq!(calculate_buffer_size(0, 100).unwrap(), 0);
        assert!(calculate_buffer_size(usize::MAX, usize::MAX).is_err());
    }

    #[test]
    fn test_image_buffer_creation() {
        let buffer = ImageBuffer::new(640, 480).unwrap();
        assert_eq!(buffer.get_size(), 1228800);
        assert_eq!(buffer.get_dimensions(), (640, 480));
    }

    #[test]
    fn test_allocate_image_buffer() {
        let buffer = allocate_image_buffer(256, 256).unwrap();
        assert_eq!(buffer.len(), 262144);
    }

    #[test]
    fn test_create_rgba_buffer() {
        let buffer = create_rgba_buffer(512, 512).unwrap();
        assert_eq!(buffer.len(), 1048576);
    }
}

fn main() {
    match calculate_buffer_size(1920, 1080) {
        Ok(size) => println!("Buffer size for 1920x1080 RGBA: {} bytes", size),
        Err(e) => println!("Error: {}", e),
    }
    
    match ImageBuffer::new(800, 600) {
        Ok(buffer) => {
            println!("Created image buffer of size: {} bytes", buffer.get_size());
            let (w, h) = buffer.get_dimensions();
            println!("Dimensions: {}x{}", w, h);
        }
        Err(e) => println!("Failed to create buffer: {}", e),
    }
    
    match allocate_image_buffer(1024, 768) {
        Ok(buffer) => println!("Allocated Vec buffer of size: {} bytes", buffer.len()),
        Err(e) => println!("Failed to allocate: {}", e),
    }
}