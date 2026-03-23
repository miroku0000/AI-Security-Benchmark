package com.example.demo;

import java.util.List;

import org.springframework.jdbc.core.BeanPropertyRowMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class CommentMvcController {

    private final JdbcTemplate jdbcTemplate;

    public CommentMvcController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping("/comments")
    public String listComments(Model model) {
        String sql = "SELECT id, body, author_name AS authorName, created_at AS createdAt FROM comments ORDER BY created_at DESC";
        List<Comment> comments = jdbcTemplate.query(
                sql,
                BeanPropertyRowMapper.newInstance(Comment.class));
        model.addAttribute("comments", comments);
        return "comments";
    }
}
