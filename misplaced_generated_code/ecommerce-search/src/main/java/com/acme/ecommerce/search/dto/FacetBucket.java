package com.acme.ecommerce.search.dto;

public class FacetBucket {

    private String key;
    private long docCount;

    public FacetBucket() {}

    public FacetBucket(String key, long docCount) {
        this.key = key;
        this.docCount = docCount;
    }

    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }

    public long getDocCount() { return docCount; }
    public void setDocCount(long docCount) { this.docCount = docCount; }
}
