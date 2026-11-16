package com.Afrobad.Acadex.security.jwt;

import com.Afrobad.Acadex.security.user.CustomUserDetailsService;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import lombok.RequiredArgsConstructor;

import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;

import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;

    private final CustomUserDetailsService userDetailsService;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {

    	String authHeader = request.getHeader("Authorization");

    	if (authHeader == null || !authHeader.startsWith("Bearer ")) {
    	    log.warn("No Bearer token found for request: {}", request.getRequestURI());

    	    filterChain.doFilter(request, response);
    	    return;
    	}

    	String token = authHeader.substring(7);

    	try {
    	    if (!jwtService.isTokenValid(token)) {
    	        log.warn("Invalid JWT for request: {}", request.getRequestURI());

    	        filterChain.doFilter(request, response);
    	        return;
    	    }

    	    String employeeId = jwtService.extractEmployeeId(token);

    	    if (SecurityContextHolder.getContext().getAuthentication() == null) {
    	        UserDetails userDetails =
    	                userDetailsService.loadUserByUsername(employeeId);

    	        UsernamePasswordAuthenticationToken authentication =
    	                new UsernamePasswordAuthenticationToken(
    	                        userDetails,
    	                        null,
    	                        userDetails.getAuthorities()
    	                );

    	        authentication.setDetails(
    	                new WebAuthenticationDetailsSource().buildDetails(request)
    	        );

    	        SecurityContextHolder.getContext().setAuthentication(authentication);

    	        log.info(
    	                "JWT authenticated user: {}, Authorities: {}",
    	                userDetails.getUsername(),
    	                userDetails.getAuthorities()
    	        );
    	    }

    	} catch (Exception exception) {
    	    log.error("JWT authentication failed for request: {}",
    	            request.getRequestURI(), exception);

    	    SecurityContextHolder.clearContext();
    	}

    	filterChain.doFilter(request, response);
    }
}
