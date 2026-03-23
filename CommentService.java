package com.example.comments;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class CommentService {
    
    @Autowired
    private CommentRepository commentRepository;
    
    public List<Comment> getAllComments() {
        return commentRepository.findAllByOrderByCreatedAtDesc();
    }
    
    public Comment saveComment(Comment comment) {
        return commentRepository.save(comment);
    }
}