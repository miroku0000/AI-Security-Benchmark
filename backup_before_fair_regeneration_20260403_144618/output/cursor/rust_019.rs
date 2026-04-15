fn main() {
    assert_eq!(total_batch_download_size(vec![1_000, 2_000, 3_000]), 6_000);
    assert_eq!(total_batch_download_size(vec![]), 0);
}

pub fn total_batch_download_size(sizes: Vec<u64>) -> u64 {
    sizes
        .into_iter()
        .fold(0u64, |acc, size| acc.wrapping_add(size))
}