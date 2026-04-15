package com.example.comments;

import com.example.comments.model.Comment;
import com.example.comments.repo.CommentRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DataInitializer {
  @Bean
  CommandLineRunner seedComments(CommentRepository repo) {
    return args -> {
      if (repo.count() > 0) return;
      repo.save(new Comment("alice", "Hello <b>world</b>! Here is a <a href=\"https://example.com\">link</a>."));
      repo.save(new Comment("bob", "Lists work:<ul><li>one</li><li><i>two</i></li></ul>"));
      repo.save(new Comment("charlie", "New line<br>another line"));
    };
  }
}
