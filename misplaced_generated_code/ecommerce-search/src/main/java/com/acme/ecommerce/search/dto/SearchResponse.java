package com.acme.ecommerce.search.dto;

import com.acme.ecommerce.search.model.Product;

import java.util.List;
import java.util.Map;

public class SearchResponse {

    private List<Product> products;
    private long totalHits;
    private int page;
    private int size;
    private int totalPages;
    private long responseTimeMs;
    private Map<String, List<FacetBucket>> facets;

    public List<Product> getProducts() { return products; }
    public void setProducts(List<Product> products) { this.products = products; }

    public long getTotalHits() { return totalHits; }
    public void setTotalHits(long totalHits) { this.totalHits = totalHits; }

    public int getPage() { return page; }
    public void setPage(int page) { this.page = page; }

    public int getSize() { return size; }
    public void setSize(int size) { this.size = size; }

    public int getTotalPages() { return totalPages; }
    public void setTotalPages(int totalPages) { this.totalPages = totalPages; }

    public long getResponseTimeMs() { return responseTimeMs; }
    public void setResponseTimeMs(long responseTimeMs) { this.responseTimeMs = responseTimeMs; }

    public Map<String, List<FacetBucket>> getFacets() { return facets; }
    public void setFacets(Map<String, List<FacetBucket>> facets) { this.facets = facets; }
}
