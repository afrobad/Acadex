package com.Afrobad.Acadex.features.course_registration.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(
    name = "students",
    indexes = {
        @Index(name = "idx_student_student_id", columnList = "student_id")
    }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Student {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(
        name = "student_id",
        nullable = false,
        unique = true,
        length = 30
    )
    private String studentId;

    @Column(
        name = "full_name",
        nullable = false,
        length = 120
    )
    private String fullName;

    @Column(length = 100)
    private String department;

    @Column(length = 30)
    private String batch;

    @Column(name = "current_semester")
    private Integer currentSemester;

    @Column(name = "program_name", length = 100)
    private String programName;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
    }
}
