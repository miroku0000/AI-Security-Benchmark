package com.example.profile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
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
@RequestMapping("/api/profile")
public class ProfilePictureController {

    private static final Set<String> ALLOWED_TYPES = Set.of(
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/bmp",
            "image/svg+xml",
            "image/x-icon",
            "image/vnd.microsoft.icon"
    );

    private final ProfilePictureProperties properties;

    public ProfilePictureController(ProfilePictureProperties properties) {
        this.properties = properties;
    }

    @PostMapping(value = "/picture", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<Map<String, String>> upload(@RequestParam("file") MultipartFile file)
            throws IOException {
        if (file == null || file.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "file is required"));
        }
        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_TYPES.contains(contentType.toLowerCase(Locale.ROOT))) {
            return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
                    .body(Map.of("error", "unsupported image type"));
        }

        String ext = extensionForContentType(contentType, file.getOriginalFilename());
        if (ext == null) {
            return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
                    .body(Map.of("error", "could not determine file extension"));
        }

        Path baseDir = Path.of(properties.getPublicDirectory()).toAbsolutePath().normalize();
        Files.createDirectories(baseDir);

        String filename = UUID.randomUUID() + ext;
        Path target = baseDir.resolve(filename).normalize();
        if (!target.startsWith(baseDir)) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "invalid path"));
        }

        Files.copy(file.getInputStream(), target);

        String publicUrl = ServletUriComponentsBuilder.fromCurrentContextPath()
                .path(properties.getUrlPath())
                .path("/")
                .path(filename)
                .toUriString();

        return ResponseEntity.ok(Map.of("url", publicUrl));
    }

    private static String extensionForContentType(String contentType, String originalName) {
        String ct = contentType.toLowerCase(Locale.ROOT);
        return switch (ct) {
            case "image/jpeg" -> ".jpg";
            case "image/png" -> ".png";
            case "image/gif" -> ".gif";
            case "image/webp" -> ".webp";
            case "image/bmp" -> ".bmp";
            case "image/svg+xml" -> ".svg";
            case "image/x-icon", "image/vnd.microsoft.icon" -> ".ico";
            default -> guessFromOriginalFilename(originalName);
        };
    }

    private static String guessFromOriginalFilename(String originalName) {
        if (!StringUtils.hasText(originalName)) {
            return null;
        }
        String lower = originalName.toLowerCase(Locale.ROOT);
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
        if (lower.endsWith(".svg")) {
            return ".svg";
        }
        if (lower.endsWith(".ico")) {
            return ".ico";
        }
        return null;
    }
}
