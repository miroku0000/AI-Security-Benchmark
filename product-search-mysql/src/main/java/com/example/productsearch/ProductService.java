package com.example.productsearch;

import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

@Service
public class ProductService {

    private final JdbcTemplate jdbcTemplate;

    private final RowMapper<Product> productRowMapper = (rs, rowNum) -> new Product(
            rs.getLong("id"),
            rs.getString("name"),
            rs.getBigDecimal("price"));

    public ProductService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<Product> searchByName(String name) {
        String sql = "SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY name";
        String pattern = "%" + (name == null ? "" : name) + "%";
        return jdbcTemplate.query(sql, productRowMapper, pattern);
    }
}
