package com.Afrobad.Acadex.features.authentication.controller;


import com.Afrobad.Acadex.features.authentication.dto.LoginRequest;
import com.Afrobad.Acadex.features.authentication.dto.LoginResponse;

import com.Afrobad.Acadex.features.authentication.service.AuthService;

import jakarta.validation.Valid;

import lombok.RequiredArgsConstructor;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(
            @Valid @RequestBody LoginRequest request
    ) {

        LoginResponse response =
                authService.login(request);

        return ResponseEntity.ok(response);
    }
}