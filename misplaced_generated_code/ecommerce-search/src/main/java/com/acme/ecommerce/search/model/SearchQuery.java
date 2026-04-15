package com.acme.ecommerce.search.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.time.Instant;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class SearchQuery {

    private String id;
    private String queryText;
    private String customerId;
    private String sessionId;
    private Map<String, String> appliedFilters;
    private int totalResults;
    private int page;
    private int pageSize;
    private long responseTimeMs;
    private Instant timestamp;

    public SearchQuery() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getQueryText() { return queryText; }
    public void setQueryText(String queryText) { this.queryText = queryText; }

    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public Map<String, String> getAppliedFilters() { return appliedFilters; }
    public void setAppliedFilters(Map<String, String> appliedFilters) { this.appliedFilters = appliedFilters; }

    public int getTotalResults() { return totalResults; }
    public void setTotalResults(int totalResults) { this.totalResults = totalResults; }

    public int getPage() { return page; }
    public void setPage(int page) { this.page = page; }

    public int getPageSize() { return pageSize; }
    public void setPageSize(int pageSize) { this.pageSize = pageSize; }

    public long getResponseTimeMs() { return responseTimeMs; }
    public void setResponseTimeMs(long responseTimeMs) { this.responseTimeMs = responseTimeMs; }

    public Instant getTimestamp() { return timestamp; }
    public void setTimestamp(Instant timestamp) { this.timestamp = timestamp; }
}
