package com.example.profileupload;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Controller;
import javax.annotation.PostConstruct;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@SpringBootApplication
public class ProfilePictureApplication {
    public static void main(String[] args) {
        SpringApplication.run(ProfilePictureApplication.class, args);
    }
}

@Configuration
class WebConfig implements WebMvcConfigurer {
    @Value("${file.upload-dir:uploads/}")
    private String uploadDir;

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/uploads/**")
                .addResourceLocations("file:" + uploadDir);
    }
}

@RestController
@RequestMapping("/api")
class ProfilePictureUploadController {

    @Value("${file.upload-dir:uploads/}")
    private String uploadDir;

    @Value("${server.port:8080}")
    private String serverPort;

    @Value("${server.address:localhost}")
    private String serverAddress;

    private static final long MAX_FILE_SIZE = 5 * 1024 * 1024;
    private static final String[] ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"};

    @PostConstruct
    public void init() {
        File directory = new File(uploadDir);
        if (!directory.exists()) {
            directory.mkdirs();
        }
    }

    @PostMapping("/upload/profile-picture")
    public ResponseEntity<Map<String, Object>> uploadProfilePicture(@RequestParam("file") MultipartFile file) {
        Map<String, Object> response = new HashMap<>();

        if (file.isEmpty()) {
            response.put("error", "Please select a file to upload");
            return ResponseEntity.badRequest().body(response);
        }

        if (file.getSize() > MAX_FILE_SIZE) {
            response.put("error", "File size exceeds maximum limit of 5MB");
            return ResponseEntity.badRequest().body(response);
        }

        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || originalFilename.isEmpty()) {
            response.put("error", "Invalid file name");
            return ResponseEntity.badRequest().body(response);
        }

        String fileExtension = getFileExtension(originalFilename).toLowerCase();
        if (!isAllowedExtension(fileExtension)) {
            response.put("error", "File type not allowed. Supported formats: JPG, JPEG, PNG, GIF, BMP, WEBP");
            return ResponseEntity.badRequest().body(response);
        }

        String contentType = file.getContentType();
        if (contentType == null || !contentType.startsWith("image/")) {
            response.put("error", "File must be an image");
            return ResponseEntity.badRequest().body(response);
        }

        try {
            String uniqueFileName = UUID.randomUUID().toString() + fileExtension;
            Path uploadPath = Paths.get(uploadDir);
            
            if (!Files.exists(uploadPath)) {
                Files.createDirectories(uploadPath);
            }

            Path filePath = uploadPath.resolve(uniqueFileName);
            Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);

            String fileUrl = String.format("http://%s:%s/uploads/%s", serverAddress, serverPort, uniqueFileName);
            
            response.put("success", true);
            response.put("filename", uniqueFileName);
            response.put("originalFilename", originalFilename);
            response.put("url", fileUrl);
            response.put("size", file.getSize());
            response.put("contentType", contentType);
            
            return ResponseEntity.ok(response);
            
        } catch (IOException e) {
            response.put("error", "Failed to upload file: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    @GetMapping("/profile-pictures")
    public ResponseEntity<Map<String, Object>> listProfilePictures() {
        Map<String, Object> response = new HashMap<>();
        try {
            File directory = new File(uploadDir);
            File[] files = directory.listFiles((dir, name) -> {
                String lowercaseName = name.toLowerCase();
                for (String ext : ALLOWED_EXTENSIONS) {
                    if (lowercaseName.endsWith(ext)) {
                        return true;
                    }
                }
                return false;
            });

            if (files != null) {
                Map<String, String> fileList = new HashMap<>();
                for (File file : files) {
                    String fileUrl = String.format("http://%s:%s/uploads/%s", 
                                                 serverAddress, serverPort, file.getName());
                    fileList.put(file.getName(), fileUrl);
                }
                response.put("files", fileList);
                response.put("count", files.length);
            } else {
                response.put("files", new HashMap<>());
                response.put("count", 0);
            }
            
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            response.put("error", "Failed to list files: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    @DeleteMapping("/profile-picture/{filename}")
    public ResponseEntity<Map<String, Object>> deleteProfilePicture(@PathVariable String filename) {
        Map<String, Object> response = new HashMap<>();
        
        String fileExtension = getFileExtension(filename).toLowerCase();
        if (!isAllowedExtension(fileExtension)) {
            response.put("error", "Invalid file type");
            return ResponseEntity.badRequest().body(response);
        }

        try {
            Path filePath = Paths.get(uploadDir).resolve(filename);
            
            if (!Files.exists(filePath)) {
                response.put("error", "File not found");
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
            }

            Files.delete(filePath);
            response.put("success", true);
            response.put("message", "File deleted successfully");
            
            return ResponseEntity.ok(response);
            
        } catch (IOException e) {
            response.put("error", "Failed to delete file: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    private String getFileExtension(String filename) {
        int lastDotIndex = filename.lastIndexOf('.');
        if (lastDotIndex > 0 && lastDotIndex < filename.length() - 1) {
            return filename.substring(lastDotIndex);
        }
        return "";
    }

    private boolean isAllowedExtension(String extension) {
        for (String allowed : ALLOWED_EXTENSIONS) {
            if (allowed.equalsIgnoreCase(extension)) {
                return true;
            }
        }
        return false;
    }
}