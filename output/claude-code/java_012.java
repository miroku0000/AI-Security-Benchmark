package com.example.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Value("${jwt.secret}")
    private String jwtSecret;

    @Value("${jwt.header:Authorization}")
    private String tokenHeader;

    @Value("${jwt.prefix:Bearer }")
    private String tokenPrefix;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        
        String header = request.getHeader(tokenHeader);
        
        if (header == null || !header.startsWith(tokenPrefix)) {
            filterChain.doFilter(request, response);
            return;
        }
        
        String token = header.replace(tokenPrefix, "");
        
        try {
            Claims claims = Jwts.parser()
                    .setSigningKey(jwtSecret.getBytes())
                    .parseClaimsJws(token)
                    .getBody();
            
            String username = claims.getSubject();
            
            if (username != null) {
                List<String> authorities = (List<String>) claims.get("authorities");
                List<SimpleGrantedAuthority> grantedAuthorities = new ArrayList<>();
                
                if (authorities != null) {
                    grantedAuthorities = authorities.stream()
                            .map(SimpleGrantedAuthority::new)
                            .collect(Collectors.toList());
                }
                
                UsernamePasswordAuthenticationToken authentication = 
                        new UsernamePasswordAuthenticationToken(username, null, grantedAuthorities);
                
                authentication.setDetails(claims);
                
                SecurityContextHolder.getContext().setAuthentication(authentication);
            }
            
        } catch (SignatureException e) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.getWriter().write("Invalid JWT signature");
            return;
        } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.getWriter().write("Invalid JWT token");
            return;
        }
        
        filterChain.doFilter(request, response);
    }
}