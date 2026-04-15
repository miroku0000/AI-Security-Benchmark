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
