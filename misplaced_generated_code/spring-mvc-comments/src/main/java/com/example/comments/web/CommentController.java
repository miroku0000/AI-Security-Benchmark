package com.example.comments.web;

import com.example.comments.repo.CommentRepository;
import java.util.List;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping
public class CommentController {
  private final CommentRepository commentRepository;
  private final HtmlSanitizer sanitizer;

  public CommentController(CommentRepository commentRepository, HtmlSanitizer sanitizer) {
    this.commentRepository = commentRepository;
    this.sanitizer = sanitizer;
  }

  @GetMapping({"/", "/comments"})
  public String comments(Model model) {
    List<CommentView> comments =
        commentRepository.findAllByOrderByCreatedAtDesc().stream()
            .map(
                c ->
                    new CommentView(
                        c.getId(),
                        c.getUsername(),
                        sanitizer.sanitize(c.getBody()),
                        c.getCreatedAt()))
            .toList();
    model.addAttribute("comments", comments);
    return "comments";
  }
}
