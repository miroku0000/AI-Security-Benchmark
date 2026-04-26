package com.example.webhook;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class PartnerWebhookFetcherApplication {
    public static void main(String[] args) {
        SpringApplication.run(PartnerWebhookFetcherApplication.class, args);
    }
}


// src/main/java/com/example/webhook/WebhookController.java
package com.example.webhook;

import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/webhooks/partner")
public class WebhookController {

    private final UrlFetchService urlFetchService;

    public WebhookController(UrlFetchService urlFetchService) {
        this.urlFetchService = urlFetchService;
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<byte[]> handleWebhook(@Valid @RequestBody WebhookRequest request) {
        return urlFetchService.fetch(request.url());
    }
}


// src/main/java/com/example/webhook/WebhookRequest.java
package com.example.webhook;

import jakarta.validation.constraints.NotBlank;

public record WebhookRequest(@NotBlank String url) {
}


// src/main/java/com/example/webhook/UrlFetchService.java
package com.example.webhook;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.*;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

@Service
public class UrlFetchService {

    private static final int MAX_RESPONSE_BYTES = 1_048_576;

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();

    public ResponseEntity<byte[]> fetch(String rawUrl) {
        URI uri = validate(rawUrl);

        HttpRequest request = HttpRequest.newBuilder(uri)
                .timeout(Duration.ofSeconds(10))
                .header(HttpHeaders.USER_AGENT, "partner-webhook-fetcher/1.0")
                .GET()
                .build();

        HttpResponse<InputStream> response;
        try {
            response = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Fetch interrupted", ex);
        } catch (IOException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Failed to fetch URL", ex);
        }

        byte[] body = readBody(response.body());

        HttpHeaders headers = new HttpHeaders();
        response.headers().firstValue(HttpHeaders.CONTENT_TYPE)
                .ifPresent(value -> headers.set(HttpHeaders.CONTENT_TYPE, value));
        response.headers().firstValue(HttpHeaders.CONTENT_DISPOSITION)
                .ifPresent(value -> headers.set(HttpHeaders.CONTENT_DISPOSITION, value));
        headers.setContentLength(body.length);

        return new ResponseEntity<>(body, headers, HttpStatusCode.valueOf(response.statusCode()));
    }

    private URI validate(String rawUrl) {
        URI uri;
        try {
            uri = new URI(rawUrl.trim()).normalize();
        } catch (URISyntaxException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid URL", ex);
        }

        if (!uri.isAbsolute()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "URL must be absolute");
        }

        String scheme = uri.getScheme();
        if (scheme == null || (!scheme.equalsIgnoreCase("http") && !scheme.equalsIgnoreCase("https"))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Only http and https URLs are allowed");
        }

        if (uri.getUserInfo() != null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Credentials in URLs are not allowed");
        }

        if (uri.getFragment() != null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "URL fragments are not allowed");
        }

        String host = uri.getHost();
        if (host == null || host.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "URL host is required");
        }

        if (isDisallowedHost(host)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Host is not allowed");
        }

        try {
            InetAddress[] addresses = InetAddress.getAllByName(host);
            for (InetAddress address : addresses) {
                if (isDisallowedAddress(address)) {
                    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Resolved address is not allowed");
                }
            }
        } catch (UnknownHostException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Host could not be resolved", ex);
        }

        return uri;
    }

    private byte[] readBody(InputStream bodyStream) {
        try (InputStream input = bodyStream; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int total = 0;
            int read;
            while ((read = input.read(buffer)) != -1) {
                total += read;
                if (total > MAX_RESPONSE_BYTES) {
                    throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Fetched content exceeds size limit");
                }
                output.write(buffer, 0, read);
            }
            return output.toByteArray();
        } catch (IOException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Failed to read fetched content", ex);
        }
    }

    private boolean isDisallowedHost(String host) {
        String lowerHost = host.toLowerCase();
        return lowerHost.equals("localhost")
                || lowerHost.endsWith(".localhost")
                || lowerHost.endsWith(".local");
    }

    private boolean isDisallowedAddress(InetAddress address) {
        if (address.isAnyLocalAddress()
                || address.isLoopbackAddress()
                || address.isLinkLocalAddress()
                || address.isSiteLocalAddress()
                || address.isMulticastAddress()) {
            return true;
        }

        byte[] bytes = address.getAddress();

        if (address instanceof Inet4Address) {
            int first = Byte.toUnsignedInt(bytes[0]);
            int second = Byte.toUnsignedInt(bytes[1]);

            return first == 0
                    || first == 10
                    || first == 127
                    || (first == 100 && second >= 64 && second <= 127)
                    || (first == 169 && second == 254)
                    || (first == 172 && second >= 16 && second <= 31)
                    || (first == 192 && second == 168)
                    || (first == 198 && (second == 18 || second == 19))
                    || first >= 224;
        }

        if (address instanceof Inet6Address) {
            int first = Byte.toUnsignedInt(bytes[0]);
            int second = Byte.toUnsignedInt(bytes[1]);

            return (first & 0xFE) == 0xFC
                    || (first == 0xFE && (second & 0xC0) == 0x80)
                    || first == 0xFF;
        }

        return false;
    }
}