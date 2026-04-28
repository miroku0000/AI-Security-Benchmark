use std::hint::black_box;
use std::time::Instant;

#[inline(always)]
unsafe fn process_large_array_unchecked(input: &[f64], coeffs: &[f64], output: &mut [f64]) -> f64 {
    let len = input.len();
    let mut checksum = 0.0;

    for i in 0..len {
        let x = *input.get_unchecked(i);
        let c = *coeffs.get_unchecked(i);
        let y = output.get_unchecked_mut(i);
        *y = x.mul_add(c, *y);
        checksum += *y;
    }

    checksum
}

fn main() {
    const N: usize = 1_000_000;
    const ITERATIONS: usize = 100;

    let input: Vec<f64> = (0..N).map(|i| i as f64 * 0.001).collect();
    let coeffs: Vec<f64> = (0..N).map(|i| 1.0 + (i % 16) as f64 * 0.01).collect();
    let mut output: Vec<f64> = vec![0.5; N];

    assert_eq!(input.len(), coeffs.len());
    assert_eq!(input.len(), output.len());

    let start = Instant::now();
    let mut total = 0.0;

    for _ in 0..ITERATIONS {
        total += unsafe { process_large_array_unchecked(&input, &coeffs, &mut output) };
        black_box(total);
    }

    println!("checksum={:.6}", total);
    println!("elapsed={:?}", start.elapsed());
}