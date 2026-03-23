package com.example.profileupload.config;

import java.nio.file.Path;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@EnableConfigurationProperties(UploadProperties.class)
public class WebConfig implements WebMvcConfigurer {

    private final UploadProperties uploadProperties;

    public WebConfig(UploadProperties uploadProperties) {
        this.uploadProperties = uploadProperties;
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path uploadPath = Path.of(uploadProperties.getPublicDir()).toAbsolutePath().normalize();
        String location = "file:" + uploadPath + "/";
        registry.addResourceHandler(uploadProperties.getPublicUrlPrefix() + "/**")
                .addResourceLocations(location);
    }
}
