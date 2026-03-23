package com.example.profileupload;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.nio.file.Path;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Value("${app.upload.public-dir}")
    private String publicUploadDir;

    @Value("${app.upload.url-prefix:/public/uploads}")
    private String urlPrefix;

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        String location = Path.of(publicUploadDir).toAbsolutePath().normalize().toUri().toString();
        if (!location.endsWith("/")) {
            location = location + "/";
        }
        String pattern = urlPrefix.startsWith("/") ? urlPrefix : "/" + urlPrefix;
        if (!pattern.endsWith("/")) {
            pattern = pattern + "/";
        }
        pattern = pattern + "**";
        registry.addResourceHandler(pattern).addResourceLocations(location);
    }
}
