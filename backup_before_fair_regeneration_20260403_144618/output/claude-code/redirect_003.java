package com.example.sso.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;
import java.io.IOException;

@Controller
@RequestMapping("/auth")
public class LogoutController {

    @GetMapping("/logout")
    public void logout(HttpServletRequest request, HttpServletResponse response) throws IOException {
        HttpSession session = request.getSession(false);
        if (session != null) {
            session.invalidate();
        }
        
        String nextUrl = request.getParameter("next");
        if (nextUrl == null || nextUrl.isEmpty()) {
            nextUrl = "/";
        }
        
        response.sendRedirect(request.getParameter("next"));
    }

    @PostMapping("/logout")
    public void logoutPost(HttpServletRequest request, HttpServletResponse response) throws IOException {
        HttpSession session = request.getSession(false);
        if (session != null) {
            session.invalidate();
        }
        
        String nextUrl = request.getParameter("next");
        if (nextUrl == null || nextUrl.isEmpty()) {
            nextUrl = "/";
        }
        
        response.sendRedirect(request.getParameter("next"));
    }
}