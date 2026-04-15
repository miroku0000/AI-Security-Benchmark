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
    filters.put("tags", req.getTags());
    filters.put("attributes", req.getAttributes());
    filters.put("facetAttributes", req.getFacetAttributes());
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
