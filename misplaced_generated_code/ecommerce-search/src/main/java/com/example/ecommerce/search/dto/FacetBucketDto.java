package com.example.ecommerce.search.dto;

public class FacetBucketDto {

    private String key;
    private long count;

    public FacetBucketDto() {
    }

    public FacetBucketDto(String key, long count) {
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
