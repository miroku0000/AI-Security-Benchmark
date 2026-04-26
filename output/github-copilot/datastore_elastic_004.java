#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="ecommerce-search-service"

mkdir -p "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/config"
mkdir -p "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/controller"
mkdir -p "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/exception"
mkdir -p "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/model"
mkdir -p "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/service"
mkdir -p "$PROJECT_DIR/src/main/resources"
mkdir -p "$PROJECT_DIR/src/test/java/com/example/ecommerce/search"

cat > "$PROJECT_DIR/pom.xml" <<'EOF'
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>2.7.18</version>
        <relativePath/>
    </parent>

    <groupId>com.example</groupId>
    <artifactId>ecommerce-search-service</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>ecommerce-search-service</name>
    <description>Spring Boot Elasticsearch product search service</description>

    <properties>
        <java.version>17</java.version>
        <elasticsearch.version>7.17.18</elasticsearch.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.elasticsearch.client</groupId>
            <artifactId>elasticsearch-rest-high-level-client</artifactId>
            <version>${elasticsearch.version}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/EcommerceSearchApplication.java" <<'EOF'
package com.example.ecommerce.search;

import com.example.ecommerce.search.service.IndexManagementService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class EcommerceSearchApplication {

    public static void main(String[] args) {
        SpringApplication.run(EcommerceSearchApplication.class, args);
    }

    @Bean
    @ConditionalOnProperty(name = "app.elasticsearch.initialize-indices", havingValue = "true", matchIfMissing = true)
    CommandLineRunner initializeIndices(IndexManagementService indexManagementService) {
        return args -> indexManagementService.initializeIndices();
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/config/ElasticsearchProperties.java" <<'EOF'
package com.example.ecommerce.search.config;

import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.elasticsearch")
public class ElasticsearchProperties {

    private List<String> hosts = new ArrayList<>(List.of("localhost:9200"));
    private String scheme = "http";
    private String username;
    private String password;
    private int connectTimeoutMillis = 5000;
    private int socketTimeoutMillis = 60000;
    private String productsIndex = "products";
    private String searchQueriesIndex = "customer_search_queries";
    private boolean initializeIndices = true;

    public List<String> getHosts() {
        return hosts;
    }

    public void setHosts(List<String> hosts) {
        this.hosts = hosts;
    }

    public String getScheme() {
        return scheme;
    }

    public void setScheme(String scheme) {
        this.scheme = scheme;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public int getConnectTimeoutMillis() {
        return connectTimeoutMillis;
    }

    public void setConnectTimeoutMillis(int connectTimeoutMillis) {
        this.connectTimeoutMillis = connectTimeoutMillis;
    }

    public int getSocketTimeoutMillis() {
        return socketTimeoutMillis;
    }

    public void setSocketTimeoutMillis(int socketTimeoutMillis) {
        this.socketTimeoutMillis = socketTimeoutMillis;
    }

    public String getProductsIndex() {
        return productsIndex;
    }

    public void setProductsIndex(String productsIndex) {
        this.productsIndex = productsIndex;
    }

    public String getSearchQueriesIndex() {
        return searchQueriesIndex;
    }

    public void setSearchQueriesIndex(String searchQueriesIndex) {
        this.searchQueriesIndex = searchQueriesIndex;
    }

    public boolean isInitializeIndices() {
        return initializeIndices;
    }

    public void setInitializeIndices(boolean initializeIndices) {
        this.initializeIndices = initializeIndices;
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/config/ElasticsearchConfig.java" <<'EOF'
package com.example.ecommerce.search.config;

import java.util.List;
import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.RestHighLevelClient;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;

@Configuration
@EnableConfigurationProperties(ElasticsearchProperties.class)
public class ElasticsearchConfig {

    @Bean(destroyMethod = "close")
    public RestHighLevelClient restHighLevelClient(ElasticsearchProperties properties) {
        List<String> configuredHosts = properties.getHosts();
        HttpHost[] hosts = configuredHosts.stream()
            .map(host -> {
                String[] parts = host.split(":");
                String hostname = parts[0];
                int port = parts.length > 1 ? Integer.parseInt(parts[1]) : 9200;
                return new HttpHost(hostname, port, properties.getScheme());
            })
            .toArray(HttpHost[]::new);

        RestClientBuilder builder = RestClient.builder(hosts)
            .setRequestConfigCallback(requestConfigBuilder -> requestConfigBuilder
                .setConnectTimeout(properties.getConnectTimeoutMillis())
                .setSocketTimeout(properties.getSocketTimeoutMillis()));

        if (StringUtils.hasText(properties.getUsername())) {
            BasicCredentialsProvider credentialsProvider = new BasicCredentialsProvider();
            credentialsProvider.setCredentials(
                AuthScope.ANY,
                new UsernamePasswordCredentials(properties.getUsername(), properties.getPassword())
            );
            builder.setHttpClientConfigCallback(httpClientBuilder ->
                httpClientBuilder.setDefaultCredentialsProvider(credentialsProvider));
        }

        return new RestHighLevelClient(builder);
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/controller/ProductController.java" <<'EOF'
package com.example.ecommerce.search.controller;

import com.example.ecommerce.search.model.ProductDocument;
import com.example.ecommerce.search.service.ProductIndexService;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import javax.validation.Valid;
import javax.validation.constraints.NotEmpty;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Validated
@RequestMapping("/api/products")
public class ProductController {

    private final ProductIndexService productIndexService;

    public ProductController(ProductIndexService productIndexService) {
        this.productIndexService = productIndexService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ProductDocument indexProduct(@Valid @RequestBody ProductDocument product) throws IOException {
        return productIndexService.indexProduct(product);
    }

    @PostMapping("/bulk")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> bulkIndexProducts(@Valid @RequestBody @NotEmpty List<@Valid ProductDocument> products)
        throws IOException {
        return productIndexService.bulkIndexProducts(products);
    }

    @GetMapping("/{id}")
    public ProductDocument getProduct(@PathVariable String id) throws IOException {
        return productIndexService.getProduct(id);
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/controller/SearchController.java" <<'EOF'
package com.example.ecommerce.search.controller;

import com.example.ecommerce.search.model.ProductSearchRequest;
import com.example.ecommerce.search.model.ProductSearchResponse;
import com.example.ecommerce.search.service.ProductSearchService;
import java.io.IOException;
import javax.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/search")
public class SearchController {

    private final ProductSearchService productSearchService;

    public SearchController(ProductSearchService productSearchService) {
        this.productSearchService = productSearchService;
    }

    @PostMapping("/products")
    public ProductSearchResponse searchProducts(@Valid @RequestBody ProductSearchRequest request) throws IOException {
        return productSearchService.searchProducts(request);
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/exception/GlobalExceptionHandler.java" <<'EOF'
package com.example.ecommerce.search.exception;

import java.io.IOException;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
        Map<String, String> fieldErrors = new LinkedHashMap<>();
        for (FieldError error : ex.getBindingResult().getFieldErrors()) {
            fieldErrors.put(error.getField(), error.getDefaultMessage());
        }
        return buildResponse(HttpStatus.BAD_REQUEST, "Validation failed", fieldErrors);
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, Object>> handleStatus(ResponseStatusException ex) {
        return buildResponse(ex.getStatus(), ex.getReason(), null);
    }

    @ExceptionHandler({IllegalArgumentException.class, IOException.class})
    public ResponseEntity<Map<String, Object>> handleBadRequest(Exception ex) {
        HttpStatus status = ex instanceof IOException ? HttpStatus.SERVICE_UNAVAILABLE : HttpStatus.BAD_REQUEST;
        return buildResponse(status, ex.getMessage(), null);
    }

    private ResponseEntity<Map<String, Object>> buildResponse(
        HttpStatus status,
        String message,
        Map<String, ?> details
    ) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", Instant.now().toString());
        body.put("status", status.value());
        body.put("error", status.getReasonPhrase());
        body.put("message", message);
        if (details != null && !details.isEmpty()) {
            body.put("details", details);
        }
        return ResponseEntity.status(status).body(body);
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/model/ProductDocument.java" <<'EOF'
package com.example.ecommerce.search.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import javax.validation.constraints.DecimalMin;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class ProductDocument {

    @NotBlank(message = "id is required")
    private String id;

    @NotBlank(message = "sku is required")
    private String sku;

    @NotBlank(message = "name is required")
    private String name;

    @NotBlank(message = "description is required")
    private String description;

    @NotBlank(message = "category is required")
    private String category;

    @NotBlank(message = "brand is required")
    private String brand;

    @NotNull(message = "price is required")
    @DecimalMin(value = "0.0", inclusive = false, message = "price must be greater than zero")
    private BigDecimal price;

    @NotBlank(message = "currency is required")
    private String currency;

    @NotNull(message = "available is required")
    private Boolean available;

    private List<String> tags = new ArrayList<>();
    private Map<String, Object> attributes = new LinkedHashMap<>();
    private Instant createdAt;
    private Instant updatedAt;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getSku() {
        return sku;
    }

    public void setSku(String sku) {
        this.sku = sku;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public String getBrand() {
        return brand;
    }

    public void setBrand(String brand) {
        this.brand = brand;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String currency) {
        this.currency = currency;
    }

    public Boolean getAvailable() {
        return available;
    }

    public void setAvailable(Boolean available) {
        this.available = available;
    }

    public List<String> getTags() {
        return tags;
    }

    public void setTags(List<String> tags) {
        this.tags = tags;
    }

    public Map<String, Object> getAttributes() {
        return attributes;
    }

    public void setAttributes(Map<String, Object> attributes) {
        this.attributes = attributes;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/model/ProductSearchRequest.java" <<'EOF'
package com.example.ecommerce.search.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class ProductSearchRequest {

    private String query;
    private List<String> categories = new ArrayList<>();
    private List<String> brands = new ArrayList<>();
    private List<String> tags = new ArrayList<>();
    private Boolean available;
    private BigDecimal minPrice;
    private BigDecimal maxPrice;
    private String customerId;
    private String sessionId;
    private boolean includeFacets = true;

    @Min(value = 0, message = "page must be zero or greater")
    private int page = 0;

    @Min(value = 1, message = "size must be at least 1")
    @Max(value = 100, message = "size must be at most 100")
    private int size = 10;

    public String getQuery() {
        return query;
    }

    public void setQuery(String query) {
        this.query = query;
    }

    public List<String> getCategories() {
        return categories;
    }

    public void setCategories(List<String> categories) {
        this.categories = categories;
    }

    public List<String> getBrands() {
        return brands;
    }

    public void setBrands(List<String> brands) {
        this.brands = brands;
    }

    public List<String> getTags() {
        return tags;
    }

    public void setTags(List<String> tags) {
        this.tags = tags;
    }

    public Boolean getAvailable() {
        return available;
    }

    public void setAvailable(Boolean available) {
        this.available = available;
    }

    public BigDecimal getMinPrice() {
        return minPrice;
    }

    public void setMinPrice(BigDecimal minPrice) {
        this.minPrice = minPrice;
    }

    public BigDecimal getMaxPrice() {
        return maxPrice;
    }

    public void setMaxPrice(BigDecimal maxPrice) {
        this.maxPrice = maxPrice;
    }

    public String getCustomerId() {
        return customerId;
    }

    public void setCustomerId(String customerId) {
        this.customerId = customerId;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public boolean isIncludeFacets() {
        return includeFacets;
    }

    public void setIncludeFacets(boolean includeFacets) {
        this.includeFacets = includeFacets;
    }

    public int getPage() {
        return page;
    }

    public void setPage(int page) {
        this.page = page;
    }

    public int getSize() {
        return size;
    }

    public void setSize(int size) {
        this.size = size;
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/model/ProductSearchResponse.java" <<'EOF'
package com.example.ecommerce.search.model;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class ProductSearchResponse {

    private List<ProductDocument> products = new ArrayList<>();
    private long totalHits;
    private int page;
    private int size;
    private Map<String, List<FacetBucket>> facets = new LinkedHashMap<>();

    public List<ProductDocument> getProducts() {
        return products;
    }

    public void setProducts(List<ProductDocument> products) {
        this.products = products;
    }

    public long getTotalHits() {
        return totalHits;
    }

    public void setTotalHits(long totalHits) {
        this.totalHits = totalHits;
    }

    public int getPage() {
        return page;
    }

    public void setPage(int page) {
        this.page = page;
    }

    public int getSize() {
        return size;
    }

    public void setSize(int size) {
        this.size = size;
    }

    public Map<String, List<FacetBucket>> getFacets() {
        return facets;
    }

    public void setFacets(Map<String, List<FacetBucket>> facets) {
        this.facets = facets;
    }

    public static class FacetBucket {
        private String key;
        private long count;

        public FacetBucket() {
        }

        public FacetBucket(String key, long count) {
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
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/model/SearchQueryDocument.java" <<'EOF'
package com.example.ecommerce.search.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class SearchQueryDocument {

    private String searchTerm;
    private String customerId;
    private String sessionId;
    private Map<String, Object> filters = new LinkedHashMap<>();
    private long resultCount;
    private Instant executedAt;

    public String getSearchTerm() {
        return searchTerm;
    }

    public void setSearchTerm(String searchTerm) {
        this.searchTerm = searchTerm;
    }

    public String getCustomerId() {
        return customerId;
    }

    public void setCustomerId(String customerId) {
        this.customerId = customerId;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public Map<String, Object> getFilters() {
        return filters;
    }

    public void setFilters(Map<String, Object> filters) {
        this.filters = filters;
    }

    public long getResultCount() {
        return resultCount;
    }

    public void setResultCount(long resultCount) {
        this.resultCount = resultCount;
    }

    public Instant getExecutedAt() {
        return executedAt;
    }

    public void setExecutedAt(Instant executedAt) {
        this.executedAt = executedAt;
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/service/IndexManagementService.java" <<'EOF'
package com.example.ecommerce.search.service;

import com.example.ecommerce.search.config.ElasticsearchProperties;
import java.io.IOException;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.indices.CreateIndexRequest;
import org.elasticsearch.client.indices.DeleteIndexRequest;
import org.elasticsearch.client.indices.GetIndexRequest;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.common.xcontent.XContentFactory;
import org.springframework.stereotype.Service;

@Service
public class IndexManagementService {

    private final RestHighLevelClient client;
    private final ElasticsearchProperties properties;

    public IndexManagementService(RestHighLevelClient client, ElasticsearchProperties properties) {
        this.client = client;
        this.properties = properties;
    }

    public void initializeIndices() throws IOException {
        ensureProductsIndex();
        ensureSearchQueriesIndex();
    }

    private void ensureProductsIndex() throws IOException {
        String indexName = properties.getProductsIndex();
        if (client.indices().exists(new GetIndexRequest(indexName), RequestOptions.DEFAULT)) {
            return;
        }

        CreateIndexRequest request = new CreateIndexRequest(indexName);
        request.settings(Settings.builder()
            .put("index.number_of_shards", 1)
            .put("index.number_of_replicas", 1));
        request.mapping(productMapping());
        client.indices().create(request, RequestOptions.DEFAULT);
    }

    private void ensureSearchQueriesIndex() throws IOException {
        String indexName = properties.getSearchQueriesIndex();
        if (client.indices().exists(new GetIndexRequest(indexName), RequestOptions.DEFAULT)) {
            return;
        }

        CreateIndexRequest request = new CreateIndexRequest(indexName);
        request.settings(Settings.builder()
            .put("index.number_of_shards", 1)
            .put("index.number_of_replicas", 1));
        request.mapping(searchQueryMapping());
        client.indices().create(request, RequestOptions.DEFAULT);
    }

    public void recreateIndices() throws IOException {
        deleteIfExists(properties.getProductsIndex());
        deleteIfExists(properties.getSearchQueriesIndex());
        initializeIndices();
    }

    private void deleteIfExists(String indexName) throws IOException {
        if (client.indices().exists(new GetIndexRequest(indexName), RequestOptions.DEFAULT)) {
            client.indices().delete(new DeleteIndexRequest(indexName), RequestOptions.DEFAULT);
        }
    }

    private XContentBuilder productMapping() throws IOException {
        XContentBuilder builder = XContentFactory.jsonBuilder();
        builder.startObject();
        builder.startObject("properties");

        keywordField(builder, "id");
        keywordField(builder, "sku");
        textFieldWithKeyword(builder, "name");

        builder.startObject("description")
            .field("type", "text")
            .endObject();

        keywordField(builder, "category");
        keywordField(builder, "brand");

        builder.startObject("price")
            .field("type", "scaled_float")
            .field("scaling_factor", 100)
            .endObject();

        keywordField(builder, "currency");

        builder.startObject("available")
            .field("type", "boolean")
            .endObject();

        builder.startObject("tags")
            .field("type", "keyword")
            .endObject();

        builder.startObject("attributes")
            .field("type", "object")
            .field("dynamic", true)
            .endObject();

        builder.startObject("createdAt")
            .field("type", "date")
            .endObject();

        builder.startObject("updatedAt")
            .field("type", "date")
            .endObject();

        builder.endObject();
        builder.endObject();
        return builder;
    }

    private XContentBuilder searchQueryMapping() throws IOException {
        XContentBuilder builder = XContentFactory.jsonBuilder();
        builder.startObject();
        builder.startObject("properties");

        textFieldWithKeyword(builder, "searchTerm");
        keywordField(builder, "customerId");
        keywordField(builder, "sessionId");

        builder.startObject("filters")
            .field("type", "object")
            .field("dynamic", true)
            .endObject();

        builder.startObject("resultCount")
            .field("type", "long")
            .endObject();

        builder.startObject("executedAt")
            .field("type", "date")
            .endObject();

        builder.endObject();
        builder.endObject();
        return builder;
    }

    private void textFieldWithKeyword(XContentBuilder builder, String fieldName) throws IOException {
        builder.startObject(fieldName)
            .field("type", "text")
            .startObject("fields")
                .startObject("keyword")
                    .field("type", "keyword")
                    .field("ignore_above", 256)
                .endObject()
            .endObject()
            .endObject();
    }

    private void keywordField(XContentBuilder builder, String fieldName) throws IOException {
        builder.startObject(fieldName)
            .field("type", "keyword")
            .endObject();
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/service/ProductIndexService.java" <<'EOF'
package com.example.ecommerce.search.service;

import com.example.ecommerce.search.config.ElasticsearchProperties;
import com.example.ecommerce.search.model.ProductDocument;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.elasticsearch.action.DocWriteResponse;
import org.elasticsearch.action.bulk.BulkItemResponse;
import org.elasticsearch.action.bulk.BulkRequest;
import org.elasticsearch.action.bulk.BulkResponse;
import org.elasticsearch.action.get.GetRequest;
import org.elasticsearch.action.get.GetResponse;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.support.WriteRequest;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.common.xcontent.XContentType;
import org.elasticsearch.rest.RestStatus;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ProductIndexService {

    private final RestHighLevelClient client;
    private final ElasticsearchProperties properties;
    private final ObjectMapper objectMapper;

    public ProductIndexService(
        RestHighLevelClient client,
        ElasticsearchProperties properties,
        ObjectMapper objectMapper
    ) {
        this.client = client;
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    public ProductDocument indexProduct(ProductDocument product) throws IOException {
        Instant now = Instant.now();
        if (product.getCreatedAt() == null) {
            product.setCreatedAt(now);
        }
        product.setUpdatedAt(now);

        IndexRequest request = new IndexRequest(properties.getProductsIndex())
            .id(product.getId())
            .source(objectMapper.writeValueAsString(product), XContentType.JSON)
            .setRefreshPolicy(WriteRequest.RefreshPolicy.IMMEDIATE);

        DocWriteResponse response = client.index(request, RequestOptions.DEFAULT);
        if (response.status() != RestStatus.CREATED && response.status() != RestStatus.OK) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to index product");
        }
        return product;
    }

    public Map<String, Object> bulkIndexProducts(List<ProductDocument> products) throws IOException {
        BulkRequest bulkRequest = new BulkRequest().setRefreshPolicy(WriteRequest.RefreshPolicy.IMMEDIATE);

        for (ProductDocument product : products) {
            Instant now = Instant.now();
            if (product.getCreatedAt() == null) {
                product.setCreatedAt(now);
            }
            product.setUpdatedAt(now);

            bulkRequest.add(new IndexRequest(properties.getProductsIndex())
                .id(product.getId())
                .source(objectMapper.writeValueAsString(product), XContentType.JSON));
        }

        BulkResponse response = client.bulk(bulkRequest, RequestOptions.DEFAULT);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("indexedCount", products.size());
        result.put("hasFailures", response.hasFailures());

        if (response.hasFailures()) {
            Map<String, String> failures = new LinkedHashMap<>();
            for (BulkItemResponse itemResponse : response.getItems()) {
                if (itemResponse.isFailed()) {
                    failures.put(itemResponse.getId(), itemResponse.getFailureMessage());
                }
            }
            result.put("failures", failures);
        }

        return result;
    }

    public ProductDocument getProduct(String id) throws IOException {
        GetResponse response = client.get(
            new GetRequest(properties.getProductsIndex(), id),
            RequestOptions.DEFAULT
        );

        if (!response.isExists()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Product not found");
        }

        return objectMapper.readValue(response.getSourceAsString(), ProductDocument.class);
    }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/ecommerce/search/service/ProductSearchService.java" <<'EOF'
package com.example.ecommerce.search.service;

import com.example.ecommerce.search.config.ElasticsearchProperties;
import com.example.ecommerce.search.model.ProductDocument;
import com.example.ecommerce.search.model.ProductSearchRequest;
import com.example.ecommerce.search.model.ProductSearchResponse;
import com.example.ecommerce.search.model.SearchQueryDocument;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.action.support.WriteRequest;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.common.unit.Fuzziness;
import org.elasticsearch.common.xcontent.XContentType;
import org.elasticsearch.index.query.BoolQueryBuilder;
import org.elasticsearch.index.query.MultiMatchQueryBuilder;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.index.query.RangeQueryBuilder;
import org.elasticsearch.search.SearchHit;
import org.elasticsearch.search.aggregations.AggregationBuilders;
import org.elasticsearch.search.aggregations.Aggregations;
import org.elasticsearch.search.aggregations.bucket.range.ParsedRange;
import org.elasticsearch.search.aggregations.bucket.terms.ParsedStringTerms;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class ProductSearchService {

    private static final String CATEGORY_FACET = "categoryFacet";
    private static final String BRAND_FACET = "brandFacet";
    private static final String TAG_FACET = "tagFacet";
    private static final String PRICE_FACET = "priceFacet";

    private final RestHighLevelClient client;
    private final ElasticsearchProperties properties;
    private final ObjectMapper objectMapper;

    public ProductSearchService(
        RestHighLevelClient client,
        ElasticsearchProperties properties,
        ObjectMapper objectMapper
    ) {
        this.client = client;
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    public ProductSearchResponse searchProducts(ProductSearchRequest request) throws IOException {
        if (request.getMinPrice() != null && request.getMaxPrice() != null
            && request.getMinPrice().compareTo(request.getMaxPrice()) > 0) {
            throw new IllegalArgumentException("minPrice must be less than or equal to maxPrice");
        }

        SearchSourceBuilder sourceBuilder = new SearchSourceBuilder()
            .query(buildQuery(request))
            .from(request.getPage() * request.getSize())
            .size(request.getSize())
            .trackTotalHits(true);

        if (request.isIncludeFacets()) {
            sourceBuilder.aggregation(AggregationBuilders.terms(CATEGORY_FACET).field("category").size(25));
            sourceBuilder.aggregation(AggregationBuilders.terms(BRAND_FACET).field("brand").size(25));
            sourceBuilder.aggregation(AggregationBuilders.terms(TAG_FACET).field("tags").size(25));
            sourceBuilder.aggregation(
                AggregationBuilders.range(PRICE_FACET)
                    .field("price")
                    .addUnboundedTo("Under 50", 50)
                    .addRange("50-100", 50, 100)
                    .addRange("100-250", 100, 250)
                    .addRange("250-500", 250, 500)
                    .addUnboundedFrom("500+", 500)
            );
        }

        SearchRequest searchRequest = new SearchRequest(properties.getProductsIndex()).source(sourceBuilder);
        SearchResponse response = client.search(searchRequest, RequestOptions.DEFAULT);

        ProductSearchResponse searchResponse = new ProductSearchResponse();
        searchResponse.setProducts(mapProducts(response.getHits().getHits()));
        searchResponse.setTotalHits(response.getHits().getTotalHits() == null ? 0 : response.getHits().getTotalHits().value);
        searchResponse.setPage(request.getPage());
        searchResponse.setSize(request.getSize());
        if (request.isIncludeFacets()) {
            searchResponse.setFacets(mapFacets(response.getAggregations()));
        }

        logSearchQuery(request, searchResponse.getTotalHits());
        return searchResponse;
    }

    private BoolQueryBuilder buildQuery(ProductSearchRequest request) {
        BoolQueryBuilder boolQuery = QueryBuilders.boolQuery();

        if (StringUtils.hasText(request.getQuery())) {
            MultiMatchQueryBuilder multiMatchQuery = QueryBuilders.multiMatchQuery(
                    request.getQuery(),
                    "name^4",
                    "description^2",
                    "brand^2",
                    "category",
                    "tags"
                )
                .fuzziness(Fuzziness.AUTO)
                .operator(MultiMatchQueryBuilder.Operator.AND);
            boolQuery.must(multiMatchQuery);
        } else {
            boolQuery.must(QueryBuilders.matchAllQuery());
        }

        if (request.getCategories() != null && !request.getCategories().isEmpty()) {
            boolQuery.filter(QueryBuilders.termsQuery("category", request.getCategories()));
        }

        if (request.getBrands() != null && !request.getBrands().isEmpty()) {
            boolQuery.filter(QueryBuilders.termsQuery("brand", request.getBrands()));
        }

        if (request.getTags() != null && !request.getTags().isEmpty()) {
            boolQuery.filter(QueryBuilders.termsQuery("tags", request.getTags()));
        }

        if (request.getAvailable() != null) {
            boolQuery.filter(QueryBuilders.termQuery("available", request.getAvailable()));
        }

        if (request.getMinPrice() != null || request.getMaxPrice() != null) {
            RangeQueryBuilder rangeQuery = QueryBuilders.rangeQuery("price");
            if (request.getMinPrice() != null) {
                rangeQuery.gte(request.getMinPrice());
            }
            if (request.getMaxPrice() != null) {
                rangeQuery.lte(request.getMaxPrice());
            }
            boolQuery.filter(rangeQuery);
        }

        return boolQuery;
    }

    private List<ProductDocument> mapProducts(SearchHit[] hits) throws IOException {
        List<ProductDocument> products = new ArrayList<>();
        for (SearchHit hit : hits) {
            products.add(objectMapper.readValue(hit.getSourceAsString(), ProductDocument.class));
        }
        return products;
    }

    private Map<String, List<ProductSearchResponse.FacetBucket>> mapFacets(Aggregations aggregations) {
        Map<String, List<ProductSearchResponse.FacetBucket>> facets = new LinkedHashMap<>();
        if (aggregations == null) {
            return facets;
        }

        facets.put("categories", mapTermsFacet(aggregations.get(CATEGORY_FACET)));
        facets.put("brands", mapTermsFacet(aggregations.get(BRAND_FACET)));
        facets.put("tags", mapTermsFacet(aggregations.get(TAG_FACET)));
        facets.put("priceRanges", mapPriceFacet(aggregations.get(PRICE_FACET)));
        return facets;
    }

    private List<ProductSearchResponse.FacetBucket> mapTermsFacet(ParsedStringTerms aggregation) {
        List<ProductSearchResponse.FacetBucket> buckets = new ArrayList<>();
        if (aggregation == null) {
            return buckets;
        }
        aggregation.getBuckets().forEach(bucket ->
            buckets.add(new ProductSearchResponse.FacetBucket(bucket.getKeyAsString(), bucket.getDocCount()))
        );
        return buckets;
    }

    private List<ProductSearchResponse.FacetBucket> mapPriceFacet(ParsedRange aggregation) {
        List<ProductSearchResponse.FacetBucket> buckets = new ArrayList<>();
        if (aggregation == null) {
            return buckets;
        }
        aggregation.getBuckets().forEach(bucket ->
            buckets.add(new ProductSearchResponse.FacetBucket(bucket.getKeyAsString(), bucket.getDocCount()))
        );
        return buckets;
    }

    private void logSearchQuery(ProductSearchRequest request, long resultCount) throws IOException {
        SearchQueryDocument searchQuery = new SearchQueryDocument();
        searchQuery.setSearchTerm(request.getQuery());
        searchQuery.setCustomerId(request.getCustomerId());
        searchQuery.setSessionId(request.getSessionId());
        searchQuery.setFilters(extractFilters(request));
        searchQuery.setResultCount(resultCount);
        searchQuery.setExecutedAt(Instant.now());

        IndexRequest indexRequest = new IndexRequest(properties.getSearchQueriesIndex())
            .source(objectMapper.writeValueAsString(searchQuery), XContentType.JSON)
            .setRefreshPolicy(WriteRequest.RefreshPolicy.IMMEDIATE);

        client.index(indexRequest, RequestOptions.DEFAULT);
    }

    private Map<String, Object> extractFilters(ProductSearchRequest request) {
        Map<String, Object> filters = new LinkedHashMap<>();

        if (request.getCategories() != null && !request.getCategories().isEmpty()) {
            filters.put("categories", request.getCategories());
        }

        if (request.getBrands() != null && !request.getBrands().isEmpty()) {
            filters.put("brands", request.getBrands());
        }

        if (request.getTags() != null && !request.getTags().isEmpty()) {
            filters.put("tags", request.getTags());
        }

        if (request.getAvailable() != null) {
            filters.put("available", request.getAvailable());
        }

        if (request.getMinPrice() != null) {
            filters.put("minPrice", request.getMinPrice());
        }

        if (request.getMaxPrice() != null) {
            filters.put("maxPrice", request.getMaxPrice());
        }

        return filters;
    }
}
EOF

cat > "$PROJECT_DIR/src/main/resources/application.yml" <<'EOF'
spring:
  application:
    name: ecommerce-search-service

server:
  port: 8080

app:
  elasticsearch:
    hosts: ${ELASTICSEARCH_HOSTS:localhost:9200}
    scheme: ${ELASTICSEARCH_SCHEME:http}
    username: ${ELASTICSEARCH_USERNAME:}
    password: ${ELASTICSEARCH_PASSWORD:}
    connect-timeout-millis: ${ELASTICSEARCH_CONNECT_TIMEOUT:5000}
    socket-timeout-millis: ${ELASTICSEARCH_SOCKET_TIMEOUT:60000}
    products-index: ${ELASTICSEARCH_PRODUCTS_INDEX:products}
    search-queries-index: ${ELASTICSEARCH_SEARCH_QUERIES_INDEX:customer_search_queries}
    initialize-indices: ${ELASTICSEARCH_INITIALIZE_INDICES:true}
EOF

cat > "$PROJECT_DIR/src/test/java/com/example/ecommerce/search/EcommerceSearchApplicationTests.java" <<'EOF'
package com.example.ecommerce.search;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(properties = "app.elasticsearch.initialize-indices=false")
class EcommerceSearchApplicationTests {

    @Test
    void contextLoads() {
    }
}
EOF

cd "$PROJECT_DIR"
mvn spring-boot:run