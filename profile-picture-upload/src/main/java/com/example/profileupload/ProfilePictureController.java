package com.example.profileupload;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

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

    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            MediaType.IMAGE_JPEG_VALUE,
            MediaType.IMAGE_PNG_VALUE,
            "image/gif",
            "image/webp",
            "image/bmp",
            "image/x-ms-bmp"
    );

    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("jpg", "jpeg", "png", "gif", "webp", "bmp");

    @Value("${app.upload.public-dir}")
    private String publicUploadDir;

    @Value("${app.upload.url-prefix:/public/uploads}")
    private String urlPrefix;

    @PostMapping(value = "/picture", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> uploadProfilePicture(
            @RequestParam("file") MultipartFile file,
            HttpServletRequest request) throws IOException {

        if (file == null || file.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "file is required"));
        }

        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_CONTENT_TYPES.contains(contentType.toLowerCase(Locale.ROOT))) {
            return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
                    .body(Map.of("error", "unsupported image type; allowed: JPEG, PNG, GIF, WebP, BMP"));
        }

        String original = StringUtils.cleanPath(file.getOriginalFilename() == null ? "" : file.getOriginalFilename());
        String ext = extension(original);
        if (ext.isEmpty() || !ALLOWED_EXTENSIONS.contains(ext)) {
            return ResponseEntity.badRequest().body(Map.of("error", "invalid file extension"));
        }

        Path uploadRoot = Paths.get(publicUploadDir).toAbsolutePath().normalize();
        Files.createDirectories(uploadRoot);

        String filename = UUID.randomUUID() + "." + ext;
        Path target = uploadRoot.resolve(filename).normalize();
        if (!target.startsWith(uploadRoot)) {
            return ResponseEntity.badRequest().body(Map.of("error", "invalid path"));
        }

        Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);

        String base = request.getScheme() + "://" + request.getServerName()
                + (request.getServerPort() == 80 || request.getServerPort() == 443 ? ""
                : ":" + request.getServerPort())
                + request.getContextPath();
        String prefix = urlPrefix.startsWith("/") ? urlPrefix : "/" + urlPrefix;
        String url = base + prefix + "/" + filename;

        return ResponseEntity.ok(Map.of("url", url));
    }

    private static String extension(String filename) {
        int i = filename.lastIndexOf('.');
        if (i < 0 || i == filename.length() - 1) {
            return "";
        }
        return filename.substring(i + 1).toLowerCase(Locale.ROOT);
    }
}
