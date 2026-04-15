package com.example.search.dto;

import com.example.search.model.Product;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class SearchResponseDto {
  private long total;
  private int page;
  private int size;
  private List<Product> items = new ArrayList<>();
  private Map<String, List<Bucket>> facets = new HashMap<>();
  private Map<String, Object> metrics = new HashMap<>();

  public static class Bucket {
    private String key;
    private long count;

    public Bucket() {}

    public Bucket(String key, long count) {
      this.key = key;
      this.count = count;
    }

    public String getKey() {
      return key;
    }

    public void setKey(String key) {
      this.key = key;
    }

    public long getCount() {
      return count;
    }

    public void setCount(long count) {
      this.count = count;
    }
  }

  public long getTotal() {
    return total;
  }

  public void setTotal(long total) {
    this.total = total;
  }

  public int getPage() {
    return page;
  }

  public void setPage(int page) {
    this.page = page;
  }

  public int getSize() {
    return size;
  }

  public void setSize(int size) {
    this.size = size;
  }

  public List<Product> getItems() {
    return items;
  }

  public void setItems(List<Product> items) {
    this.items = items == null ? new ArrayList<>() : items;
  }

  public Map<String, List<Bucket>> getFacets() {
    return facets;
  }

  public void setFacets(Map<String, List<Bucket>> facets) {
    this.facets = facets == null ? new HashMap<>() : facets;
  }

  public Map<String, Object> getMetrics() {
    return metrics;
  }

  public void setMetrics(Map<String, Object> metrics) {
    this.metrics = metrics == null ? new HashMap<>() : metrics;
  }
}
