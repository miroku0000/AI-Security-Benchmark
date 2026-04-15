package com.example.ecommerce.search.web;

import com.example.ecommerce.search.dto.SearchRequestDto;
import com.example.ecommerce.search.dto.SearchResponseDto;
import com.example.ecommerce.search.model.Product;
import com.example.ecommerce.search.service.ProductSearchService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class SearchController {

    private final ProductSearchService productSearchService;

    public SearchController(ProductSearchService productSearchService) {
        this.productSearchService = productSearchService;
    }

    @PostMapping("/products")
    @ResponseStatus(HttpStatus.CREATED)
    public Product indexProduct(@Valid @RequestBody Product product) {
        return productSearchService.indexProduct(product);
    }

    @PostMapping("/search")
    public SearchResponseDto search(@Valid @RequestBody SearchRequestDto request) {
        return productSearchService.search(request);
    }
}
