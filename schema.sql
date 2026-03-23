CREATE TABLE IF NOT EXISTS products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    quantity INT
);

INSERT INTO products (name, description, price, quantity) VALUES
('Laptop', 'High-performance laptop', 999.99, 50),
('Mouse', 'Wireless mouse', 29.99, 200),
('Keyboard', 'Mechanical keyboard', 79.99, 150),
('Monitor', '27-inch LED monitor', 299.99, 75),
('Headphones', 'Noise-canceling headphones', 199.99, 100);