package com.example.comments.web;

import java.time.Instant;

public record CommentView(Long id, String username, String sanitizedHtmlBody, Instant createdAt) {}
