package com.acme.ecommerce.search.controller;

import com.acme.ecommerce.search.dto.ProductSearchRequest;
import com.acme.ecommerce.search.dto.SearchResponse;
import com.acme.ecommerce.search.model.Product;
import com.acme.ecommerce.search.service.ProductIndexService;
import com.acme.ecommerce.search.service.ProductSearchService;
import com.acme.ecommerce.search.service.SearchQueryService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ProductController {

    private final ProductIndexService indexService;
    private final ProductSearchService searchService;
    private final SearchQueryService searchQueryService;

    public ProductController(ProductIndexService indexService,
                             ProductSearchService searchService,
                             SearchQueryService searchQueryService) {
        this.indexService = indexService;
        this.searchService = searchService;
        this.searchQueryService = searchQueryService;
    }

    @PostMapping("/products")
    public ResponseEntity<Product> createProduct(@RequestBody Product product) throws IOException {
        Product indexed = indexService.indexProduct(product);
        return ResponseEntity.status(HttpStatus.CREATED).body(indexed);
    }

    @PostMapping("/products/bulk")
    public ResponseEntity<Map<String, Object>> bulkIndex(@RequestBody List<Product> products) throws IOException {
        var bulkResponse = indexService.bulkIndex(products);
        return ResponseEntity.ok(Map.of(
                "indexed", products.size(),
                "hasFailures", bulkResponse.hasFailures(),
                "tookMs", bulkResponse.getTook().millis()
        ));
    }

    @GetMapping("/products/{id}")
    public ResponseEntity<Product> getProduct(@PathVariable String id) throws IOException {
        return indexService.getProduct(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/products/{id}")
    public ResponseEntity<Void> deleteProduct(@PathVariable String id) throws IOException {
        boolean deleted = indexService.deleteProduct(id);
        return deleted ? ResponseEntity.noContent().build() : ResponseEntity.notFound().build();
    }

    @PostMapping("/products/search")
    public ResponseEntity<SearchResponse> search(@RequestBody ProductSearchRequest request) throws IOException {
        SearchResponse response = searchService.search(request);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/analytics/top-searches")
    public ResponseEntity<List<String>> topSearches(
            @RequestParam(defaultValue = "10") int limit) throws IOException {
        return ResponseEntity.ok(searchQueryService.getTopSearchTerms(limit));
    }

    @GetMapping("/analytics/zero-result-queries")
    public ResponseEntity<List<String>> zeroResultQueries(
            @RequestParam(defaultValue = "10") int limit) throws IOException {
        return ResponseEntity.ok(searchQueryService.getZeroResultQueries(limit));
    }
}
