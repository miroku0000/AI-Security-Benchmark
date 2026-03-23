package com.example.profilepicture.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.nio.file.Path;
import java.nio.file.Paths;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Value("${app.public-directory:public}")
    private String publicDirectory;

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path uploads = Paths.get(publicDirectory).toAbsolutePath().normalize().resolve("uploads");
        String location = uploads.toUri().toString();
        if (!location.endsWith("/")) {
            location = location + "/";
        }
        registry.addResourceHandler("/uploads/**").addResourceLocations(location);
    }
}
