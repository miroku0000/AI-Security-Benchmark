package com.acme.ecommerce.search.service;

import com.acme.ecommerce.search.dto.ProductSearchRequest;
import com.acme.ecommerce.search.model.SearchQuery;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.indices.CreateIndexRequest;
import org.elasticsearch.client.indices.GetIndexRequest;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.search.aggregations.AggregationBuilders;
import org.elasticsearch.search.aggregations.bucket.terms.Terms;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.elasticsearch.xcontent.XContentType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class SearchQueryService {

    private static final Logger log = LoggerFactory.getLogger(SearchQueryService.class);

    private final RestHighLevelClient client;
    private final ObjectMapper objectMapper;

    @Value("${app.indices.searchQueries}")
    private String searchQueriesIndex;

    public SearchQueryService(RestHighLevelClient client, ObjectMapper objectMapper) {
        this.client = client;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void initIndex() throws IOException {
        boolean exists = client.indices().exists(
                new GetIndexRequest(searchQueriesIndex), RequestOptions.DEFAULT);
        if (!exists) {
            CreateIndexRequest request = new CreateIndexRequest(searchQueriesIndex);
            request.settings(Settings.builder()
                    .put("number_of_shards", 1)
                    .put("number_of_replicas", 1));
            request.mapping(Map.of(
                    "properties", Map.of(
                            "queryText", Map.of("type", "text",
                                    "fields", Map.of("keyword", Map.of("type", "keyword"))),
                            "customerId", Map.of("type", "keyword"),
                            "sessionId", Map.of("type", "keyword"),
                            "appliedFilters", Map.of("type", "object", "enabled", true),
                            "totalResults", Map.of("type", "integer"),
                            "page", Map.of("type", "integer"),
                            "pageSize", Map.of("type", "integer"),
                            "responseTimeMs", Map.of("type", "long"),
                            "timestamp", Map.of("type", "date")
                    )
            ), XContentType.JSON);
            client.indices().create(request, RequestOptions.DEFAULT);
            log.info("Created index: {}", searchQueriesIndex);
        }
    }

    public void logSearchQuery(ProductSearchRequest request, long totalResults, long responseTimeMs) {
        try {
            SearchQuery searchQuery = new SearchQuery();
            searchQuery.setId(UUID.randomUUID().toString());
            searchQuery.setQueryText(request.getQuery());
            searchQuery.setCustomerId(request.getCustomerId());
            searchQuery.setSessionId(request.getSessionId());
            searchQuery.setTotalResults((int) totalResults);
            searchQuery.setPage(request.getPage());
            searchQuery.setPageSize(request.getSize());
            searchQuery.setResponseTimeMs(responseTimeMs);
            searchQuery.setTimestamp(Instant.now());

            Map<String, String> filters = new HashMap<>();
            if (request.getCategory() != null) filters.put("category", request.getCategory());
            if (request.getBrand() != null) filters.put("brand", request.getBrand());
            if (request.getMinPrice() != null) filters.put("minPrice", request.getMinPrice().toString());
            if (request.getMaxPrice() != null) filters.put("maxPrice", request.getMaxPrice().toString());
            if (request.getMinRating() != null) filters.put("minRating", request.getMinRating().toString());
            if (request.getInStock() != null) filters.put("inStock", request.getInStock().toString());
            searchQuery.setAppliedFilters(filters);

            String json = objectMapper.writeValueAsString(searchQuery);
            IndexRequest indexRequest = new IndexRequest(searchQueriesIndex)
                    .id(searchQuery.getId())
                    .source(json, XContentType.JSON);

            client.index(indexRequest, RequestOptions.DEFAULT);
            log.debug("Logged search query: {}", searchQuery.getQueryText());
        } catch (IOException e) {
            log.warn("Failed to log search query", e);
        }
    }

    public List<String> getTopSearchTerms(int topN) throws IOException {
        SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();
        sourceBuilder.size(0);
        sourceBuilder.aggregation(AggregationBuilders.terms("top_queries")
                .field("queryText.keyword")
                .size(topN));

        SearchRequest searchRequest = new SearchRequest(searchQueriesIndex);
        searchRequest.source(sourceBuilder);

        var response = client.search(searchRequest, RequestOptions.DEFAULT);
        Terms topQueries = response.getAggregations().get("top_queries");

        List<String> terms = new ArrayList<>();
        for (Terms.Bucket bucket : topQueries.getBuckets()) {
            terms.add(bucket.getKeyAsString());
        }
        return terms;
    }

    public List<String> getZeroResultQueries(int topN) throws IOException {
        SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();
        sourceBuilder.query(QueryBuilders.termQuery("totalResults", 0));
        sourceBuilder.size(0);
        sourceBuilder.aggregation(AggregationBuilders.terms("zero_result_queries")
                .field("queryText.keyword")
                .size(topN));

        SearchRequest searchRequest = new SearchRequest(searchQueriesIndex);
        searchRequest.source(sourceBuilder);

        var response = client.search(searchRequest, RequestOptions.DEFAULT);
        Terms zeroResultQueries = response.getAggregations().get("zero_result_queries");

        List<String> terms = new ArrayList<>();
        for (Terms.Bucket bucket : zeroResultQueries.getBuckets()) {
            terms.add(bucket.getKeyAsString());
        }
        return terms;
    }
}
