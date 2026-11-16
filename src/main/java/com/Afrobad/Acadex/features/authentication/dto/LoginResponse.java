package com.Afrobad.Acadex.features.authentication.dto;

import lombok.*;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponse {

    private String accessToken;

    private String tokenType;

    private Long expiresIn;

    private Long facultyId;

    private String employeeId;

    private String fullName;

    private String email;

    private String role;
}