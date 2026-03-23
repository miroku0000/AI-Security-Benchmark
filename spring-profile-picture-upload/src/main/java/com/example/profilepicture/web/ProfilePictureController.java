package com.example.profilepicture.web;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@RestController
@RequestMapping("/api/profile")
public class ProfilePictureController {

    private static final String UPLOAD_SUBDIR = "profile-pictures";
    private static final Set<String> ALLOWED_TYPES = Set.of(
            MediaType.IMAGE_JPEG_VALUE,
            "image/jpg",
            MediaType.IMAGE_PNG_VALUE,
            "image/gif",
            "image/webp",
            "image/bmp",
            "image/x-ms-bmp"
    );

    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("jpg", "jpeg", "png", "gif", "webp", "bmp");

    @Value("${app.public-directory:public}")
    private String publicDirectory;

    @PostMapping(value = "/picture", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> upload(@RequestPart("file") MultipartFile file) throws IOException {
        if (file == null || file.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "file is required"));
        }
        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_TYPES.contains(contentType.toLowerCase(Locale.ROOT))) {
            return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
                    .body(Map.of("error", "unsupported image type"));
        }
        String ext = extensionForContentType(contentType);
        String original = StringUtils.cleanPath(file.getOriginalFilename() != null ? file.getOriginalFilename() : "");
        if (original.contains("..")) {
            return ResponseEntity.badRequest().body(Map.of("error", "invalid filename"));
        }
        if (ext.isEmpty()) {
            ext = extensionFromFilename(original);
            if (ext.isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of("error", "could not determine file extension"));
            }
        }
        String filename = UUID.randomUUID() + "." + ext;
        Path destDir = Paths.get(publicDirectory).toAbsolutePath().normalize().resolve("uploads").resolve(UPLOAD_SUBDIR);
        Files.createDirectories(destDir);
        Path dest = destDir.resolve(filename);
        Files.copy(file.getInputStream(), dest, StandardCopyOption.REPLACE_EXISTING);
        String url = ServletUriComponentsBuilder.fromCurrentContextPath()
                .path("/uploads/" + UPLOAD_SUBDIR + "/")
                .path(filename)
                .toUriString();
        return ResponseEntity.ok(Map.of("url", url));
    }

    private static String extensionForContentType(String contentType) {
        String ct = contentType.toLowerCase(Locale.ROOT);
        return switch (ct) {
            case "image/jpeg", "image/jpg" -> "jpg";
            case "image/png" -> "png";
            case "image/gif" -> "gif";
            case "image/webp" -> "webp";
            case "image/bmp", "image/x-ms-bmp" -> "bmp";
            default -> "";
        };
    }

    private static String extensionFromFilename(String name) {
        int i = name.lastIndexOf('.');
        if (i < 0 || i == name.length() - 1) {
            return "";
        }
        String ext = name.substring(i + 1).toLowerCase(Locale.ROOT);
        if ("jpeg".equals(ext)) {
            ext = "jpg";
        }
        return ALLOWED_EXTENSIONS.contains(ext) ? ext : "";
    }
}
