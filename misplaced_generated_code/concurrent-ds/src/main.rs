use concurrent_ds::{LockFreePtr, SharedMut, ShardedRaw};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;

fn main() {
    let cell = Arc::new(SharedMut::new(AtomicU64::new(0)));
    let mut handles = vec![];
    for _ in 0..4 {
        let c = Arc::clone(&cell);
        handles.push(thread::spawn(move || unsafe {
            for _ in 0..1000 {
                (*c.as_mut_ptr()).fetch_add(1, Ordering::Relaxed);
            }
        }));
    }
    for h in handles {
        h.join().unwrap();
    }
    let total = unsafe { (*cell.as_mut_ptr()).load(Ordering::Acquire) };
    println!("{total}");

    let p = LockFreePtr::new(42u32);
    let prev = p.swap_boxed(7, Ordering::AcqRel);
    println!("{} {}", *prev, unsafe { *p.load_raw(Ordering::Acquire) });

    let shards: ShardedRaw<AtomicU64> = ShardedRaw::new_sharded_default(4);
    unsafe {
        let q = shards.any_shard_mut_ptr();
        (*q).fetch_add(1, Ordering::Relaxed);
    }
}
