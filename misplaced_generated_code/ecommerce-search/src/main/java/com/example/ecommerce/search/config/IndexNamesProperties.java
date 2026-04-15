package com.example.ecommerce.search.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "indices")
public class IndexNamesProperties {

    private String products = "products";
    private String searchQueries = "customer-search-queries";

    public String getProducts() {
        return products;
    }

    public void setProducts(String products) {
        this.products = products;
    }

    public String getSearchQueries() {
        return searchQueries;
    }

    public void setSearchQueries(String searchQueries) {
        this.searchQueries = searchQueries;
    }
}
