fn decrement_stock(&self, item: &str, quantity: u32) -> Result<u32, String> {
        let mut stock = self.stock.lock().unwrap();
        match stock.get_mut(item) {
            Some(current) if *current >= quantity => {
                *current -= quantity;
                Ok(*current)
            }
            Some(current) => Err(format!(
                "Insufficient stock for '{}': requested {}, available {}",
                item, quantity, *current
            )),
            None => Err(format!("Item '{}' not found", item)),
        }
    }
}