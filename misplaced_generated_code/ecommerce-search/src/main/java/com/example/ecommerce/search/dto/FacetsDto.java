package com.example.ecommerce.search.dto;

import java.util.ArrayList;
import java.util.List;

public class FacetsDto {

    private List<FacetBucketDto> categories = new ArrayList<>();
    private List<FacetBucketDto> brands = new ArrayList<>();
    private List<PriceRangeBucketDto> priceRanges = new ArrayList<>();

    public List<FacetBucketDto> getCategories() {
        return categories;
    }

    public void setCategories(List<FacetBucketDto> categories) {
        this.categories = categories;
    }

    public List<FacetBucketDto> getBrands() {
        return brands;
    }

    public void setBrands(List<FacetBucketDto> brands) {
        this.brands = brands;
    }

    public List<PriceRangeBucketDto> getPriceRanges() {
        return priceRanges;
    }

    public void setPriceRanges(List<PriceRangeBucketDto> priceRanges) {
        this.priceRanges = priceRanges;
    }
}
