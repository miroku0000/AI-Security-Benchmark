package com.example.ecommerce.search.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.HashMap;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CustomerSearchQuery {

    private String id;
    private String queryText;
    private Map<String, String> activeFilters = new HashMap<>();
    private String sessionId;
    private long timestampEpochMillis;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getQueryText() {
        return queryText;
    }

    public void setQueryText(String queryText) {
        this.queryText = queryText;
    }

    public Map<String, String> getActiveFilters() {
        return activeFilters;
    }

    public void setActiveFilters(Map<String, String> activeFilters) {
        this.activeFilters = activeFilters != null ? activeFilters : new HashMap<>();
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public long getTimestampEpochMillis() {
        return timestampEpochMillis;
    }

    public void setTimestampEpochMillis(long timestampEpochMillis) {
        this.timestampEpochMillis = timestampEpochMillis;
    }
}
