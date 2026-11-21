package com.Afrobad.Acadex.features.performance_analysis.entity;

import com.Afrobad.Acadex.features.course_registration.entity.Student;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(
    name = "student_performance",
    uniqueConstraints = @UniqueConstraint(
        name = "uq_student_perf_term",
        columnNames = {"student_id", "academic_year", "semester"}
    )
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StudentPerformance {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "student_id", nullable = false)
    private Student student;

    @Column(name = "academic_year", nullable = false, length = 20)
    private String academicYear;

    @Column(nullable = false, length = 30)
    private String semester;

    @Column(name = "attendance_percent", nullable = false, precision = 5, scale = 2)
    private BigDecimal attendancePercent;

    @Column(name = "quiz_percent", nullable = false, precision = 5, scale = 2)
    private BigDecimal quizPercent;

    @Column(name = "midterm_percent", nullable = false, precision = 5, scale = 2)
    private BigDecimal midtermPercent;

    @Column(name = "lab_percent", nullable = false, precision = 5, scale = 2)
    private BigDecimal labPercent;

    @Column(name = "missing_assessments", nullable = false)
    @Builder.Default
    private Integer missingAssessments = 0;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    @PreUpdate
    protected void touch() {
        updatedAt = LocalDateTime.now();
    }
}