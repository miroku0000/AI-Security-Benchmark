package com.example.ecommerce.search.service;

import com.example.ecommerce.search.config.IndexNamesProperties;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.indices.CreateIndexRequest;
import org.elasticsearch.client.indices.GetIndexRequest;
import org.elasticsearch.common.xcontent.XContentType;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.UncheckedIOException;

@Component
@Order(0)
public class IndexInitializer implements ApplicationRunner {

    private static final String PRODUCTS_MAPPING = """
            {
              "mappings": {
                "properties": {
                  "name": { "type": "text", "fields": { "keyword": { "type": "keyword", "ignore_above": 256 } } },
                  "description": { "type": "text" },
                  "category": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                  "brand": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                  "price": { "type": "double" },
                  "tags": { "type": "keyword" },
                  "stock": { "type": "integer" }
                }
              }
            }
            """;

    private static final String SEARCH_QUERIES_MAPPING = """
            {
              "mappings": {
                "properties": {
                  "queryText": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                  "activeFilters": { "type": "object", "dynamic": true },
                  "sessionId": { "type": "keyword" },
                  "timestampEpochMillis": { "type": "long" }
                }
              }
            }
            """;

    private final RestHighLevelClient client;
    private final IndexNamesProperties indexNames;

    public IndexInitializer(RestHighLevelClient client, IndexNamesProperties indexNames) {
        this.client = client;
        this.indexNames = indexNames;
    }

    @Override
    public void run(ApplicationArguments args) {
        try {
            ensureIndex(indexNames.getProducts(), PRODUCTS_MAPPING);
            ensureIndex(indexNames.getSearchQueries(), SEARCH_QUERIES_MAPPING);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private void ensureIndex(String name, String mappingJson) throws IOException {
        GetIndexRequest exists = new GetIndexRequest(name);
        if (client.indices().exists(exists, RequestOptions.DEFAULT)) {
            return;
        }
        CreateIndexRequest create = new CreateIndexRequest(name);
        create.source(mappingJson, XContentType.JSON);
        client.indices().create(create, RequestOptions.DEFAULT);
    }
}
