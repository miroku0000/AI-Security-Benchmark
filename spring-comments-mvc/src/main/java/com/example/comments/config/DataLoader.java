package com.example.comments.config;

import com.example.comments.model.Comment;
import com.example.comments.repository.CommentRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DataLoader {

    @Bean
    CommandLineRunner loadSampleComments(CommentRepository commentRepository) {
        return args -> {
            if (commentRepository.count() > 0) {
                return;
            }
            Comment c1 = new Comment();
            c1.setAuthor("Alice");
            c1.setBody("<p>Welcome! You can use <strong>bold</strong>, <em>italic</em>, and <a href=\"https://example.com\">links</a>.</p>");
            commentRepository.save(c1);
            Comment c2 = new Comment();
            c2.setAuthor("Bob");
            c2.setBody("<ul><li>Item one</li><li>Item two</li></ul>");
            commentRepository.save(c2);
        };
    }
}
