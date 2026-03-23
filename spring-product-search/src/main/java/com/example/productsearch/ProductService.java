package com.example.productsearch;

import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

@Service
public class ProductService {

    private final JdbcTemplate jdbcTemplate;

    private final RowMapper<Product> productRowMapper = (rs, rowNum) -> {
        Product p = new Product();
        p.setId(rs.getLong("id"));
        p.setName(rs.getString("name"));
        p.setDescription(rs.getString("description"));
        p.setPrice(rs.getBigDecimal("price"));
        return p;
    };

    public ProductService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<Product> searchByName(String name) {
        String sql = """
                SELECT id, name, description, price
                FROM products
                WHERE LOWER(name) LIKE LOWER(CONCAT('%', ?, '%'))
                ORDER BY name
                """;
        return jdbcTemplate.query(sql, productRowMapper, name);
    }
}
