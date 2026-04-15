package com.example.ecommerce.search.config;

import org.apache.http.HttpHost;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.RestHighLevelClient;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties({ElasticsearchProperties.class, IndexNamesProperties.class})
public class ElasticsearchConfig {

    @Bean(destroyMethod = "close")
    public RestHighLevelClient restHighLevelClient(ElasticsearchProperties props) {
        RestClientBuilder builder = RestClient.builder(
                new HttpHost(props.getHost(), props.getPort(), props.getScheme()));
        return new RestHighLevelClient(builder);
    }
}
