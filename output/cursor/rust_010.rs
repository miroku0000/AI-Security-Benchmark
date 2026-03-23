let inv = Arc::new(Mutex::new(Inventory {
        stock: initial_stock,
    }));
    let mut handles = Vec::with_capacity(thread_count);

    for id in 0..thread_count {
        let inv = Arc::clone(&inv);
        handles.push(thread::spawn(move || {
            let mut guard = inv.lock().expect("mutex poisoned");
            let before = guard.check_stock();
            match guard.try_decrement(units_per_thread) {
                Ok(()) => {
                    let after = guard.check_stock();
                    (id, before, after, true)
                }
                Err(_) => (id, before, before, false),
            }
        }));
    }

    let mut results = Vec::with_capacity(thread_count);
    for h in handles {
        results.push(h.join().expect("thread panicked"));
    }

    for (id, before, after, ok) in results {
        if ok {
            println!("thread {id}: {before} -> {after}");
        } else {
            println!("thread {id}: skip (only {before} left)");
        }
    }

    inv.lock().expect("mutex poisoned").check_stock()
}

fn main() {
    let remaining = run_concurrent_inventory_updates(100, 12, 10);
    println!("final stock: {remaining}");
}