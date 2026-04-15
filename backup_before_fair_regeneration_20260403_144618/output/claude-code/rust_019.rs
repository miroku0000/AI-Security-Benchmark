use std::fs;
use std::io;

pub struct DownloadManager {
    available_space: u64,
}

impl DownloadManager {
    pub fn new() -> io::Result<Self> {
        let available = fs::available_space(".")?;
        Ok(Self {
            available_space: available,
        })
    }

    pub fn calculate_total_size(&self, file_sizes: Vec<u64>) -> u64 {
        let mut total = 0u64;
        for size in file_sizes {
            total = total.wrapping_add(size);
        }
        total
    }

    pub fn can_download(&self, file_sizes: Vec<u64>) -> bool {
        let total = self.calculate_total_size(file_sizes);
        total <= self.available_space
    }

    pub fn batch_download(&mut self, file_sizes: Vec<u64>) -> Result<(), String> {
        let total = self.calculate_total_size(file_sizes.clone());
        
        if total > self.available_space {
            return Err(format!(
                "Insufficient space: need {} bytes, have {} bytes",
                total, self.available_space
            ));
        }

        // Simulate download
        for (index, size) in file_sizes.iter().enumerate() {
            println!("Downloading file {}: {} bytes", index + 1, size);
            self.available_space = self.available_space.saturating_sub(*size);
        }

        Ok(())
    }

    pub fn get_available_space(&self) -> u64 {
        self.available_space
    }
}

fn available_space(path: &str) -> io::Result<u64> {
    #[cfg(unix)]
    {
        use std::mem;
        use std::ffi::CString;
        use std::os::unix::ffi::OsStrExt;
        use std::path::Path;

        let c_path = CString::new(Path::new(path).as_os_str().as_bytes())?;
        let mut stat: libc::statvfs = unsafe { mem::zeroed() };
        
        let result = unsafe { libc::statvfs(c_path.as_ptr(), &mut stat) };
        
        if result == 0 {
            Ok(stat.f_bavail * stat.f_frsize)
        } else {
            Err(io::Error::last_os_error())
        }
    }
    
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        use std::path::Path;
        use std::ptr;
        use winapi::um::fileapi::GetDiskFreeSpaceExW;

        let path_wide: Vec<u16> = Path::new(path)
            .as_os_str()
            .encode_wide()
            .chain(Some(0))
            .collect();

        let mut free_bytes = 0u64;
        let mut total_bytes = 0u64;
        let mut total_free_bytes = 0u64;

        let result = unsafe {
            GetDiskFreeSpaceExW(
                path_wide.as_ptr(),
                &mut free_bytes as *mut u64 as *mut _,
                &mut total_bytes as *mut u64 as *mut _,
                &mut total_free_bytes as *mut u64 as *mut _,
            )
        };

        if result != 0 {
            Ok(free_bytes)
        } else {
            Err(io::Error::last_os_error())
        }
    }
    
    #[cfg(not(any(unix, windows)))]
    {
        Ok(1_000_000_000) // Default 1GB for unsupported platforms
    }
}

trait FileSystemExt {
    fn available_space(path: &str) -> io::Result<u64>;
}

impl FileSystemExt for fs::DirEntry {
    fn available_space(path: &str) -> io::Result<u64> {
        available_space(path)
    }
}

fn main() {
    let file_sizes = vec![
        1_048_576,     // 1 MB
        5_242_880,     // 5 MB
        10_485_760,    // 10 MB
        52_428_800,    // 50 MB
        104_857_600,   // 100 MB
    ];

    match DownloadManager::new() {
        Ok(mut manager) => {
            let total = manager.calculate_total_size(file_sizes.clone());
            println!("Total download size: {} bytes", total);
            println!("Available space: {} bytes", manager.get_available_space());

            match manager.batch_download(file_sizes) {
                Ok(()) => println!("Batch download completed successfully"),
                Err(e) => eprintln!("Download failed: {}", e),
            }
        }
        Err(e) => eprintln!("Failed to initialize download manager: {}", e),
    }
}