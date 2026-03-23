package com.example.profile;

import java.nio.file.Path;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@EnableConfigurationProperties(ProfilePictureProperties.class)
public class WebConfig implements WebMvcConfigurer {

    private final ProfilePictureProperties properties;

    public WebConfig(ProfilePictureProperties properties) {
        this.properties = properties;
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path dir = Path.of(properties.getPublicDirectory()).toAbsolutePath().normalize();
        String location = "file:" + dir.toString();
        if (!location.endsWith("/")) {
            location = location + "/";
        }
        registry.addResourceHandler(properties.getUrlPath() + "/**")
                .addResourceLocations(location);
    }
}
