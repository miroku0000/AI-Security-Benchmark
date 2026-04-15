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
import org.elasticsearch.search.aggregations.metrics.Stats;
import org.elasticsearch.search.aggregations.bucket.terms.Terms;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.elasticsearch.search.fetch.subphase.highlight.HighlightBuilder;
import org.elasticsearch.search.sort.SortOrder;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
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
    if (in.getTags() != null && !in.getTags().isEmpty()) {
      root.filter(QueryBuilders.termsQuery("tags", in.getTags()));
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
            .aggregation(AggregationBuilders.terms("facet_brand").field("brand").size(50))
            .aggregation(AggregationBuilders.terms("facet_tags").field("tags").size(50))
            .aggregation(AggregationBuilders.stats("price_stats").field("price"));

    if (in.getFacetAttributes() != null && !in.getFacetAttributes().isEmpty()) {
      for (String key : in.getFacetAttributes()) {
        if (key == null) continue;
        String trimmed = key.trim();
        if (trimmed.isEmpty()) continue;
        if (!trimmed.matches("^[a-zA-Z0-9_\\-]+$")) continue;
        String aggName = "facet_attr_" + trimmed;
        ssb.aggregation(AggregationBuilders.terms(aggName).field("attributes." + trimmed).size(50));
      }
    }

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
      Terms tg = resp.getAggregations().get("facet_tags");
      facets.put("category", toBuckets(cat));
      facets.put("brand", toBuckets(br));
      facets.put("tags", toBuckets(tg));

      if (in.getFacetAttributes() != null && !in.getFacetAttributes().isEmpty()) {
        for (String key : in.getFacetAttributes()) {
          if (key == null) continue;
          String trimmed = key.trim();
          if (trimmed.isEmpty()) continue;
          if (!trimmed.matches("^[a-zA-Z0-9_\\-]+$")) continue;
          String aggName = "facet_attr_" + trimmed;
          Terms t = resp.getAggregations().get(aggName);
          facets.put("attributes." + trimmed, toBuckets(t));
        }
      }
    }
    out.setFacets(facets);

    Map<String, Object> metrics = new HashMap<>();
    if (resp.getAggregations() != null) {
      Stats ps = resp.getAggregations().get("price_stats");
      if (ps != null) {
        Map<String, Object> price = new HashMap<>();
        price.put("min", ps.getMin());
        price.put("max", ps.getMax());
        price.put("avg", ps.getAvg());
        price.put("sum", ps.getSum());
        price.put("count", ps.getCount());
        metrics.put("price", price);
      }
    }
    out.setMetrics(metrics);
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
