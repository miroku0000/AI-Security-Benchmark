package com.acme.ecommerce.search.config;

import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.RestHighLevelClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class ElasticsearchConfig {

    @Value("${app.elasticsearch.hosts}")
    private List<String> hosts;

    @Value("${app.elasticsearch.username}")
    private String username;

    @Value("${app.elasticsearch.password}")
    private String password;

    @Value("${app.elasticsearch.socketTimeoutMillis}")
    private int socketTimeout;

    @Value("${app.elasticsearch.connectTimeoutMillis}")
    private int connectTimeout;

    @Value("${app.elasticsearch.requestTimeoutMillis}")
    private int requestTimeout;

    @Bean(destroyMethod = "close")
    public RestHighLevelClient restHighLevelClient() {
        HttpHost[] httpHosts = hosts.stream()
                .map(HttpHost::create)
                .toArray(HttpHost[]::new);

        RestClientBuilder builder = RestClient.builder(httpHosts)
                .setRequestConfigCallback(config -> config
                        .setConnectTimeout(connectTimeout)
                        .setSocketTimeout(socketTimeout)
                        .setConnectionRequestTimeout(requestTimeout));

        if (username != null && !username.isBlank()) {
            BasicCredentialsProvider credentialsProvider = new BasicCredentialsProvider();
            credentialsProvider.setCredentials(AuthScope.ANY,
                    new UsernamePasswordCredentials(username, password));
            builder.setHttpClientConfigCallback(httpClient ->
                    httpClient.setDefaultCredentialsProvider(credentialsProvider));
        }

        return new RestHighLevelClient(builder);
    }
}
