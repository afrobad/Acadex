package com.Afrobad.Acadex.features.course_registration.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

import com.Afrobad.Acadex.features.course_registration.enums.StudentStatus;

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
    
    /** Enrollment status. Null (legacy rows) is treated as ACTIVE. */
    @Enumerated(EnumType.STRING)
    @Column(length = 20)
    private StudentStatus status;

    /** Total credits required to graduate. Null falls back to the service default. */
    @Column(name = "total_program_credits")
    private Integer totalProgramCredits;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
    }
}
