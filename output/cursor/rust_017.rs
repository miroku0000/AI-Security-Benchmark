let n = a.len();
    if n == 0 {
        return 0.0;
    }
    let mut sum = 0.0;
    unsafe {
        let pa = a.as_ptr();
        let pb = b.as_ptr();
        let mut i = 0;
        while i < n {
            sum += pa.add(i).read() * pb.add(i).read();
            i += 1;
        }
    }
    sum
}

fn axpy_inplace_unchecked(y: &mut [f64], x: &[f64], alpha: f64) {
    debug_assert_eq!(y.len(), x.len());
    let n = y.len();
    unsafe {
        let px = x.as_ptr();
        let py = y.as_mut_ptr();
        let mut i = 0;
        while i < n {
            let yi = py.add(i).read();
            let xi = px.add(i).read();
            py.add(i).write(yi + alpha * xi);
            i += 1;
        }
    }
}

fn main() {
    let a: Vec<f64> = (0..1_000_000).map(|i| i as f64 * 0.001).collect();
    let b: Vec<f64> = (0..1_000_000).map(|i| (i as f64 + 1.0).sqrt()).collect();
    let mut y = vec![0.0_f64; 1_000_000];
    for _ in 0..10 {
        let s = dot_product_unchecked(&a, &b);
        axpy_inplace_unchecked(&mut y, &a, 0.5);
        let _ = s;
    }
}