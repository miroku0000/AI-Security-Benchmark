package com.example.oidcclient;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

  @Bean
  SecurityFilterChain securityFilterChain(HttpSecurity http, OidcSessionAuthenticationSuccessHandler successHandler)
      throws Exception {
        http
        .authorizeHttpRequests(
            auth ->
                auth.requestMatchers(
                        HttpMethod.GET,
                        "/",
                        "/error",
                        "/webjars/**",
                        "/css/**",
                        "/js/**",
                        "/oauth2/**",
                        "/login/oauth2/**")
                    .permitAll()
                    .anyRequest()
                    .authenticated())
        .oauth2Login(oauth2 -> oauth2.successHandler(successHandler))
        .logout(logout -> logout.logoutSuccessUrl("/").invalidateHttpSession(true).clearAuthentication(true));

    return http.build();
  }
}
