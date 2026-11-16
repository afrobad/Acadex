package com.Afrobad.Acadex.features.course_registration.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import com.Afrobad.Acadex.features.course_registration.enums.StudentCourseStatus;

@Entity
@Table(
    name = "student_courses",
    indexes = {
        @Index(name = "idx_student_course_student", columnList = "student_id"),
        @Index(name = "idx_student_course_course", columnList = "course_id")
    }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StudentCourse {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "student_id", nullable = false)
    private Student student;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "course_id", nullable = false)
    private Course course;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private StudentCourseStatus status;

    @Column(name = "grade_point", precision = 3, scale = 2)
    private BigDecimal gradePoint;

    @Column(name = "earned_credits", precision = 4, scale = 2)
    private BigDecimal earnedCredits;

    @Column(name = "academic_year", length = 20)
    private String academicYear;

    @Column(name = "semester", length = 30)
    private String semester;

    @Column(name = "attempt_number", nullable = false)
    @Builder.Default
    private Integer attemptNumber = 1;

    @Column(name = "enrolled_at")
    private LocalDateTime enrolledAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }

        if (enrolledAt == null) {
            enrolledAt = LocalDateTime.now();
        }

        if (attemptNumber == null) {
            attemptNumber = 1;
        }
    }
}
