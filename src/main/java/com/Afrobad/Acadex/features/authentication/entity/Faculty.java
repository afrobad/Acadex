package com.Afrobad.Acadex.features.authentication.entity;


import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

import com.Afrobad.Acadex.features.authentication.enums.Role;

@Entity
@Table(
    name = "faculties",
    uniqueConstraints = {
        @UniqueConstraint(columnNames = "employee_id"),
        @UniqueConstraint(columnNames = "email")
    }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Faculty {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(
        name = "employee_id",
        nullable = false,
        unique = true,
        length = 30
    )
    private String employeeId;

    @Column(
        name = "full_name",
        nullable = false,
        length = 100
    )
    private String fullName;

    @Column(
        name = "email",
        nullable = false,
        unique = true,
        length = 120
    )
    private String email;

    @Column(
        name = "password",
        nullable = false
    )
    private String password;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Role role;

    @Column(nullable = false)
    @Builder.Default
    private Boolean enabled = true;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    public void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
    }
}