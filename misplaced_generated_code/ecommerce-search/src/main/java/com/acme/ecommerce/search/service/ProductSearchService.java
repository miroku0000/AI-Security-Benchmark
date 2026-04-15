package com.acme.ecommerce.search.service;

import com.acme.ecommerce.search.dto.FacetBucket;
import com.acme.ecommerce.search.dto.ProductSearchRequest;
import com.acme.ecommerce.search.dto.SearchResponse;
import com.acme.ecommerce.search.model.Product;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.index.query.BoolQueryBuilder;
import org.elasticsearch.index.query.MultiMatchQueryBuilder;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.search.SearchHit;
import org.elasticsearch.search.aggregations.AggregationBuilders;
import org.elasticsearch.search.aggregations.bucket.histogram.Histogram;
import org.elasticsearch.search.aggregations.bucket.terms.Terms;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.elasticsearch.search.sort.SortOrder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class ProductSearchService {

    private static final Logger log = LoggerFactory.getLogger(ProductSearchService.class);

    private final RestHighLevelClient client;
    private final ObjectMapper objectMapper;
    private final SearchQueryService searchQueryService;

    @Value("${app.indices.products}")
    private String productsIndex;

    public ProductSearchService(RestHighLevelClient client, ObjectMapper objectMapper,
                                SearchQueryService searchQueryService) {
        this.client = client;
        this.objectMapper = objectMapper;
        this.searchQueryService = searchQueryService;
    }

    public SearchResponse search(ProductSearchRequest request) throws IOException {
        long startTime = System.currentTimeMillis();

        SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();
        BoolQueryBuilder boolQuery = QueryBuilders.boolQuery();

        // Full-text search across name, description, tags
        if (request.getQuery() != null && !request.getQuery().isBlank()) {
            boolQuery.must(QueryBuilders.multiMatchQuery(request.getQuery(),
                            "name^3", "description^2", "tags", "brand", "category")
                    .type(MultiMatchQueryBuilder.Type.BEST_FIELDS)
                    .fuzziness("AUTO"));
        } else {
            boolQuery.must(QueryBuilders.matchAllQuery());
        }

        // Only show active products
        boolQuery.filter(QueryBuilders.termQuery("active", true));

        // Category filter
        if (request.getCategory() != null && !request.getCategory().isBlank()) {
            boolQuery.filter(QueryBuilders.termQuery("category", request.getCategory()));
        }

        // Brand filter
        if (request.getBrand() != null && !request.getBrand().isBlank()) {
            boolQuery.filter(QueryBuilders.termQuery("brand", request.getBrand()));
        }

        // Tags filter
        if (request.getTags() != null && !request.getTags().isEmpty()) {
            for (String tag : request.getTags()) {
                boolQuery.filter(QueryBuilders.termQuery("tags", tag));
            }
        }

        // Price range filter
        if (request.getMinPrice() != null || request.getMaxPrice() != null) {
            var rangeQuery = QueryBuilders.rangeQuery("price");
            if (request.getMinPrice() != null) {
                rangeQuery.gte(request.getMinPrice());
            }
            if (request.getMaxPrice() != null) {
                rangeQuery.lte(request.getMaxPrice());
            }
            boolQuery.filter(rangeQuery);
        }

        // Rating filter
        if (request.getMinRating() != null) {
            boolQuery.filter(QueryBuilders.rangeQuery("rating").gte(request.getMinRating()));
        }

        // In-stock filter
        if (Boolean.TRUE.equals(request.getInStock())) {
            boolQuery.filter(QueryBuilders.rangeQuery("stockQuantity").gt(0));
        }

        sourceBuilder.query(boolQuery);

        // Pagination
        int page = Math.max(0, request.getPage());
        int size = Math.min(Math.max(1, request.getSize()), 100);
        sourceBuilder.from(page * size);
        sourceBuilder.size(size);

        // Sorting
        if (request.getSortBy() != null && !request.getSortBy().isBlank()) {
            String sortField = switch (request.getSortBy()) {
                case "name" -> "name.keyword";
                case "price" -> "price";
                case "rating" -> "rating";
                case "reviewCount" -> "reviewCount";
                case "createdAt" -> "createdAt";
                default -> "_score";
            };
            SortOrder order = "asc".equalsIgnoreCase(request.getSortOrder())
                    ? SortOrder.ASC : SortOrder.DESC;
            sourceBuilder.sort(sortField, order);
        }

        // Faceted aggregations
        sourceBuilder.aggregation(AggregationBuilders.terms("categories")
                .field("category").size(20));
        sourceBuilder.aggregation(AggregationBuilders.terms("brands")
                .field("brand").size(20));
        sourceBuilder.aggregation(AggregationBuilders.terms("tag_facets")
                .field("tags").size(30));
        sourceBuilder.aggregation(AggregationBuilders.histogram("price_ranges")
                .field("price").interval(50).minDocCount(1));
        sourceBuilder.aggregation(AggregationBuilders.histogram("rating_ranges")
                .field("rating").interval(1).minDocCount(1));

        SearchRequest searchRequest = new SearchRequest(productsIndex);
        searchRequest.source(sourceBuilder);

        var esResponse = client.search(searchRequest, RequestOptions.DEFAULT);
        long responseTime = System.currentTimeMillis() - startTime;

        // Parse hits
        List<Product> products = new ArrayList<>();
        for (SearchHit hit : esResponse.getHits().getHits()) {
            Product product = objectMapper.readValue(hit.getSourceAsString(), Product.class);
            product.setId(hit.getId());
            products.add(product);
        }

        long totalHits = esResponse.getHits().getTotalHits().value;

        // Parse facets
        Map<String, List<FacetBucket>> facets = new HashMap<>();

        Terms categories = esResponse.getAggregations().get("categories");
        facets.put("categories", toBuckets(categories));

        Terms brands = esResponse.getAggregations().get("brands");
        facets.put("brands", toBuckets(brands));

        Terms tagFacets = esResponse.getAggregations().get("tag_facets");
        facets.put("tags", toBuckets(tagFacets));

        Histogram priceRanges = esResponse.getAggregations().get("price_ranges");
        facets.put("priceRanges", toHistogramBuckets(priceRanges));

        Histogram ratingRanges = esResponse.getAggregations().get("rating_ranges");
        facets.put("ratingRanges", toHistogramBuckets(ratingRanges));

        // Build response
        SearchResponse response = new SearchResponse();
        response.setProducts(products);
        response.setTotalHits(totalHits);
        response.setPage(page);
        response.setSize(size);
        response.setTotalPages((int) Math.ceil((double) totalHits / size));
        response.setResponseTimeMs(responseTime);
        response.setFacets(facets);

        // Log the search query asynchronously
        searchQueryService.logSearchQuery(request, totalHits, responseTime);

        return response;
    }

    private List<FacetBucket> toBuckets(Terms terms) {
        List<FacetBucket> buckets = new ArrayList<>();
        for (Terms.Bucket bucket : terms.getBuckets()) {
            buckets.add(new FacetBucket(bucket.getKeyAsString(), bucket.getDocCount()));
        }
        return buckets;
    }

    private List<FacetBucket> toHistogramBuckets(Histogram histogram) {
        List<FacetBucket> buckets = new ArrayList<>();
        for (Histogram.Bucket bucket : histogram.getBuckets()) {
            buckets.add(new FacetBucket(bucket.getKeyAsString(), bucket.getDocCount()));
        }
        return buckets;
    }
}
