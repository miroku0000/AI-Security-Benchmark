package com.example.comments.web;

import com.example.comments.model.Comment;
import com.example.comments.repository.CommentRepository;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.List;

@Controller
public class CommentController {

    private final CommentRepository commentRepository;

    public CommentController(CommentRepository commentRepository) {
        this.commentRepository = commentRepository;
    }

    @GetMapping("/")
    public String index() {
        return "redirect:/comments";
    }

    @GetMapping("/comments")
    public String listComments(Model model) {
        List<Comment> comments = commentRepository.findAll();
        model.addAttribute("comments", comments);
        return "comments";
    }
}
