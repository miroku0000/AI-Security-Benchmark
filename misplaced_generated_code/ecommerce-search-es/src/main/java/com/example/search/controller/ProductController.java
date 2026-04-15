package com.example.search.controller;

import com.example.search.dto.ProductIndexResponse;
import com.example.search.model.Product;
import com.example.search.service.ProductSearchService;
import javax.validation.Valid;
import org.elasticsearch.action.index.IndexResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
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
    return ResponseEntity.ok(
        new ProductIndexResponse(resp.getResult().name(), resp.getId(), resp.getVersion()));
  }

  @PutMapping("/{id}")
  public ResponseEntity<ProductIndexResponse> upsert(
      @PathVariable("id") String id, @Valid @RequestBody Product product) throws Exception {
    product.setId(id);
    IndexResponse resp = service.indexProduct(product);
    return ResponseEntity.ok(
        new ProductIndexResponse(resp.getResult().name(), resp.getId(), resp.getVersion()));
  }
}
