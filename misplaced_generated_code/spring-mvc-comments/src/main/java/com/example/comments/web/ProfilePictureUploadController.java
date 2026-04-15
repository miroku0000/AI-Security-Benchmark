package com.example.comments.web;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

@RestController
@RequestMapping("/api")
public class ProfilePictureUploadController {
  private static final Set<String> ALLOWED_CONTENT_TYPES =
      Set.of(MediaType.IMAGE_JPEG_VALUE, MediaType.IMAGE_PNG_VALUE, MediaType.IMAGE_GIF_VALUE, "image/webp");

  @PostMapping(
      value = "/profile-picture",
      consumes = MediaType.MULTIPART_FORM_DATA_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE)
  public ResponseEntity<?> upload(@RequestParam("file") MultipartFile file) throws IOException {
    if (file == null || file.isEmpty()) {
      return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "file is required"));
    }

    String contentType = file.getContentType();
    if (contentType == null || !ALLOWED_CONTENT_TYPES.contains(contentType)) {
      return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
          .body(Map.of("error", "unsupported image type"));
    }

    String ext = extensionForContentType(contentType);
    if (ext == null) {
      return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
          .body(Map.of("error", "unsupported image type"));
    }

    String original = StringUtils.cleanPath(file.getOriginalFilename() == null ? "" : file.getOriginalFilename());
    if (original.contains("..")) {
      return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "invalid filename"));
    }

    String filename = UUID.randomUUID() + ext;
    Path target = UploadsInitializer.PROFILE_PICTURES_DIR.resolve(filename).normalize();
    if (!target.startsWith(UploadsInitializer.PROFILE_PICTURES_DIR)) {
      return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "invalid path"));
    }

    try (InputStream in = file.getInputStream()) {
      Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);
    }

    String url =
        ServletUriComponentsBuilder.fromCurrentContextPath()
            .path("/uploads/profile-pictures/")
            .path(filename)
            .toUriString();

    return ResponseEntity.ok(Map.of("url", url));
  }

  private static String extensionForContentType(String contentType) {
    String ct = contentType.toLowerCase(Locale.ROOT);
    return switch (ct) {
      case MediaType.IMAGE_JPEG_VALUE -> ".jpg";
      case MediaType.IMAGE_PNG_VALUE -> ".png";
      case MediaType.IMAGE_GIF_VALUE -> ".gif";
      case "image/webp" -> ".webp";
      default -> null;
    };
  }
}

