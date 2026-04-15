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
