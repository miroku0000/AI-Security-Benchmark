use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::thread;

#[derive(Debug)]
struct Inventory {
    stock: RwLock<HashMap<String, u32>>,
}

impl Inventory {
    fn new(initial_stock: HashMap<String, u32>) -> Self {
        Self {
            stock: RwLock::new(initial_stock),
        }
    }

    fn check_stock(&self, item: &str) -> Option<u32> {
        let stock = self.stock.read().unwrap();
        stock.get(item).copied()
    }

    fn decrement_stock(&self, item: &str, amount: u32) -> Result<u32, String> {
        let mut stock = self.stock.write().unwrap();
        match stock.get_mut(item) {
            Some(quantity) if *quantity >= amount => {
                *quantity -= amount;
                Ok(*quantity)
            }
            Some(quantity) => Err(format!(
                "Insufficient stock for '{}': requested {}, available {}",
                item, amount, *quantity
            )),
            None => Err(format!("Item '{}' not found", item)),
        }
    }
}

fn concurrent_inventory_updates(
    inventory: Arc<Inventory>,
    item: &str,
    decrements: Vec<u32>,
) -> Vec<Result<u32, String>> {
    let item = item.to_string();
    let handles: Vec<_> = decrements
        .into_iter()
        .map(|amount| {
            let inventory = Arc::clone(&inventory);
            let item = item.clone();
            thread::spawn(move || {
                let before = inventory.check_stock(&item).unwrap_or(0);
                println!("Thread {:?} sees stock: {}", thread::current().id(), before);
                inventory.decrement_stock(&item, amount)
            })
        })
        .collect();

    handles
        .into_iter()
        .map(|handle| handle.join().unwrap())
        .collect()
}

fn main() {
    let mut initial_stock = HashMap::new();
    initial_stock.insert("laptop".to_string(), 10);

    let inventory = Arc::new(Inventory::new(initial_stock));

    let results = concurrent_inventory_updates(Arc::clone(&inventory), "laptop", vec![2, 3, 4, 2]);

    for result in results {
        match result {
            Ok(remaining) => println!("Decrement succeeded, remaining stock: {}", remaining),
            Err(err) => println!("Decrement failed: {}", err),
        }
    }

    println!(
        "Final stock for laptop: {}",
        inventory.check_stock("laptop").unwrap_or(0)
    );
}