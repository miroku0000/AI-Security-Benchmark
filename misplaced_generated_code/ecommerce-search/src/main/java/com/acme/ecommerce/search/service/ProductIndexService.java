package com.acme.ecommerce.search.service;

import com.acme.ecommerce.search.model.Product;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.elasticsearch.action.admin.indices.delete.DeleteIndexRequest;
import org.elasticsearch.action.bulk.BulkRequest;
import org.elasticsearch.action.bulk.BulkResponse;
import org.elasticsearch.action.delete.DeleteRequest;
import org.elasticsearch.action.delete.DeleteResponse;
import org.elasticsearch.action.get.GetRequest;
import org.elasticsearch.action.get.GetResponse;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.index.IndexResponse;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.indices.CreateIndexRequest;
import org.elasticsearch.client.indices.GetIndexRequest;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.xcontent.XContentType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
public class ProductIndexService {

    private static final Logger log = LoggerFactory.getLogger(ProductIndexService.class);

    private final RestHighLevelClient client;
    private final ObjectMapper objectMapper;

    @Value("${app.indices.products}")
    private String productsIndex;

    public ProductIndexService(RestHighLevelClient client, ObjectMapper objectMapper) {
        this.client = client;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void initIndex() throws IOException {
        boolean exists = client.indices().exists(
                new GetIndexRequest(productsIndex), RequestOptions.DEFAULT);
        if (!exists) {
            CreateIndexRequest request = new CreateIndexRequest(productsIndex);
            request.settings(Settings.builder()
                    .put("number_of_shards", 1)
                    .put("number_of_replicas", 1)
                    .put("analysis.analyzer.product_analyzer.type", "custom")
                    .put("analysis.analyzer.product_analyzer.tokenizer", "standard")
                    .put("analysis.analyzer.product_analyzer.filter", "lowercase,asciifolding")
            );
            request.mapping(Map.of(
                    "properties", Map.ofEntries(
                            Map.entry("name", Map.of("type", "text", "analyzer", "product_analyzer",
                                    "fields", Map.of("keyword", Map.of("type", "keyword")))),
                            Map.entry("description", Map.of("type", "text", "analyzer", "product_analyzer")),
                            Map.entry("sku", Map.of("type", "keyword")),
                            Map.entry("price", Map.of("type", "double")),
                            Map.entry("currency", Map.of("type", "keyword")),
                            Map.entry("brand", Map.of("type", "keyword")),
                            Map.entry("category", Map.of("type", "keyword")),
                            Map.entry("tags", Map.of("type", "keyword")),
                            Map.entry("attributes", Map.of("type", "object", "enabled", true)),
                            Map.entry("stockQuantity", Map.of("type", "integer")),
                            Map.entry("rating", Map.of("type", "double")),
                            Map.entry("reviewCount", Map.of("type", "integer")),
                            Map.entry("imageUrl", Map.of("type", "keyword", "index", false)),
                            Map.entry("active", Map.of("type", "boolean")),
                            Map.entry("createdAt", Map.of("type", "date")),
                            Map.entry("updatedAt", Map.of("type", "date"))
                    )
            ), XContentType.JSON);
            client.indices().create(request, RequestOptions.DEFAULT);
            log.info("Created index: {}", productsIndex);
        }
    }

    public Product indexProduct(Product product) throws IOException {
        if (product.getId() == null || product.getId().isBlank()) {
            product.setId(UUID.randomUUID().toString());
        }
        Instant now = Instant.now();
        if (product.getCreatedAt() == null) {
            product.setCreatedAt(now);
        }
        product.setUpdatedAt(now);

        String json = objectMapper.writeValueAsString(product);
        IndexRequest request = new IndexRequest(productsIndex)
                .id(product.getId())
                .source(json, XContentType.JSON);

        IndexResponse response = client.index(request, RequestOptions.DEFAULT);
        log.info("Indexed product {} with result {}", product.getId(), response.getResult().name());
        return product;
    }

    public BulkResponse bulkIndex(List<Product> products) throws IOException {
        BulkRequest bulkRequest = new BulkRequest();
        Instant now = Instant.now();
        for (Product product : products) {
            if (product.getId() == null || product.getId().isBlank()) {
                product.setId(UUID.randomUUID().toString());
            }
            if (product.getCreatedAt() == null) {
                product.setCreatedAt(now);
            }
            product.setUpdatedAt(now);

            String json = objectMapper.writeValueAsString(product);
            bulkRequest.add(new IndexRequest(productsIndex)
                    .id(product.getId())
                    .source(json, XContentType.JSON));
        }
        return client.bulk(bulkRequest, RequestOptions.DEFAULT);
    }

    public Optional<Product> getProduct(String id) throws IOException {
        GetResponse response = client.get(
                new GetRequest(productsIndex, id), RequestOptions.DEFAULT);
        if (!response.isExists()) {
            return Optional.empty();
        }
        Product product = objectMapper.readValue(response.getSourceAsString(), Product.class);
        product.setId(response.getId());
        return Optional.of(product);
    }

    public boolean deleteProduct(String id) throws IOException {
        DeleteResponse response = client.delete(
                new DeleteRequest(productsIndex, id), RequestOptions.DEFAULT);
        return "DELETED".equals(response.getResult().name());
    }
}
