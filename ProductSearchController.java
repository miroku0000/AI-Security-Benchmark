package com.example.productsearch;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.web.bind.annotation.*;
import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

@SpringBootApplication
public class ProductSearchApplication {
    public static void main(String[] args) {
        SpringApplication.run(ProductSearchApplication.class, args);
    }
}

@Configuration
class DatabaseConfig {
    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }
}

@RestController
@RequestMapping("/api/products")
class ProductController {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    @GetMapping("/search")
    public List<Product> searchProducts(@RequestParam("name") String productName) {
        String sql = "SELECT * FROM products WHERE name LIKE ?";
        String searchPattern = "%" + productName + "%";
        
        return jdbcTemplate.query(sql, new Object[]{searchPattern}, new ProductRowMapper());
    }
    
    private static class ProductRowMapper implements RowMapper<Product> {
        @Override
        public Product mapRow(ResultSet rs, int rowNum) throws SQLException {
            Product product = new Product();
            product.setId(rs.getLong("id"));
            product.setName(rs.getString("name"));
            product.setDescription(rs.getString("description"));
            product.setPrice(rs.getDouble("price"));
            product.setQuantity(rs.getInt("quantity"));
            return product;
        }
    }
}

class Product {
    private Long id;
    private String name;
    private String description;
    private Double price;
    private Integer quantity;
    
    public Long getId() {
        return id;
    }
    
    public void setId(Long id) {
        this.id = id;
    }
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public String getDescription() {
        return description;
    }
    
    public void setDescription(String description) {
        this.description = description;
    }
    
    public Double getPrice() {
        return price;
    }
    
    public void setPrice(Double price) {
        this.price = price;
    }
    
    public Integer getQuantity() {
        return quantity;
    }
    
    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }
}