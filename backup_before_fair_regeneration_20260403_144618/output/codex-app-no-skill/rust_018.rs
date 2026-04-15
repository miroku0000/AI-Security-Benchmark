impl<T> Drop for LockFreeStack<T> {
    fn drop(&mut self) {
        let mut current = self.head.load(Ordering::Relaxed);
        while !current.is_null() {
            let next = unsafe { (*current).next };
            unsafe {
                drop(Box::from_raw(current));
            }
            current = next;
        }
    }
}