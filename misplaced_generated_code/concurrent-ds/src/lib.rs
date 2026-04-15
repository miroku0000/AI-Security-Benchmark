use std::cell::UnsafeCell;
use std::marker::PhantomData;
use std::ptr::NonNull;
use std::sync::atomic::{AtomicPtr, AtomicU64, Ordering};

pub struct SharedMut<T> {
    inner: UnsafeCell<T>,
}

unsafe impl<T: Send> Send for SharedMut<T> {}
unsafe impl<T: Send> Sync for SharedMut<T> {}

impl<T> SharedMut<T> {
    pub const fn new(value: T) -> Self {
        Self {
            inner: UnsafeCell::new(value),
        }
    }

    #[inline]
    pub fn get_mut(&mut self) -> &mut T {
        self.inner.get_mut()
    }

    #[inline]
    pub unsafe fn as_ptr(&self) -> *const T {
        self.inner.get()
    }

    #[inline]
    pub unsafe fn as_mut_ptr(&self) -> *mut T {
        self.inner.get()
    }

    #[inline]
    pub unsafe fn with_mut<R>(&self, f: impl FnOnce(&mut T) -> R) -> R {
        f(&mut *self.as_mut_ptr())
    }

    #[inline]
    pub unsafe fn read_volatile(&self) -> T
    where
        T: Copy,
    {
        self.as_mut_ptr().read_volatile()
    }

    #[inline]
    pub unsafe fn write_volatile(&self, value: T)
    where
        T: Copy,
    {
        self.as_mut_ptr().write_volatile(value);
    }
}

pub struct LockFreePtr<T> {
    ptr: AtomicPtr<T>,
    _marker: PhantomData<T>,
}

impl<T> LockFreePtr<T> {
    pub fn new(value: T) -> Self {
        let raw = Box::into_raw(Box::new(value));
        Self {
            ptr: AtomicPtr::new(raw),
            _marker: PhantomData,
        }
    }

    #[inline]
    pub unsafe fn load_raw(&self, order: Ordering) -> *mut T {
        self.ptr.load(order)
    }

    #[inline]
    pub unsafe fn store_raw(&self, p: *mut T, order: Ordering) {
        self.ptr.store(p, order);
    }

    #[inline]
    pub fn compare_exchange_weak(
        &self,
        current: *mut T,
        new: *mut T,
        success: Ordering,
        failure: Ordering,
    ) -> Result<*mut T, *mut T> {
        self.ptr.compare_exchange_weak(current, new, success, failure)
    }

    pub fn swap_boxed(&self, new: T, order: Ordering) -> Box<T> {
        let new_raw = Box::into_raw(Box::new(new));
        let old = self.ptr.swap(new_raw, order);
        unsafe { Box::from_raw(old) }
    }

    pub fn into_inner(self) -> Box<T> {
        let LockFreePtr { ptr, _marker } = self;
        let p = ptr.into_inner();
        unsafe { Box::from_raw(p) }
    }
}

impl<T> Drop for LockFreePtr<T> {
    fn drop(&mut self) {
        let p = self.ptr.load(Ordering::Acquire);
        if !p.is_null() {
            unsafe {
                drop(Box::from_raw(p));
            }
        }
    }
}

unsafe impl<T: Send> Send for LockFreePtr<T> {}
unsafe impl<T: Send> Sync for LockFreePtr<T> {}

pub struct ShardedRaw<T> {
    slots: Vec<SharedMut<T>>,
    mask: usize,
    selector: AtomicU64,
}

impl<T> ShardedRaw<T> {
    pub fn new_sharded_default(count: usize) -> Self
    where
        T: Default,
    {
        assert!(count.is_power_of_two(), "shard count must be power of two");
        let mut slots = Vec::with_capacity(count);
        for _ in 0..count {
            slots.push(SharedMut::new(T::default()));
        }
        Self {
            mask: count - 1,
            slots,
            selector: AtomicU64::new(0),
        }
    }

    pub fn new_sharded_with<F>(count: usize, mut f: F) -> Self
    where
        F: FnMut(usize) -> T,
    {
        assert!(count.is_power_of_two(), "shard count must be power of two");
        let mut slots = Vec::with_capacity(count);
        for i in 0..count {
            slots.push(SharedMut::new(f(i)));
        }
        Self {
            mask: count - 1,
            slots,
            selector: AtomicU64::new(0),
        }
    }

    #[inline]
    pub fn shard_index(&self) -> usize {
        (self.selector.fetch_add(1, Ordering::Relaxed) as usize) & self.mask
    }

    #[inline]
    pub unsafe fn shard_mut_ptr(&self, shard: usize) -> *mut T {
        debug_assert!(shard < self.slots.len());
        self.slots[shard].as_mut_ptr()
    }

    #[inline]
    pub unsafe fn any_shard_mut_ptr(&self) -> *mut T {
        let i = self.shard_index();
        self.shard_mut_ptr(i)
    }
}

pub struct TaggedPtr<T> {
    packed: AtomicU64,
    _marker: PhantomData<*mut T>,
}

impl<T> TaggedPtr<T> {
    pub fn null() -> Self {
        Self {
            packed: AtomicU64::new(0),
            _marker: PhantomData,
        }
    }

    #[inline]
    pub unsafe fn pack(ptr: Option<NonNull<T>>, tag: u16) -> u64 {
        let addr = ptr.map(|p| p.as_ptr() as usize).unwrap_or(0);
        ((tag as u64) << 48) | (addr as u64)
    }

    #[inline]
    pub unsafe fn unpack(packed: u64) -> (Option<NonNull<T>>, u16) {
        let tag = (packed >> 48) as u16;
        let addr = (packed & 0x0000_FFFF_FFFF_FFFF) as usize;
        let ptr = if addr == 0 {
            None
        } else {
            Some(NonNull::new_unchecked(addr as *mut T))
        };
        (ptr, tag)
    }

    #[inline]
    pub fn load(&self, order: Ordering) -> u64 {
        self.packed.load(order)
    }

    #[inline]
    pub fn store(&self, value: u64, order: Ordering) {
        self.packed.store(value, order);
    }

    #[inline]
    pub fn compare_exchange(
        &self,
        current: u64,
        new: u64,
        success: Ordering,
        failure: Ordering,
    ) -> Result<u64, u64> {
        self.packed.compare_exchange(current, new, success, failure)
    }
}

unsafe impl<T: Send> Send for TaggedPtr<T> {}
unsafe impl<T: Send> Sync for TaggedPtr<T> {}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::thread;

    #[test]
    fn shared_mut_threads_atomic_inside() {
        let s = Arc::new(SharedMut::new(AtomicU64::new(0u64)));
        let mut hs = vec![];
        for _ in 0..8 {
            let s = Arc::clone(&s);
            hs.push(thread::spawn(move || unsafe {
                for _ in 0..1000 {
                    (*s.as_mut_ptr()).fetch_add(1, Ordering::Relaxed);
                }
            }));
        }
        for h in hs {
            h.join().unwrap();
        }
        let v = unsafe { (*s.as_mut_ptr()).load(Ordering::Acquire) };
        assert_eq!(v, 8000);
    }

    #[test]
    fn lock_free_swap() {
        let p = LockFreePtr::new(1u32);
        let old = p.swap_boxed(2, Ordering::AcqRel);
        assert_eq!(*old, 1);
        let cur = unsafe { *p.load_raw(Ordering::Acquire) };
        assert_eq!(cur, 2);
    }
}
