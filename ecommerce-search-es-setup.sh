#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-ecommerce-search-es}"

if [[ -e "$PROJECT_DIR" ]]; then
  echo "Refusing to overwrite existing path: $PROJECT_DIR" >&2
  exit 1
fi

mkdir -p "$PROJECT_DIR"

cat > "$PROJECT_DIR/pom.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>com.example</groupId>
  <artifactId>ecommerce-search-es</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <name>ecommerce-search-es</name>
  <description>E-commerce product search with Elasticsearch</description>
  <packaging>jar</packaging>

  <properties>
    <java.version>17</java.version>
    <spring-boot.version>2.7.18</spring-boot.version>
    <elasticsearch.version>7.17.21</elasticsearch.version>
  </properties>

  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-dependencies</artifactId>
        <version>${spring-boot.version}</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>
    </dependencies>
  </dependencyManagement>

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
      <groupId>org.elasticsearch</groupId>
      <artifactId>elasticsearch</artifactId>
      <version>${elasticsearch.version}</version>
    </dependency>

    <dependency>
      <groupId>org.elasticsearch.client</groupId>
      <artifactId>elasticsearch-rest-client</artifactId>
      <version>${elasticsearch.version}</version>
    </dependency>

    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
    </dependency>

    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>

    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <optional>true</optional>
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
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <configuration>
          <source>${java.version}</source>
          <target>${java.version}</target>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
EOF

mkdir -p "$PROJECT_DIR/src/main/resources"
cat > "$PROJECT_DIR/src/main/resources/application.yml" <<'EOF'
server:
  port: 8080

app:
  elasticsearch:
    hosts:
      - http://localhost:9200
    productsIndex: products
    queriesIndex: search_queries
    shards: 1
    replicas: 0
    requestTimeoutMs: 30000
EOF

mkdir -p "$PROJECT_DIR/src/main/java/com/example/search"
cat > "$PROJECT_DIR/src/main/java/com/example/search/EcommerceSearchApplication.java" <<'EOF'
package com.example.search;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class EcommerceSearchApplication {
  public static void main(String[] args) {
    SpringApplication.run(EcommerceSearchApplication.class, args);
  }
}
EOF

mkdir -p "$PROJECT_DIR/src/main/java/com/example/search/config"
cat > "$PROJECT_DIR/src/main/java/com/example/search/config/ElasticsearchProperties.java" <<'EOF'
package com.example.search.config;

import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "app.elasticsearch")
public class ElasticsearchProperties {
  private List<String> hosts = new ArrayList<>();
  private String productsIndex = "products";
  private String queriesIndex = "search_queries";
  private int shards = 1;
  private int replicas = 0;
  private int requestTimeoutMs = 30000;

  public List<String> getHosts() {
    return hosts;
  }

  public void setHosts(List<String> hosts) {
    this.hosts = hosts;
  }

  public String getProductsIndex() {
    return productsIndex;
  }

  public void setProductsIndex(String productsIndex) {
    this.productsIndex = productsIndex;
  }

  public String getQueriesIndex() {
    return queriesIndex;
  }

  public void setQueriesIndex(String queriesIndex) {
    this.queriesIndex = queriesIndex;
  }

  public int getShards() {
    return shards;
  }

  public void setShards(int shards) {
    this.shards = shards;
  }

  public int getReplicas() {
    return replicas;
  }

  public void setReplicas(int replicas) {
    this.replicas = replicas;
  }

  public int getRequestTimeoutMs() {
    return requestTimeoutMs;
  }

  public void setRequestTimeoutMs(int requestTimeoutMs) {
    this.requestTimeoutMs = requestTimeoutMs;
  }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/search/config/ElasticsearchConfig.java" <<'EOF'
package com.example.search.config;

import java.net.URI;
import java.util.List;
import java.util.stream.Collectors;
import org.apache.http.HttpHost;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.RestHighLevelClient;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(ElasticsearchProperties.class)
public class ElasticsearchConfig {
  @Bean(destroyMethod = "close")
  public RestHighLevelClient restHighLevelClient(ElasticsearchProperties props) {
    List<HttpHost> hosts =
        props.getHosts().stream()
            .map(URI::create)
            .map(
                uri ->
                    new HttpHost(
                        uri.getHost(),
                        uri.getPort() == -1 ? ("https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80) : uri.getPort(),
                        uri.getScheme()))
            .collect(Collectors.toList());

    RestClientBuilder builder = RestClient.builder(hosts.toArray(new HttpHost[0]));
    builder.setRequestConfigCallback(
        requestConfigBuilder ->
            requestConfigBuilder
                .setConnectTimeout(props.getRequestTimeoutMs())
                .setSocketTimeout(props.getRequestTimeoutMs()));
    return new RestHighLevelClient(builder);
  }

  @Bean
  public RequestOptions requestOptions() {
    return RequestOptions.DEFAULT;
  }
}
EOF

mkdir -p "$PROJECT_DIR/src/main/java/com/example/search/model"
cat > "$PROJECT_DIR/src/main/java/com/example/search/model/Product.java" <<'EOF'
package com.example.search.model;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

public class Product {
  @NotBlank private String id;
  @NotBlank private String name;
  private String description;
  @NotBlank private String category;
  @NotBlank private String brand;
  @NotNull private Double price;
  private Boolean inStock = true;
  private Map<String, Object> attributes = new HashMap<>();
  private Instant updatedAt = Instant.now();

  public String getId() {
    return id;
  }

  public void setId(String id) {
    this.id = id;
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

  public Double getPrice() {
    return price;
  }

  public void setPrice(Double price) {
    this.price = price;
  }

  public Boolean getInStock() {
    return inStock;
  }

  public void setInStock(Boolean inStock) {
    this.inStock = inStock;
  }

  public Map<String, Object> getAttributes() {
    return attributes;
  }

  public void setAttributes(Map<String, Object> attributes) {
    this.attributes = attributes == null ? new HashMap<>() : attributes;
  }

  public Instant getUpdatedAt() {
    return updatedAt;
  }

  public void setUpdatedAt(Instant updatedAt) {
    this.updatedAt = updatedAt;
  }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/search/model/SearchQueryLog.java" <<'EOF'
package com.example.search.model;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

public class SearchQueryLog {
  private String id;
  private Instant ts = Instant.now();
  private String query;
  private Map<String, Object> filters = new HashMap<>();
  private Integer page;
  private Integer size;
  private String userId;
  private String sessionId;
  private String userAgent;
  private String ip;

  public String getId() {
    return id;
  }

  public void setId(String id) {
    this.id = id;
  }

  public Instant getTs() {
    return ts;
  }

  public void setTs(Instant ts) {
    this.ts = ts;
  }

  public String getQuery() {
    return query;
  }

  public void setQuery(String query) {
    this.query = query;
  }

  public Map<String, Object> getFilters() {
    return filters;
  }

  public void setFilters(Map<String, Object> filters) {
    this.filters = filters == null ? new HashMap<>() : filters;
  }

  public Integer getPage() {
    return page;
  }

  public void setPage(Integer page) {
    this.page = page;
  }

  public Integer getSize() {
    return size;
  }

  public void setSize(Integer size) {
    this.size = size;
  }

  public String getUserId() {
    return userId;
  }

  public void setUserId(String userId) {
    this.userId = userId;
  }

  public String getSessionId() {
    return sessionId;
  }

  public void setSessionId(String sessionId) {
    this.sessionId = sessionId;
  }

  public String getUserAgent() {
    return userAgent;
  }

  public void setUserAgent(String userAgent) {
    this.userAgent = userAgent;
  }

  public String getIp() {
    return ip;
  }

  public void setIp(String ip) {
    this.ip = ip;
  }
}
EOF

mkdir -p "$PROJECT_DIR/src/main/java/com/example/search/dto"
cat > "$PROJECT_DIR/src/main/java/com/example/search/dto/ProductIndexResponse.java" <<'EOF'
package com.example.search.dto;

public class ProductIndexResponse {
  private String result;
  private String id;
  private long version;

  public ProductIndexResponse() {}

  public ProductIndexResponse(String result, String id, long version) {
    this.result = result;
    this.id = id;
    this.version = version;
  }

  public String getResult() {
    return result;
  }

  public void setResult(String result) {
    this.result = result;
  }

  public String getId() {
    return id;
  }

  public void setId(String id) {
    this.id = id;
  }

  public long getVersion() {
    return version;
  }

  public void setVersion(long version) {
    this.version = version;
  }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/search/dto/SearchRequestDto.java" <<'EOF'
package com.example.search.dto;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class SearchRequestDto {
  private String q;
  private List<String> categories = new ArrayList<>();
  private List<String> brands = new ArrayList<>();
  private Double minPrice;
  private Double maxPrice;
  private Boolean inStock;
  private Map<String, Object> attributes;
  private Integer page = 0;
  private Integer size = 10;

  public String getQ() {
    return q;
  }

  public void setQ(String q) {
    this.q = q;
  }

  public List<String> getCategories() {
    return categories;
  }

  public void setCategories(List<String> categories) {
    this.categories = categories == null ? new ArrayList<>() : categories;
  }

  public List<String> getBrands() {
    return brands;
  }

  public void setBrands(List<String> brands) {
    this.brands = brands == null ? new ArrayList<>() : brands;
  }

  public Double getMinPrice() {
    return minPrice;
  }

  public void setMinPrice(Double minPrice) {
    this.minPrice = minPrice;
  }

  public Double getMaxPrice() {
    return maxPrice;
  }

  public void setMaxPrice(Double maxPrice) {
    this.maxPrice = maxPrice;
  }

  public Boolean getInStock() {
    return inStock;
  }

  public void setInStock(Boolean inStock) {
    this.inStock = inStock;
  }

  public Map<String, Object> getAttributes() {
    return attributes;
  }

  public void setAttributes(Map<String, Object> attributes) {
    this.attributes = attributes;
  }

  public Integer getPage() {
    return page;
  }

  public void setPage(Integer page) {
    this.page = page == null ? 0 : Math.max(0, page);
  }

  public Integer getSize() {
    return size;
  }

  public void setSize(Integer size) {
    this.size = size == null ? 10 : Math.min(100, Math.max(1, size));
  }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/search/dto/SearchResponseDto.java" <<'EOF'
package com.example.search.dto;

import com.example.search.model.Product;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class SearchResponseDto {
  private long total;
  private int page;
  private int size;
  private List<Product> items = new ArrayList<>();
  private Map<String, List<Bucket>> facets = new HashMap<>();

  public static class Bucket {
    private String key;
    private long count;

    public Bucket() {}

    public Bucket(String key, long count) {
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

  public long getTotal() {
    return total;
  }

  public void setTotal(long total) {
    this.total = total;
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

  public List<Product> getItems() {
    return items;
  }

  public void setItems(List<Product> items) {
    this.items = items == null ? new ArrayList<>() : items;
  }

  public Map<String, List<Bucket>> getFacets() {
    return facets;
  }

  public void setFacets(Map<String, List<Bucket>> facets) {
    this.facets = facets == null ? new HashMap<>() : facets;
  }
}
EOF

mkdir -p "$PROJECT_DIR/src/main/java/com/example/search/service"
cat > "$PROJECT_DIR/src/main/java/com/example/search/service/IndexTemplates.java" <<'EOF'
package com.example.search.service;

public final class IndexTemplates {
  private IndexTemplates() {}

  public static String productsMappingJson() {
    return "{"
        + "\"settings\":{"
        + "\"number_of_shards\":%d,"
        + "\"number_of_replicas\":%d,"
        + "\"analysis\":{"
        + "\"normalizer\":{"
        + "\"lowercase_normalizer\":{"
        + "\"type\":\"custom\","
        + "\"filter\":[\"lowercase\",\"asciifolding\"]"
        + "}"
        + "}"
        + "}"
        + "},"
        + "\"mappings\":{"
        + "\"dynamic\":\"strict\","
        + "\"properties\":{"
        + "\"id\":{\"type\":\"keyword\"},"
        + "\"name\":{\"type\":\"text\",\"fields\":{\"raw\":{\"type\":\"keyword\",\"normalizer\":\"lowercase_normalizer\"}}},"
        + "\"description\":{\"type\":\"text\"},"
        + "\"category\":{\"type\":\"keyword\",\"normalizer\":\"lowercase_normalizer\"},"
        + "\"brand\":{\"type\":\"keyword\",\"normalizer\":\"lowercase_normalizer\"},"
        + "\"price\":{\"type\":\"double\"},"
        + "\"inStock\":{\"type\":\"boolean\"},"
        + "\"attributes\":{\"type\":\"flattened\"},"
        + "\"updatedAt\":{\"type\":\"date\"}"
        + "}"
        + "}"
        + "}";
  }

  public static String queriesMappingJson() {
    return "{"
        + "\"settings\":{"
        + "\"number_of_shards\":%d,"
        + "\"number_of_replicas\":%d"
        + "},"
        + "\"mappings\":{"
        + "\"dynamic\":true,"
        + "\"properties\":{"
        + "\"ts\":{\"type\":\"date\"},"
        + "\"query\":{\"type\":\"text\",\"fields\":{\"raw\":{\"type\":\"keyword\",\"ignore_above\":512}}},"
        + "\"filters\":{\"type\":\"flattened\"},"
        + "\"page\":{\"type\":\"integer\"},"
        + "\"size\":{\"type\":\"integer\"},"
        + "\"userId\":{\"type\":\"keyword\"},"
        + "\"sessionId\":{\"type\":\"keyword\"},"
        + "\"userAgent\":{\"type\":\"keyword\",\"ignore_above\":512},"
        + "\"ip\":{\"type\":\"ip\"}"
        + "}"
        + "}"
        + "}";
  }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/search/service/ElasticsearchIndexService.java" <<'EOF'
package com.example.search.service;

import com.example.search.config.ElasticsearchProperties;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.indices.CreateIndexRequest;
import org.elasticsearch.client.indices.GetIndexRequest;
import org.elasticsearch.common.xcontent.XContentType;
import org.springframework.stereotype.Service;

@Service
public class ElasticsearchIndexService {
  private final RestHighLevelClient client;
  private final RequestOptions requestOptions;
  private final ElasticsearchProperties props;

  public ElasticsearchIndexService(
      RestHighLevelClient client, RequestOptions requestOptions, ElasticsearchProperties props) {
    this.client = client;
    this.requestOptions = requestOptions;
    this.props = props;
  }

  public void ensureIndicesExist() throws IOException {
    ensureIndex(
        props.getProductsIndex(),
        String.format(IndexTemplates.productsMappingJson(), props.getShards(), props.getReplicas()));
    ensureIndex(
        props.getQueriesIndex(),
        String.format(IndexTemplates.queriesMappingJson(), props.getShards(), props.getReplicas()));
  }

  private void ensureIndex(String index, String body) throws IOException {
    boolean exists = client.indices().exists(new GetIndexRequest(index), requestOptions);
    if (exists) return;

    CreateIndexRequest req = new CreateIndexRequest(index);
    req.source(body.getBytes(StandardCharsets.UTF_8), XContentType.JSON);
    client.indices().create(req, requestOptions);
  }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/search/service/ProductSearchService.java" <<'EOF'
package com.example.search.service;

import com.example.search.config.ElasticsearchProperties;
import com.example.search.dto.SearchRequestDto;
import com.example.search.dto.SearchResponseDto;
import com.example.search.dto.SearchResponseDto.Bucket;
import com.example.search.model.Product;
import com.example.search.model.SearchQueryLog;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.index.IndexResponse;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.common.xcontent.XContentType;
import org.elasticsearch.index.query.BoolQueryBuilder;
import org.elasticsearch.index.query.MultiMatchQueryBuilder;
import org.elasticsearch.index.query.Operator;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.search.aggregations.AggregationBuilders;
import org.elasticsearch.search.aggregations.bucket.terms.Terms;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.elasticsearch.search.fetch.subphase.highlight.HighlightBuilder;
import org.elasticsearch.search.sort.SortOrder;
import org.springframework.stereotype.Service;

@Service
public class ProductSearchService {
  private final RestHighLevelClient client;
  private final RequestOptions requestOptions;
  private final ElasticsearchProperties props;
  private final ElasticsearchIndexService indexService;
  private final ObjectMapper mapper;

  public ProductSearchService(
      RestHighLevelClient client,
      RequestOptions requestOptions,
      ElasticsearchProperties props,
      ElasticsearchIndexService indexService,
      ObjectMapper mapper) {
    this.client = client;
    this.requestOptions = requestOptions;
    this.props = props;
    this.indexService = indexService;
    this.mapper = mapper;
  }

  @EventListener(ApplicationReadyEvent.class)
  public void init() throws IOException {
    indexService.ensureIndicesExist();
  }

  public IndexResponse indexProduct(Product product) throws IOException {
    if (product.getUpdatedAt() == null) product.setUpdatedAt(Instant.now());
    IndexRequest req = new IndexRequest(props.getProductsIndex());
    req.id(product.getId());
    req.source(mapper.writeValueAsString(product), XContentType.JSON);
    return client.index(req, requestOptions);
  }

  public void logQuery(SearchQueryLog log) {
    try {
      if (log.getId() == null) log.setId(UUID.randomUUID().toString());
      if (log.getTs() == null) log.setTs(Instant.now());
      IndexRequest req = new IndexRequest(props.getQueriesIndex());
      req.id(log.getId());
      req.source(mapper.writeValueAsString(log), XContentType.JSON);
      client.index(req, requestOptions);
    } catch (Exception ignored) {
    }
  }

  public SearchResponseDto search(SearchRequestDto in) throws IOException {
    int page = in.getPage() == null ? 0 : Math.max(0, in.getPage());
    int size = in.getSize() == null ? 10 : Math.min(100, Math.max(1, in.getSize()));

    BoolQueryBuilder root = QueryBuilders.boolQuery();

    String q = in.getQ();
    if (q == null || q.trim().isEmpty()) {
      root.must(QueryBuilders.matchAllQuery());
    } else {
      MultiMatchQueryBuilder mm =
          QueryBuilders.multiMatchQuery(q.trim(), "name^4", "description^1")
              .type(MultiMatchQueryBuilder.Type.BEST_FIELDS)
              .operator(Operator.AND)
              .fuzziness("AUTO");
      root.must(mm);
    }

    if (in.getCategories() != null && !in.getCategories().isEmpty()) {
      root.filter(QueryBuilders.termsQuery("category", in.getCategories()));
    }
    if (in.getBrands() != null && !in.getBrands().isEmpty()) {
      root.filter(QueryBuilders.termsQuery("brand", in.getBrands()));
    }
    if (in.getInStock() != null) {
      root.filter(QueryBuilders.termQuery("inStock", in.getInStock()));
    }
    if (in.getMinPrice() != null || in.getMaxPrice() != null) {
      var range = QueryBuilders.rangeQuery("price");
      if (in.getMinPrice() != null) range.gte(in.getMinPrice());
      if (in.getMaxPrice() != null) range.lte(in.getMaxPrice());
      root.filter(range);
    }
    if (in.getAttributes() != null && !in.getAttributes().isEmpty()) {
      for (Map.Entry<String, Object> e : in.getAttributes().entrySet()) {
        if (e.getKey() == null || e.getKey().trim().isEmpty()) continue;
        root.filter(QueryBuilders.termQuery("attributes." + e.getKey(), e.getValue()));
      }
    }

    SearchSourceBuilder ssb =
        new SearchSourceBuilder()
            .query(root)
            .from(page * size)
            .size(size)
            .trackTotalHits(true)
            .sort("_score", SortOrder.DESC)
            .sort("updatedAt", SortOrder.DESC)
            .aggregation(AggregationBuilders.terms("facet_category").field("category").size(50))
            .aggregation(AggregationBuilders.terms("facet_brand").field("brand").size(50));

    if (q != null && !q.trim().isEmpty()) {
      HighlightBuilder hb =
          new HighlightBuilder()
              .field(new HighlightBuilder.Field("name"))
              .field(new HighlightBuilder.Field("description"))
              .preTags("<em>")
              .postTags("</em>");
      ssb.highlighter(hb);
    }

    SearchRequest req = new SearchRequest(props.getProductsIndex());
    req.source(ssb);

    SearchResponse resp = client.search(req, requestOptions);

    SearchResponseDto out = new SearchResponseDto();
    out.setPage(page);
    out.setSize(size);
    out.setTotal(resp.getHits().getTotalHits() == null ? 0 : resp.getHits().getTotalHits().value);

    List<Product> items = new ArrayList<>();
    resp.getHits()
        .forEach(
            hit -> {
              try {
                Product p = mapper.readValue(hit.getSourceAsString(), Product.class);
                items.add(p);
              } catch (Exception ignored) {
              }
            });
    out.setItems(items);

    Map<String, List<Bucket>> facets = new HashMap<>();
    if (resp.getAggregations() != null) {
      Terms cat = resp.getAggregations().get("facet_category");
      Terms br = resp.getAggregations().get("facet_brand");
      facets.put("category", toBuckets(cat));
      facets.put("brand", toBuckets(br));
    }
    out.setFacets(facets);
    return out;
  }

  private List<Bucket> toBuckets(Terms terms) {
    List<Bucket> buckets = new ArrayList<>();
    if (terms == null) return buckets;
    for (Terms.Bucket b : terms.getBuckets()) {
      buckets.add(new Bucket(b.getKeyAsString(), b.getDocCount()));
    }
    return buckets;
  }
}
EOF

mkdir -p "$PROJECT_DIR/src/main/java/com/example/search/controller"
cat > "$PROJECT_DIR/src/main/java/com/example/search/controller/ProductController.java" <<'EOF'
package com.example.search.controller;

import com.example.search.dto.ProductIndexResponse;
import com.example.search.model.Product;
import com.example.search.service.ProductSearchService;
import javax.validation.Valid;
import org.elasticsearch.action.index.IndexResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/products")
public class ProductController {
  private final ProductSearchService service;

  public ProductController(ProductSearchService service) {
    this.service = service;
  }

  @PostMapping
  public ResponseEntity<ProductIndexResponse> index(@Valid @RequestBody Product product)
      throws Exception {
    IndexResponse resp = service.indexProduct(product);
    return ResponseEntity.ok(new ProductIndexResponse(resp.getResult().name(), resp.getId(), resp.getVersion()));
  }
}
EOF

cat > "$PROJECT_DIR/src/main/java/com/example/search/controller/SearchController.java" <<'EOF'
package com.example.search.controller;

import com.example.search.dto.SearchRequestDto;
import com.example.search.dto.SearchResponseDto;
import com.example.search.model.SearchQueryLog;
import com.example.search.service.ProductSearchService;
import java.util.HashMap;
import java.util.Map;
import javax.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/search")
public class SearchController {
  private final ProductSearchService service;

  public SearchController(ProductSearchService service) {
    this.service = service;
  }

  @PostMapping
  public ResponseEntity<SearchResponseDto> search(
      @RequestBody SearchRequestDto req, HttpServletRequest http) throws Exception {
    SearchResponseDto resp = service.search(req);

    SearchQueryLog log = new SearchQueryLog();
    log.setQuery(req.getQ());
    log.setPage(req.getPage());
    log.setSize(req.getSize());
    log.setUserAgent(http.getHeader("User-Agent"));
    log.setIp(clientIp(http));
    log.setSessionId(sessionId(http));
    Map<String, Object> filters = new HashMap<>();
    filters.put("categories", req.getCategories());
    filters.put("brands", req.getBrands());
    filters.put("minPrice", req.getMinPrice());
    filters.put("maxPrice", req.getMaxPrice());
    filters.put("inStock", req.getInStock());
    filters.put("attributes", req.getAttributes());
    log.setFilters(filters);
    service.logQuery(log);

    return ResponseEntity.ok(resp);
  }

  private static String clientIp(HttpServletRequest req) {
    String xff = req.getHeader("X-Forwarded-For");
    if (xff != null && !xff.isBlank()) {
      return xff.split(",")[0].trim();
    }
    return req.getRemoteAddr();
  }

  private static String sessionId(HttpServletRequest req) {
    try {
      return req.getSession(false) == null ? null : req.getSession(false).getId();
    } catch (Exception e) {
      return null;
    }
  }
}
EOF

mkdir -p "$PROJECT_DIR/src/main/java/com/example/search/controller"
cat > "$PROJECT_DIR/src/main/java/com/example/search/controller/HealthController.java" <<'EOF'
package com.example.search.controller;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  @GetMapping("/")
  public Map<String, Object> root() {
    return Map.of("status", "ok");
  }
}
EOF

cat > "$PROJECT_DIR/README.txt" <<'EOF'
Run Elasticsearch (7.x) locally on http://localhost:9200

Build:
  mvn -q -DskipTests package

Run:
  mvn spring-boot:run

Index a product:
  curl -s http://localhost:8080/products -H 'Content-Type: application/json' -d '{
    "id":"sku-123",
    "name":"Running Shoes",
    "description":"Lightweight running shoes for daily training",
    "category":"shoes",
    "brand":"acme",
    "price":79.99,
    "inStock":true,
    "attributes":{"color":"blue","gender":"men","size":"10"}
  }'

Search with facets:
  curl -s http://localhost:8080/search -H 'Content-Type: application/json' -d '{
    "q":"running shoes",
    "categories":["shoes"],
    "brands":["acme"],
    "minPrice":50,
    "maxPrice":150,
    "inStock":true,
    "page":0,
    "size":10
  }'
EOF

echo "Created project at: $PROJECT_DIR"
echo "Next:"
echo "  cd \"$PROJECT_DIR\" && mvn spring-boot:run"
