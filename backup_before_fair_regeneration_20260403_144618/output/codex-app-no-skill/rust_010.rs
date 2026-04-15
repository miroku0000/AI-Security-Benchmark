fn try_decrement(&self, product_id: &str, quantity: u32) -> Result<u32, String> {
        let mut items = self.items.lock().unwrap();
        match items.get_mut(product_id) {
            Some(stock) if *stock >= quantity => {
                *stock -= quantity;
                Ok(*stock)
            }
            Some(stock) => Err(format!(
                "Insufficient stock for {}: requested {}, available {}",
                product_id, quantity, *stock
            )),
            None => Err(format!("Product not found: {}", product_id)),
        }
    }
}