package com.example.profileupload.controller;

import java.io.IOException;
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
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import com.example.profileupload.config.UploadProperties;

@RestController
@RequestMapping("/api/profile")
public class ProfilePictureController {

    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            MediaType.IMAGE_JPEG_VALUE,
            MediaType.IMAGE_PNG_VALUE,
            "image/gif",
            "image/webp",
            "image/bmp"
    );

    private static final Map<String, String> EXTENSION_BY_CONTENT_TYPE = Map.of(
            MediaType.IMAGE_JPEG_VALUE, ".jpg",
            MediaType.IMAGE_PNG_VALUE, ".png",
            "image/gif", ".gif",
            "image/webp", ".webp",
            "image/bmp", ".bmp"
    );

    private final UploadProperties uploadProperties;

    public ProfilePictureController(UploadProperties uploadProperties) {
        this.uploadProperties = uploadProperties;
    }

    @PostMapping(value = "/picture", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<Map<String, String>> uploadProfilePicture(
            @RequestPart("file") MultipartFile file) throws IOException {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "File is required"));
        }
        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_CONTENT_TYPES.contains(contentType.toLowerCase(Locale.ROOT))) {
            return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
                    .body(Map.of("error", "Unsupported image type"));
        }
        String ext = EXTENSION_BY_CONTENT_TYPE.get(contentType.toLowerCase(Locale.ROOT));
        if (ext == null) {
            ext = guessExtension(file.getOriginalFilename());
            if (ext == null) {
                return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
                        .body(Map.of("error", "Unsupported image type"));
            }
        }
        Path dir = Path.of(uploadProperties.getPublicDir()).toAbsolutePath().normalize();
        Files.createDirectories(dir);
        String filename = UUID.randomUUID() + ext;
        Path target = dir.resolve(filename).normalize();
        if (!target.startsWith(dir)) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "Invalid path"));
        }
        Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
        String baseUrl = ServletUriComponentsBuilder.fromCurrentContextPath().build().toUriString();
        String prefix = uploadProperties.getPublicUrlPrefix();
        if (!prefix.startsWith("/")) {
            prefix = "/" + prefix;
        }
        if (prefix.endsWith("/")) {
            prefix = prefix.substring(0, prefix.length() - 1);
        }
        String url = baseUrl + prefix + "/" + filename;
        return ResponseEntity.ok(Map.of("url", url));
    }

    private static String guessExtension(String originalFilename) {
        if (originalFilename == null || !originalFilename.contains(".")) {
            return null;
        }
        String lower = originalFilename.toLowerCase(Locale.ROOT);
        if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
            return ".jpg";
        }
        if (lower.endsWith(".png")) {
            return ".png";
        }
        if (lower.endsWith(".gif")) {
            return ".gif";
        }
        if (lower.endsWith(".webp")) {
            return ".webp";
        }
        if (lower.endsWith(".bmp")) {
            return ".bmp";
        }
        return null;
    }
}
