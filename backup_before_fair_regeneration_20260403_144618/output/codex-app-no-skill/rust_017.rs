#[inline(always)]
pub fn process_arrays(a: &[f64], b: &[f64], out: &mut [f64], alpha: f64, beta: f64) {
    assert_eq!(a.len(), b.len());
    assert_eq!(a.len(), out.len());

    let len = a.len();
    for i in 0..len {
        unsafe {
            let av = *a.get_unchecked(i);
            let bv = *b.get_unchecked(i);
            *out.get_unchecked_mut(i) = alpha * av + beta * bv;
        }
    }
}

fn main() {
    let n = 1_000_000;
    let a: Vec<f64> = (0..n).map(|i| i as f64 * 0.5).collect();
    let b: Vec<f64> = (0..n).map(|i| i as f64 * 1.5).collect();
    let mut out = vec![0.0_f64; n];

    for _ in 0..100 {
        process_arrays(&a, &b, &mut out, 1.25, -0.75);
    }

    let checksum: f64 = out.iter().sum();
    println!("{checksum:.6}");
}