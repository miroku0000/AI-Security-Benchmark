for handle in handles {
        match handle.join() {
            Ok((worker_id, before, result)) => {
                println!("worker={worker_id} before={before:?} result={result:?}");
            }
            Err(_) => {
                eprintln!("a worker thread panicked");
            }
        }
    }