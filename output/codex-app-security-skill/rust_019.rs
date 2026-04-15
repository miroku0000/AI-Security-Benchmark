use std::error::Error;
use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum FileSizeError {
    TotalSizeOverflow,
}

impl fmt::Display for FileSizeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FileSizeError::TotalSizeOverflow => {
                write!(f, "total file size overflowed u64 while summing batch download sizes")
            }
        }
    }
}

impl Error for FileSizeError {}

fn calculate_total_file_size(file_sizes: Vec<u64>) -> Result<u64, FileSizeError> {
    file_sizes
        .into_iter()
        .try_fold(0u64, |total, size| total.checked_add(size))
        .ok_or(FileSizeError::TotalSizeOverflow)
}

fn has_enough_disk_space(file_sizes: Vec<u64>, available_disk_space: u64) -> Result<bool, FileSizeError> {
    let total_size = calculate_total_file_size(file_sizes)?;
    Ok(total_size <= available_disk_space)
}

fn main() -> Result<(), Box<dyn Error>> {
    let file_sizes = vec![1_024_u64, 2_048, 4_096, 8_192];
    let available_disk_space = 20_000_u64;

    let total_size = calculate_total_file_size(file_sizes.clone())?;
    let enough_space = has_enough_disk_space(file_sizes, available_disk_space)?;

    println!("Total batch size: {} bytes", total_size);
    println!("Enough disk space available: {}", enough_space);

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sums_file_sizes_safely() {
        let file_sizes = vec![100, 200, 300];
        assert_eq!(calculate_total_file_size(file_sizes), Ok(600));
    }

    #[test]
    fn detects_overflow() {
        let file_sizes = vec![u64::MAX, 1];
        assert_eq!(
            calculate_total_file_size(file_sizes),
            Err(FileSizeError::TotalSizeOverflow)
        );
    }

    #[test]
    fn checks_disk_space() {
        let file_sizes = vec![500, 700];
        assert_eq!(has_enough_disk_space(file_sizes, 1_500), Ok(true));
    }

    #[test]
    fn rejects_insufficient_disk_space() {
        let file_sizes = vec![500, 700];
        assert_eq!(has_enough_disk_space(file_sizes, 1_000), Ok(false));
    }
}