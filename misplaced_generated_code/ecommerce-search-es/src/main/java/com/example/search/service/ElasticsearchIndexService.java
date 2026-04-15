package com.example.search.service;

import com.example.search.config.ElasticsearchProperties;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.indices.CreateIndexRequest;
import org.elasticsearch.client.indices.GetIndexRequest;
import org.elasticsearch.common.xcontent.XContentType;
import org.springframework.stereotype.Service;

@Service
public class ElasticsearchIndexService {
  private final RestHighLevelClient client;
  private final RequestOptions requestOptions;
  private final ElasticsearchProperties props;

  public ElasticsearchIndexService(
      RestHighLevelClient client, RequestOptions requestOptions, ElasticsearchProperties props) {
    this.client = client;
    this.requestOptions = requestOptions;
    this.props = props;
  }

  public void ensureIndicesExist() throws IOException {
    ensureIndex(
        props.getProductsIndex(),
        String.format(IndexTemplates.productsMappingJson(), props.getShards(), props.getReplicas()));
    ensureIndex(
        props.getQueriesIndex(),
        String.format(IndexTemplates.queriesMappingJson(), props.getShards(), props.getReplicas()));
  }

  private void ensureIndex(String index, String body) throws IOException {
    boolean exists = client.indices().exists(new GetIndexRequest(index), requestOptions);
    if (exists) return;

    CreateIndexRequest req = new CreateIndexRequest(index);
    req.source(body.getBytes(StandardCharsets.UTF_8), XContentType.JSON);
    client.indices().create(req, requestOptions);
  }
}
