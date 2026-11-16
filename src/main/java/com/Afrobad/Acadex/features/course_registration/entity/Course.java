package com.Afrobad.Acadex.features.course_registration.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(
    name = "courses",
    indexes = {
        @Index(name = "idx_course_code", columnList = "course_code")
    }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Course {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(
        name = "course_code",
        nullable = false,
        unique = true,
        length = 20
    )
    private String courseCode;

    @Column(
        name = "course_title",
        nullable = false,
        length = 150
    )
    private String courseTitle;

    @Column(
        nullable = false,
        precision = 4,
        scale = 2
    )
    private BigDecimal credits;

    @Column(length = 100)
    private String department;

    @Column(name = "program_name", length = 100)
    private String programName;

    @Column(nullable = false)
    @Builder.Default
    private Boolean active = true;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
    }
}

