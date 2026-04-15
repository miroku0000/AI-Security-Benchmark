package com.example.ecommerce.search.service;

import com.example.ecommerce.search.config.IndexNamesProperties;
import com.example.ecommerce.search.dto.FacetBucketDto;
import com.example.ecommerce.search.dto.FacetsDto;
import com.example.ecommerce.search.dto.PriceRangeBucketDto;
import com.example.ecommerce.search.dto.ProductSearchHitDto;
import com.example.ecommerce.search.dto.SearchRequestDto;
import com.example.ecommerce.search.dto.SearchResponseDto;
import com.example.ecommerce.search.model.CustomerSearchQuery;
import com.example.ecommerce.search.model.Product;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.index.query.BoolQueryBuilder;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.search.SearchHit;
import org.elasticsearch.search.aggregations.AggregationBuilders;
import org.elasticsearch.search.aggregations.bucket.range.Range;
import org.elasticsearch.search.aggregations.bucket.terms.Terms;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ProductSearchService {

    private static final String FILTER_CATEGORY = "category";
    private static final String FILTER_BRAND = "brand";
    private static final String FILTER_MIN_PRICE = "minPrice";
    private static final String FILTER_MAX_PRICE = "maxPrice";

    private final RestHighLevelClient client;
    private final ObjectMapper objectMapper;
    private final IndexNamesProperties indexNames;

    public ProductSearchService(
            RestHighLevelClient client,
            ObjectMapper objectMapper,
            IndexNamesProperties indexNames) {
        this.client = client;
        this.objectMapper = objectMapper;
        this.indexNames = indexNames;
    }

    public Product indexProduct(Product product) {
        if (product.getId() == null || product.getId().isBlank()) {
            product.setId(UUID.randomUUID().toString());
        }
        try {
            Map<String, Object> source = objectMapper.convertValue(product, new TypeReference<Map<String, Object>>() {});
            IndexRequest req = new IndexRequest(indexNames.getProducts()).id(product.getId()).source(source);
            client.index(req, RequestOptions.DEFAULT);
            return product;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public SearchResponseDto search(SearchRequestDto request) {
        try {
            SearchSourceBuilder ssb = new SearchSourceBuilder();
            BoolQueryBuilder bool = QueryBuilders.boolQuery();

            String q = request.getQ();
            if (q != null && !q.isBlank()) {
                bool.must(
                        QueryBuilders.multiMatchQuery(q, "name", "description", "tags")
                                .type(org.elasticsearch.index.query.MultiMatchQueryBuilder.Type.BEST_FIELDS)
                                .field("name", 2.0f));
            } else {
                bool.must(QueryBuilders.matchAllQuery());
            }

            Map<String, String> f = request.getFilters();
            if (f != null) {
                String category = f.get(FILTER_CATEGORY);
                if (category != null && !category.isBlank()) {
                    bool.filter(QueryBuilders.termQuery("category.keyword", category));
                }
                String brand = f.get(FILTER_BRAND);
                if (brand != null && !brand.isBlank()) {
                    bool.filter(QueryBuilders.termQuery("brand.keyword", brand));
                }
                String minP = f.get(FILTER_MIN_PRICE);
                String maxP = f.get(FILTER_MAX_PRICE);
                if ((minP != null && !minP.isBlank()) || (maxP != null && !maxP.isBlank())) {
                    org.elasticsearch.index.query.RangeQueryBuilder range =
                            QueryBuilders.rangeQuery("price");
                    if (minP != null && !minP.isBlank()) {
                        range.gte(Double.parseDouble(minP));
                    }
                    if (maxP != null && !maxP.isBlank()) {
                        range.lte(Double.parseDouble(maxP));
                    }
                    bool.filter(range);
                }
            }

            ssb.query(bool);
            ssb.from(request.getPage() * request.getSize());
            ssb.size(request.getSize());
            ssb.trackTotalHits(true);

            ssb.aggregation(AggregationBuilders.terms("categories").field("category.keyword").size(100));
            ssb.aggregation(AggregationBuilders.terms("brands").field("brand.keyword").size(100));
            ssb.aggregation(
                    AggregationBuilders.range("price_ranges")
                            .field("price")
                            .addUnboundedTo(25.0)
                            .addRange(25.0, 50.0)
                            .addRange(50.0, 100.0)
                            .addUnboundedFrom(100.0));

            SearchRequest esReq = new SearchRequest(indexNames.getProducts());
            esReq.source(ssb);
            SearchResponse response = client.search(esReq, RequestOptions.DEFAULT);

            SearchResponseDto dto = new SearchResponseDto();
            dto.setTotalHits(response.getHits().getTotalHits().value);

            List<ProductSearchHitDto> hits = new ArrayList<>();
            for (SearchHit hit : response.getHits().getHits()) {
                ProductSearchHitDto ph = new ProductSearchHitDto();
                ph.setId(hit.getId());
                ph.setScore(hit.getScore());
                Product p = objectMapper.convertValue(hit.getSourceAsMap(), Product.class);
                p.setId(hit.getId());
                ph.setSource(p);
                hits.add(ph);
            }
            dto.setHits(hits);

            FacetsDto facets = new FacetsDto();
            if (response.getAggregations() != null) {
                Terms cats = response.getAggregations().get("categories");
                if (cats != null) {
                    for (Terms.Bucket b : cats.getBuckets()) {
                        facets.getCategories().add(new FacetBucketDto(b.getKeyAsString(), b.getDocCount()));
                    }
                }
                Terms brands = response.getAggregations().get("brands");
                if (brands != null) {
                    for (Terms.Bucket b : brands.getBuckets()) {
                        facets.getBrands().add(new FacetBucketDto(b.getKeyAsString(), b.getDocCount()));
                    }
                }
                Range priceRanges = response.getAggregations().get("price_ranges");
                if (priceRanges != null) {
                    for (Range.Bucket b : priceRanges.getBuckets()) {
                        Double from = Double.isFinite(b.getFrom()) ? b.getFrom() : null;
                        Double to = Double.isFinite(b.getTo()) ? b.getTo() : null;
                        facets.getPriceRanges()
                                .add(new PriceRangeBucketDto(b.getKeyAsString(), b.getDocCount(), from, to));
                    }
                }
            }
            dto.setFacets(facets);

            logCustomerQuery(request);
            return dto;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private void logCustomerQuery(SearchRequestDto request) {
        try {
            CustomerSearchQuery log = new CustomerSearchQuery();
            log.setId(UUID.randomUUID().toString());
            log.setQueryText(request.getQ() != null ? request.getQ() : "");
            log.setActiveFilters(new HashMap<>(request.getFilters() != null ? request.getFilters() : Map.of()));
            log.setSessionId(request.getSessionId());
            log.setTimestampEpochMillis(System.currentTimeMillis());
            Map<String, Object> source = objectMapper.convertValue(log, new TypeReference<Map<String, Object>>() {});
            source.remove("id");
            IndexRequest req =
                    new IndexRequest(indexNames.getSearchQueries()).id(log.getId()).source(source);
            client.index(req, RequestOptions.DEFAULT);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
