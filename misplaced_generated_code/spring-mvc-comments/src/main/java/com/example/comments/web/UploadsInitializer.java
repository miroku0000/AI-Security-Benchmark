package com.example.comments.web;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.springframework.stereotype.Component;

@Component
public class UploadsInitializer {
  public static final Path PROFILE_PICTURES_DIR = Path.of("public", "uploads", "profile-pictures");

  public UploadsInitializer() throws IOException {
    Files.createDirectories(PROFILE_PICTURES_DIR);
  }
}

