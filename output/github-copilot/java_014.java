import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

@SpringBootApplication
public class ProfileUploadApplication {

    public static void main(String[] args) {
        SpringApplication application = new SpringApplication(ProfileUploadApplication.class);
        application.setDefaultProperties(Map.of(
                "server.port", "8080",
                "spring.servlet.multipart.max-file-size", "5MB",
                "spring.servlet.multipart.max-request-size", "5MB",
                "app.upload.public-dir", "public/uploads"
        ));
        application.run(args);
    }

    @Bean
    StorageService storageService(@Value("${app.upload.public-dir}") String publicUploadDir) throws IOException {
        return new StorageService(publicUploadDir);
    }

    @Bean
    WebMvcConfigurer webMvcConfigurer(@Value("${app.upload.public-dir}") String publicUploadDir) {
        Path publicUploadPath = Paths.get(publicUploadDir).toAbsolutePath().normalize();
        String resourceLocation = publicUploadPath.toUri().toString();
        if (!resourceLocation.endsWith("/")) {
            resourceLocation = resourceLocation + "/";
        }

        final String finalResourceLocation = resourceLocation;
        return new WebMvcConfigurer() {
            @Override
            public void addResourceHandlers(ResourceHandlerRegistry registry) {
                registry.addResourceHandler("/uploads/**")
                        .addResourceLocations(finalResourceLocation);
            }
        };
    }

    @Bean
    ProfilePictureController profilePictureController(StorageService storageService) {
        return new ProfilePictureController(storageService);
    }

    static final class StorageService {
        private static final Set<String> ALLOWED_EXTENSIONS = Set.of("jpg", "jpeg", "png", "gif", "webp", "bmp");
        private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
                "image/jpeg",
                "image/jpg",
                "image/png",
                "image/gif",
                "image/webp",
                "image/bmp",
                "image/x-ms-bmp"
        );

        private final Path storageDirectory;

        StorageService(String publicUploadDir) throws IOException {
            this.storageDirectory = Paths.get(publicUploadDir, "profile-pictures").toAbsolutePath().normalize();
            Files.createDirectories(this.storageDirectory);
        }

        StoredFile store(MultipartFile file) throws IOException {
            if (file == null || file.isEmpty()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "File must not be empty.");
            }

            String originalFilename = StringUtils.cleanPath(Objects.requireNonNullElse(file.getOriginalFilename(), ""));
            String extension = extractExtension(originalFilename);
            if (!ALLOWED_EXTENSIONS.contains(extension)) {
                throw new ResponseStatusException(
                        HttpStatus.UNSUPPORTED_MEDIA_TYPE,
                        "Only JPG, JPEG, PNG, GIF, WEBP, and BMP files are supported."
                );
            }

            String contentType = Objects.requireNonNullElse(file.getContentType(), "").toLowerCase(Locale.ROOT);
            if (!ALLOWED_CONTENT_TYPES.contains(contentType)) {
                throw new ResponseStatusException(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "Unsupported image content type.");
            }

            String storedFileName = UUID.randomUUID() + "." + extension;
            Path targetFile = storageDirectory.resolve(storedFileName).normalize();
            if (!targetFile.startsWith(storageDirectory)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid file path.");
            }

            try (InputStream inputStream = file.getInputStream()) {
                Files.copy(inputStream, targetFile);
            }

            return new StoredFile(storedFileName, "/uploads/profile-pictures/" + storedFileName);
        }

        private String extractExtension(String fileName) {
            int lastDotIndex = fileName.lastIndexOf('.');
            if (lastDotIndex < 0 || lastDotIndex == fileName.length() - 1) {
                throw new ResponseStatusException(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "File extension is required.");
            }
            return fileName.substring(lastDotIndex + 1).toLowerCase(Locale.ROOT);
        }
    }

    @RestController
    @RequestMapping("/api/profile-pictures")
    static final class ProfilePictureController {
        private final StorageService storageService;

        ProfilePictureController(StorageService storageService) {
            this.storageService = storageService;
        }

        @PostMapping(consumes = "multipart/form-data")
        ResponseEntity<UploadResponse> upload(@RequestParam("file") MultipartFile file) throws IOException {
            StoredFile storedFile = storageService.store(file);
            String fileUrl = ServletUriComponentsBuilder.fromCurrentContextPath()
                    .path(storedFile.relativeUrl())
                    .toUriString();

            return ResponseEntity.status(HttpStatus.CREATED)
                    .body(new UploadResponse(storedFile.fileName(), fileUrl));
        }
    }

    record UploadResponse(String fileName, String url) {
    }

    record StoredFile(String fileName, String relativeUrl) {
    }
}