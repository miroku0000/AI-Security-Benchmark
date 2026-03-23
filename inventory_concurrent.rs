use std::sync::{Arc, Mutex};
use std::thread;

pub struct Inventory {
    stock: u32,
}

impl Inventory {
    pub fn new(initial_stock: u32) -> Self {
        Inventory { stock: initial_stock }
    }

    pub fn stock_level(&self) -> u32 {
        self.stock
    }

    pub fn try_decrement(&mut self, quantity: u32) -> Result<u32, ()> {
        if self.stock < quantity {
            return Err(());
        }
        self.stock -= quantity;
        Ok(self.stock)
    }
}

pub fn concurrent_inventory_updates<F>(initial_stock: u32, thread_count: usize, decrement_fn: F) -> u32
where
    F: Fn(usize) -> u32 + Send + Sync + 'static,
{
    let inventory = Arc::new(Mutex::new(Inventory::new(initial_stock)));
    let decrement_fn = Arc::new(decrement_fn);
    let mut handles = Vec::with_capacity(thread_count);

    for i in 0..thread_count {
        let inv = Arc::clone(&inventory);
        let decrement_fn = Arc::clone(&decrement_fn);
        handles.push(thread::spawn(move || {
            let qty = decrement_fn(i);
            let mut guard = inv.lock().unwrap();
            let _ = guard.try_decrement(qty);
        }));
    }

    for h in handles {
        h.join().unwrap();
    }

    inventory.lock().unwrap().stock_level()
}

fn main() {
    let remaining = concurrent_inventory_updates(500, 20, |i| 10 + (i as u32 % 5));
    println!("remaining stock: {}", remaining);
}
