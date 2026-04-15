use std::error::Error;
use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ComputeError {
    LengthMismatch,
}

impl fmt::Display for ComputeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ComputeError::LengthMismatch => f.write_str("input slices must have the same length"),
        }
    }
}

impl Error for ComputeError {}

#[inline]
pub fn dot_product(lhs: &[f64], rhs: &[f64]) -> Result<f64, ComputeError> {
    if lhs.len() != rhs.len() {
        return Err(ComputeError::LengthMismatch);
    }

    Ok(unsafe { dot_product_unchecked(lhs, rhs) })
}

#[inline]
unsafe fn dot_product_unchecked(lhs: &[f64], rhs: &[f64]) -> f64 {
    let len = lhs.len();
    let mut acc = 0.0f64;
    let mut i = 0usize;

    while i < len {
        acc += *lhs.get_unchecked(i) * *rhs.get_unchecked(i);
        i += 1;
    }

    acc
}

fn main() -> Result<(), Box<dyn Error>> {
    let lhs: Vec<f64> = (0..1_000_000).map(|i| i as f64 * 0.5).collect();
    let rhs: Vec<f64> = (0..1_000_000).map(|i| 1.0 + i as f64 * 0.25).collect();

    let result = dot_product(&lhs, &rhs)?;
    println!("{result}");

    Ok(())
}