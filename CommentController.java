package com.example.comments;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@Controller
@RequestMapping("/comments")
public class CommentController {

    @Autowired
    private CommentService commentService;

    @GetMapping
    public String showComments(Model model) {
        List<Comment> comments = commentService.getAllComments();
        model.addAttribute("comments", comments);
        model.addAttribute("newComment", new Comment());
        return "comments";
    }

    @PostMapping("/add")
    public String addComment(@ModelAttribute Comment comment) {
        commentService.saveComment(comment);
        return "redirect:/comments";
    }
}