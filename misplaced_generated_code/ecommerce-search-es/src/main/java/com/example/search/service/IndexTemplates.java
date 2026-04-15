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
        + "\"tags\":{\"type\":\"keyword\",\"normalizer\":\"lowercase_normalizer\"},"
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
