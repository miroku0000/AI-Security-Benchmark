package com.example.ecommerce.search.dto;

public class PriceRangeBucketDto {

    private String key;
    private long count;
    private Double from;
    private Double to;

    public PriceRangeBucketDto() {
    }

    public PriceRangeBucketDto(String key, long count, Double from, Double to) {
        this.key = key;
        this.count = count;
        this.from = from;
        this.to = to;
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

    public Double getFrom() {
        return from;
    }

    public void setFrom(Double from) {
        this.from = from;
    }

    public Double getTo() {
        return to;
    }

    public void setTo(Double to) {
        this.to = to;
    }
}
