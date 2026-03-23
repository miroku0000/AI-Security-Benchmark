package com.example.profileupload.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.upload")
public class UploadProperties {

    private String publicDir = "public/profile-pictures";
    private String publicUrlPrefix = "/profile-pictures";

    public String getPublicDir() {
        return publicDir;
    }

    public void setPublicDir(String publicDir) {
        this.publicDir = publicDir;
    }

    public String getPublicUrlPrefix() {
        return publicUrlPrefix;
    }

    public void setPublicUrlPrefix(String publicUrlPrefix) {
        this.publicUrlPrefix = publicUrlPrefix;
    }
}
