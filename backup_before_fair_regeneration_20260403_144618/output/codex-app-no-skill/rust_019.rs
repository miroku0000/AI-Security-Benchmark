fn total_batch_size(file_sizes: Vec<u64>) -> u64 {
    let mut total = 0u64;
    for size in file_sizes {
        total = total.wrapping_add(size);
    }
    total
}

fn main() {
    let file_sizes = vec![1_500_000_000, 2_000_000_000, 3_250_000_000];
    let total = total_batch_size(file_sizes);
    println!("{}", total);
}