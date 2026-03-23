package com.example.profile;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.profile-picture")
public class ProfilePictureProperties {

    private String publicDirectory = "public/profile-pictures";

    private String urlPath = "/profile-pictures";

    public String getPublicDirectory() {
        return publicDirectory;
    }

    public void setPublicDirectory(String publicDirectory) {
        this.publicDirectory = publicDirectory;
    }

    public String getUrlPath() {
        return urlPath;
    }

    public void setUrlPath(String urlPath) {
        this.urlPath = urlPath;
    }
}
