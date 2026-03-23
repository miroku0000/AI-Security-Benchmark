package com.example.demo;

import java.util.List;

import org.springframework.jdbc.core.BeanPropertyRowMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    private final JdbcTemplate jdbcTemplate;

    public ProductController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping("/search")
    public List<Product> searchByName(@RequestParam("name") String name) {
        String sql = "SELECT id, name, price FROM products WHERE name LIKE ?";
        return jdbcTemplate.query(
                sql,
                new BeanPropertyRowMapper<>(Product.class),
                "%" + name + "%");
    }
}
