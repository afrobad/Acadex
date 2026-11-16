package com.Afrobad.Acadex.features.authentication.service;

import com.Afrobad.Acadex.features.authentication.dto.LoginRequest;
import com.Afrobad.Acadex.features.authentication.dto.LoginResponse;

import com.Afrobad.Acadex.features.authentication.entity.Faculty;
import com.Afrobad.Acadex.features.authentication.repository.FacultyRepository;

import com.Afrobad.Acadex.security.jwt.JwtService;

import lombok.RequiredArgsConstructor;

import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.authentication.BadCredentialsException;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final FacultyRepository facultyRepository;

    private final AuthenticationManager authenticationManager;

    private final JwtService jwtService;

    @Transactional(readOnly = true)
    public LoginResponse login(LoginRequest request) {

        String employeeId =
                request.getEmployeeId().trim().toUpperCase();

        String email =
                request.getEmail().trim().toLowerCase();

        Faculty faculty = facultyRepository
                .findByEmployeeId(employeeId)
                .orElseThrow(() ->
                        new BadCredentialsException(
                                "Invalid login credentials"
                        )
                );

        if (!faculty.getEmail().equalsIgnoreCase(email)) {

            throw new BadCredentialsException(
                    "Invalid login credentials"
            );
        }

        if (!Boolean.TRUE.equals(faculty.getEnabled())) {

            throw new BadCredentialsException(
                    "Invalid login credentials"
            );
        }

        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                        employeeId,
                        request.getPassword()
                )
        );

        String token =
                jwtService.generateToken(employeeId);

        return LoginResponse.builder()

                .accessToken(token)

                .tokenType("Bearer")

                .expiresIn(jwtService.getExpiration())

                .facultyId(faculty.getId())

                .employeeId(faculty.getEmployeeId())

                .fullName(faculty.getFullName())

                .email(faculty.getEmail())

                .role(faculty.getRole().name())

                .build();
    }
}
