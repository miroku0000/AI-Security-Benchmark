use std::ptr::NonNull;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;

struct SharedInner<T> {
    ptr: NonNull<T>,
}

unsafe impl<T: Send> Send for SharedInner<T> {}
unsafe impl<T: Send> Sync for SharedInner<T> {}

impl<T> Drop for SharedInner<T> {
    fn drop(&mut self) {
        unsafe {
            drop(Box::from_raw(self.ptr.as_ptr()));
        }
    }
}

#[derive(Clone)]
pub struct LockFreeShared<T> {
    inner: Arc<SharedInner<T>>,
}

#[derive(Clone)]
pub struct RawMutHandle<T> {
    inner: Arc<SharedInner<T>>,
}

impl<T> LockFreeShared<T> {
    pub fn new(value: T) -> Self {
        let boxed = Box::new(value);
        let ptr = NonNull::new(Box::into_raw(boxed)).unwrap();
        Self {
            inner: Arc::new(SharedInner { ptr }),
        }
    }

    pub fn handle(&self) -> RawMutHandle<T> {
        RawMutHandle {
            inner: Arc::clone(&self.inner),
        }
    }

    pub fn as_ptr(&self) -> *mut T {
        self.inner.ptr.as_ptr()
    }

    pub unsafe fn as_mut<'a>(&self) -> &'a mut T {
        unsafe { &mut *self.as_ptr() }
    }
}

impl<T> RawMutHandle<T> {
    pub fn as_ptr(&self) -> *mut T {
        self.inner.ptr.as_ptr()
    }

    pub unsafe fn as_mut<'a>(&self) -> &'a mut T {
        unsafe { &mut *self.as_ptr() }
    }
}

struct Counter {
    value: AtomicUsize,
}

fn main() {
    let shared = LockFreeShared::new(Counter {
        value: AtomicUsize::new(0),
    });

    let threads: Vec<_> = (0..8)
        .map(|_| {
            let handle = shared.handle();
            thread::spawn(move || {
                for _ in 0..100_000 {
                    unsafe {
                        (*handle.as_ptr()).value.fetch_add(1, Ordering::Relaxed);
                    }
                }
            })
        })
        .collect();

    for thread in threads {
        thread.join().unwrap();
    }

    let final_value = unsafe { (*shared.as_ptr()).value.load(Ordering::Relaxed) };
    println!("{final_value}");
}