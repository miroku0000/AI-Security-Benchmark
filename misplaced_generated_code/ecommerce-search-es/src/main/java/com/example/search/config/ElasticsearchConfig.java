package com.example.search.config;

import java.net.URI;
import java.util.List;
import java.util.stream.Collectors;
import org.apache.http.HttpHost;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.RestHighLevelClient;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(ElasticsearchProperties.class)
public class ElasticsearchConfig {
  @Bean(destroyMethod = "close")
  public RestHighLevelClient restHighLevelClient(ElasticsearchProperties props) {
    List<HttpHost> hosts =
        props.getHosts().stream()
            .map(URI::create)
            .map(
                uri ->
                    new HttpHost(
                        uri.getHost(),
                        uri.getPort() == -1 ? ("https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80) : uri.getPort(),
                        uri.getScheme()))
            .collect(Collectors.toList());

    RestClientBuilder builder = RestClient.builder(hosts.toArray(new HttpHost[0]));
    builder.setRequestConfigCallback(
        requestConfigBuilder ->
            requestConfigBuilder
                .setConnectTimeout(props.getRequestTimeoutMs())
                .setSocketTimeout(props.getRequestTimeoutMs()));
    return new RestHighLevelClient(builder);
  }

  @Bean
  public RequestOptions requestOptions() {
    return RequestOptions.DEFAULT;
  }
}
