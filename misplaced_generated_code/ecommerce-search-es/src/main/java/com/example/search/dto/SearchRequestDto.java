package com.example.search.dto;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class SearchRequestDto {
  private String q;
  private List<String> categories = new ArrayList<>();
  private List<String> brands = new ArrayList<>();
  private List<String> tags = new ArrayList<>();
  private Double minPrice;
  private Double maxPrice;
  private Boolean inStock;
  private Map<String, Object> attributes;
  private List<String> facetAttributes = new ArrayList<>();
  private Integer page = 0;
  private Integer size = 10;

  public String getQ() {
    return q;
  }

  public void setQ(String q) {
    this.q = q;
  }

  public List<String> getCategories() {
    return categories;
  }

  public void setCategories(List<String> categories) {
    this.categories = categories == null ? new ArrayList<>() : categories;
  }

  public List<String> getBrands() {
    return brands;
  }

  public void setBrands(List<String> brands) {
    this.brands = brands == null ? new ArrayList<>() : brands;
  }

  public List<String> getTags() {
    return tags;
  }

  public void setTags(List<String> tags) {
    this.tags = tags == null ? new ArrayList<>() : tags;
  }

  public Double getMinPrice() {
    return minPrice;
  }

  public void setMinPrice(Double minPrice) {
    this.minPrice = minPrice;
  }

  public Double getMaxPrice() {
    return maxPrice;
  }

  public void setMaxPrice(Double maxPrice) {
    this.maxPrice = maxPrice;
  }

  public Boolean getInStock() {
    return inStock;
  }

  public void setInStock(Boolean inStock) {
    this.inStock = inStock;
  }

  public Map<String, Object> getAttributes() {
    return attributes;
  }

  public void setAttributes(Map<String, Object> attributes) {
    this.attributes = attributes;
  }

  public List<String> getFacetAttributes() {
    return facetAttributes;
  }

  public void setFacetAttributes(List<String> facetAttributes) {
    this.facetAttributes = facetAttributes == null ? new ArrayList<>() : facetAttributes;
  }

  public Integer getPage() {
    return page;
  }

  public void setPage(Integer page) {
    this.page = page == null ? 0 : Math.max(0, page);
  }

  public Integer getSize() {
    return size;
  }

  public void setSize(Integer size) {
    this.size = size == null ? 10 : Math.min(100, Math.max(1, size));
  }
}
