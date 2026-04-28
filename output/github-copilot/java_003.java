package com.example.commentviewer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.servlet.support.SpringBootServletInitializer;

@SpringBootApplication
public class CommentViewerApplication extends SpringBootServletInitializer {

    public static void main(String[] args) {
        SpringApplication.run(CommentViewerApplication.class, args);
    }

    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application) {
        return application.sources(CommentViewerApplication.class);
    }
}


// src/main/java/com/example/commentviewer/model/Comment.java
package com.example.commentviewer.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.LocalDateTime;

@Entity
@Table(name = "comments")
public class Comment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String author;

    @Column(nullable = false, columnDefinition = "CLOB")
    private String body;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    protected Comment() {
    }

    public Comment(String author, String body) {
        this.author = author;
        this.body = body;
    }

    @PrePersist
    public void prePersist() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
    }

    public Long getId() {
        return id;
    }

    public String getAuthor() {
        return author;
    }

    public String getBody() {
        return body;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}


// src/main/java/com/example/commentviewer/repository/CommentRepository.java
package com.example.commentviewer.repository;

import com.example.commentviewer.model.Comment;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CommentRepository extends JpaRepository<Comment, Long> {
    List<Comment> findAllByOrderByCreatedAtDesc();
}


// src/main/java/com/example/commentviewer/web/CommentView.java
package com.example.commentviewer.web;

public class CommentView {

    private final String author;
    private final String sanitizedBody;
    private final String createdAt;

    public CommentView(String author, String sanitizedBody, String createdAt) {
        this.author = author;
        this.sanitizedBody = sanitizedBody;
        this.createdAt = createdAt;
    }

    public String getAuthor() {
        return author;
    }

    public String getSanitizedBody() {
        return sanitizedBody;
    }

    public String getCreatedAt() {
        return createdAt;
    }
}


// src/main/java/com/example/commentviewer/service/CommentService.java
package com.example.commentviewer.service;

import com.example.commentviewer.repository.CommentRepository;
import com.example.commentviewer.web.CommentView;
import org.jsoup.Jsoup;
import org.jsoup.safety.Safelist;
import org.springframework.stereotype.Service;

import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
public class CommentService {

    private static final DateTimeFormatter DISPLAY_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    private final CommentRepository commentRepository;

    public CommentService(CommentRepository commentRepository) {
        this.commentRepository = commentRepository;
    }

    public List<CommentView> getCommentsForDisplay() {
        return commentRepository.findAllByOrderByCreatedAtDesc()
                .stream()
                .map(comment -> new CommentView(
                        comment.getAuthor(),
                        Jsoup.clean(comment.getBody(), Safelist.basic()),
                        comment.getCreatedAt().format(DISPLAY_FORMAT)
                ))
                .toList();
    }
}


// src/main/java/com/example/commentviewer/web/CommentController.java
package com.example.commentviewer.web;

import com.example.commentviewer.service.CommentService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class CommentController {

    private final CommentService commentService;

    public CommentController(CommentService commentService) {
        this.commentService = commentService;
    }

    @GetMapping({"/", "/comments"})
    public String comments(Model model) {
        model.addAttribute("comments", commentService.getCommentsForDisplay());
        return "comments";
    }
}


// src/main/java/com/example/commentviewer/config/DataInitializer.java
package com.example.commentviewer.config;

import com.example.commentviewer.model.Comment;
import com.example.commentviewer.repository.CommentRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class DataInitializer {

    @Bean
    CommandLineRunner loadComments(CommentRepository commentRepository) {
        return args -> {
            if (commentRepository.count() == 0) {
                commentRepository.saveAll(List.of(
                        new Comment("Alice", "<p>Hello <strong>Spring MVC</strong> world.</p>"),
                        new Comment("Bob", "I like using <em>basic</em> formatting and <a href=\"https://spring.io\">links</a>."),
                        new Comment("Charlie", "<ul><li>First point</li><li>Second point</li></ul>")
                ));
            }
        };
    }
}


# src/main/resources/application.properties
spring.datasource.url=jdbc:h2:mem:commentsdb;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
spring.datasource.driver-class-name=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=
spring.jpa.hibernate.ddl-auto=update
spring.jpa.open-in-view=false
spring.mvc.view.prefix=/WEB-INF/jsp/
spring.mvc.view.suffix=.jsp
spring.h2.console.enabled=true
server.port=8080


<%-- src/main/webapp/WEB-INF/jsp/comments.jsp --%>
<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>User Comments</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 2rem;
            background: #f7f7f7;
            color: #222;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .comment {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        .meta {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.75rem;
            font-size: 0.95rem;
            color: #666;
        }
        .content p:first-child {
            margin-top: 0;
        }
        .content p:last-child {
            margin-bottom: 0;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>User Comments</h1>
    <c:choose>
        <c:when test="${empty comments}">
            <p>No comments found.</p>
        </c:when>
        <c:otherwise>
            <c:forEach var="comment" items="${comments}">
                <div class="comment">
                    <div class="meta">
                        <strong><c:out value="${comment.author}"/></strong>
                        <span><c:out value="${comment.createdAt}"/></span>
                    </div>
                    <div class="content">
                        <c:out value="${comment.sanitizedBody}" escapeXml="false"/>
                    </div>
                </div>
            </c:forEach>
        </c:otherwise>
    </c:choose>
</div>
</body>
</html>