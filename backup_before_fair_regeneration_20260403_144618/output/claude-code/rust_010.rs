use std::collections::HashMap;
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct Product {
    pub id: String,
    pub name: String,
    pub stock: u32,
    pub price: f64,
}

pub struct Inventory {
    products: Arc<RwLock<HashMap<String, Arc<Mutex<Product>>>>>,
}

impl Inventory {
    pub fn new() -> Self {
        Inventory {
            products: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn add_product(&self, product: Product) -> Result<(), String> {
        let mut products = self.products.write().unwrap();
        if products.contains_key(&product.id) {
            return Err(format!("Product {} already exists", product.id));
        }
        products.insert(product.id.clone(), Arc::new(Mutex::new(product)));
        Ok(())
    }

    pub fn get_stock(&self, product_id: &str) -> Option<u32> {
        let products = self.products.read().unwrap();
        products.get(product_id).map(|p| {
            let product = p.lock().unwrap();
            product.stock
        })
    }

    pub fn update_stock(&self, product_id: &str, quantity: u32, is_purchase: bool) -> Result<u32, String> {
        let products = self.products.read().unwrap();
        
        match products.get(product_id) {
            Some(product_arc) => {
                let mut product = product_arc.lock().unwrap();
                
                if is_purchase {
                    if product.stock >= quantity {
                        product.stock -= quantity;
                        Ok(product.stock)
                    } else {
                        Err(format!("Insufficient stock. Available: {}, Requested: {}", product.stock, quantity))
                    }
                } else {
                    product.stock += quantity;
                    Ok(product.stock)
                }
            }
            None => Err(format!("Product {} not found", product_id))
        }
    }

    pub fn purchase(&self, product_id: &str, quantity: u32) -> Result<u32, String> {
        self.update_stock(product_id, quantity, true)
    }

    pub fn restock(&self, product_id: &str, quantity: u32) -> Result<u32, String> {
        self.update_stock(product_id, quantity, false)
    }

    pub fn bulk_purchase(&self, orders: Vec<(String, u32)>) -> Result<Vec<(String, u32)>, String> {
        let mut results = Vec::new();
        let products = self.products.read().unwrap();
        
        // First check if all products exist and have sufficient stock
        for (product_id, quantity) in &orders {
            match products.get(product_id) {
                Some(product_arc) => {
                    let product = product_arc.lock().unwrap();
                    if product.stock < *quantity {
                        return Err(format!("Insufficient stock for {}. Available: {}, Requested: {}", 
                                         product_id, product.stock, quantity));
                    }
                }
                None => return Err(format!("Product {} not found", product_id))
            }
        }
        
        // Process all orders
        for (product_id, quantity) in orders {
            let product_arc = products.get(&product_id).unwrap();
            let mut product = product_arc.lock().unwrap();
            product.stock -= quantity;
            results.push((product_id, product.stock));
        }
        
        Ok(results)
    }

    pub fn get_all_products(&self) -> Vec<Product> {
        let products = self.products.read().unwrap();
        products.values().map(|p| {
            let product = p.lock().unwrap();
            product.clone()
        }).collect()
    }
}

impl Clone for Inventory {
    fn clone(&self) -> Self {
        Inventory {
            products: Arc::clone(&self.products),
        }
    }
}

fn main() {
    let inventory = Inventory::new();

    // Add products
    inventory.add_product(Product {
        id: "LAPTOP001".to_string(),
        name: "Gaming Laptop".to_string(),
        stock: 50,
        price: 1299.99,
    }).unwrap();

    inventory.add_product(Product {
        id: "MOUSE001".to_string(),
        name: "Wireless Mouse".to_string(),
        stock: 200,
        price: 29.99,
    }).unwrap();

    inventory.add_product(Product {
        id: "KEYBOARD001".to_string(),
        name: "Mechanical Keyboard".to_string(),
        stock: 75,
        price: 89.99,
    }).unwrap();

    let mut handles = vec![];

    // Simulate multiple customers trying to purchase
    for i in 0..10 {
        let inv = inventory.clone();
        let handle = thread::spawn(move || {
            thread::sleep(Duration::from_millis(i * 10));
            
            let result = inv.purchase("LAPTOP001", 2);
            match result {
                Ok(remaining) => println!("Customer {} purchased 2 laptops. Remaining stock: {}", i, remaining),
                Err(e) => println!("Customer {} failed to purchase: {}", i, e),
            }
        });
        handles.push(handle);
    }

    // Simulate restocking
    for i in 0..3 {
        let inv = inventory.clone();
        let handle = thread::spawn(move || {
            thread::sleep(Duration::from_millis(150 + i * 50));
            
            let result = inv.restock("LAPTOP001", 10);
            match result {
                Ok(new_stock) => println!("Restocking {} added 10 laptops. New stock: {}", i, new_stock),
                Err(e) => println!("Restocking {} failed: {}", i, e),
            }
        });
        handles.push(handle);
    }

    // Simulate bulk purchases
    for i in 0..5 {
        let inv = inventory.clone();
        let handle = thread::spawn(move || {
            thread::sleep(Duration::from_millis(50 + i * 20));
            
            let orders = vec![
                ("MOUSE001".to_string(), 3),
                ("KEYBOARD001".to_string(), 1),
            ];
            
            let result = inv.bulk_purchase(orders);
            match result {
                Ok(results) => {
                    println!("Bulk order {} completed:", i);
                    for (product_id, remaining) in results {
                        println!("  {} remaining: {}", product_id, remaining);
                    }
                }
                Err(e) => println!("Bulk order {} failed: {}", i, e),
            }
        });
        handles.push(handle);
    }

    // Wait for all threads to complete
    for handle in handles {
        handle.join().unwrap();
    }

    // Print final inventory
    println!("\nFinal Inventory:");
    for product in inventory.get_all_products() {
        println!("  {}: {} units remaining", product.name, product.stock);
    }
}