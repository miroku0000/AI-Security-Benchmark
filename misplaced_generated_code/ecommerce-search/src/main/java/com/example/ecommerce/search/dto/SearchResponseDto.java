package com.example.ecommerce.search.dto;

import java.util.ArrayList;
import java.util.List;

public class SearchResponseDto {

    private long totalHits;
    private List<ProductSearchHitDto> hits = new ArrayList<>();
    private FacetsDto facets = new FacetsDto();

    public long getTotalHits() {
        return totalHits;
    }

    public void setTotalHits(long totalHits) {
        this.totalHits = totalHits;
    }

    public List<ProductSearchHitDto> getHits() {
        return hits;
    }

    public void setHits(List<ProductSearchHitDto> hits) {
        this.hits = hits;
    }

    public FacetsDto getFacets() {
        return facets;
    }

    public void setFacets(FacetsDto facets) {
        this.facets = facets;
    }
}
