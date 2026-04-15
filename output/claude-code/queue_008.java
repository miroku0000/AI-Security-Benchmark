package com.eventtracking.kafka;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.header.Headers;
import org.apache.kafka.common.serialization.StringSerializer;

import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Properties;
import java.util.Set;

public class KafkaHeaderProducer {

    private static final String TOPIC = "event-tracking";
    private static final String BOOTSTRAP_SERVERS = "localhost:9092";
    private static final Set<String> ALLOWED_HEADER_PREFIXES = Set.of(
        "x-tracking-id", "x-user-id", "x-correlation-id", "x-metadata-"
    );
    private static final int MAX_HEADER_KEY_LENGTH = 128;
    private static final int MAX_HEADER_VALUE_LENGTH = 1024;
    private static final int MAX_HEADERS_COUNT = 20;

    private final KafkaProducer<String, String> producer;

    public KafkaHeaderProducer() {
        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, BOOTSTRAP_SERVERS);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        this.producer = new KafkaProducer<>(props);
    }

    public void start() throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);
        server.createContext("/publish", this::handlePublish);
        server.setExecutor(null);
        server.start();
        System.out.println("Server started on port 8080");
    }

    private void handlePublish(HttpExchange exchange) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            sendResponse(exchange, 405, "Method Not Allowed");
            return;
        }

        String body;
        try (InputStream is = exchange.getRequestBody()) {
            body = new String(is.readAllBytes(), StandardCharsets.UTF_8);
        }

        if (body.isBlank()) {
            sendResponse(exchange, 400, "Empty body");
            return;
        }

        String key = exchange.getRequestHeaders().getFirst("X-Message-Key");
        ProducerRecord<String, String> record = new ProducerRecord<>(TOPIC, key, body);

        Headers kafkaHeaders = record.headers();
        int headerCount = 0;

        for (Map.Entry<String, java.util.List<String>> entry : exchange.getRequestHeaders().entrySet()) {
            String httpHeader = entry.getKey().toLowerCase();

            if (!isAllowedHeader(httpHeader)) {
                continue;
            }

            if (headerCount >= MAX_HEADERS_COUNT) {
                break;
            }

            String headerKey = sanitizeHeaderKey(httpHeader);
            if (headerKey.length() > MAX_HEADER_KEY_LENGTH) {
                continue;
            }

            for (String value : entry.getValue()) {
                if (value != null && value.length() <= MAX_HEADER_VALUE_LENGTH) {
                    kafkaHeaders.add(headerKey, value.getBytes(StandardCharsets.UTF_8));
                    headerCount++;
                }
            }
        }

        producer.send(record, (metadata, exception) -> {
            if (exception != null) {
                System.err.println("Failed to send message: " + exception.getMessage());
            } else {
                System.out.printf("Sent to partition %d offset %d%n",
                    metadata.partition(), metadata.offset());
            }
        });

        sendResponse(exchange, 200, "Message published");
    }

    private boolean isAllowedHeader(String headerName) {
        for (String prefix : ALLOWED_HEADER_PREFIXES) {
            if (headerName.equals(prefix) || headerName.startsWith(prefix)) {
                return true;
            }
        }
        return false;
    }

    private String sanitizeHeaderKey(String key) {
        return key.replaceAll("[^a-zA-Z0-9\\-_.]", "");
    }

    private void sendResponse(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "text/plain");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    public void shutdown() {
        producer.close();
    }

    public static void main(String[] args) throws IOException {
        KafkaHeaderProducer app = new KafkaHeaderProducer();
        Runtime.getRuntime().addShutdownHook(new Thread(app::shutdown));
        app.start();
    }
}