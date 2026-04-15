package com.example.ecommerce.search.dto;

import com.example.ecommerce.search.model.Product;

public class ProductSearchHitDto {

    private String id;
    private double score;
    private Product source;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public double getScore() {
        return score;
    }

    public void setScore(double score) {
        this.score = score;
    }

    public Product getSource() {
        return source;
    }

    public void setSource(Product source) {
        this.source = source;
    }
}
