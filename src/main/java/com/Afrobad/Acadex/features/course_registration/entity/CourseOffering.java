package com.Afrobad.Acadex.features.course_registration.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(
    name = "course_offerings",
    indexes = {
        @Index(
            name = "idx_offering_semester",
            columnList = "academic_year, semester"
        ),
        @Index(
            name = "idx_offering_course",
            columnList = "course_id"
        )
    },
    uniqueConstraints = {
    		@UniqueConstraint(
    			    name = "uk_course_semester_batch",
    			    columnNames = {
    			        "course_id",
    			        "academic_year",
    			        "semester",
    			        "batch"
    			    }
    			)
    }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CourseOffering {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    // Course being offered
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "course_id", nullable = false)
    private Course course;

    // Example: 2027
    @Column(name = "academic_year", nullable = false, length = 20)
    private String academicYear;

    // Example: Spring, Summer, Fall
    @Column(nullable = false, length = 30)
    private String semester;
    
    @Column(nullable = false, length = 20)
    private String batch;


    // Maximum number of students allowed
    @Column(name = "capacity")
    private Integer capacity;

    // Number of students currently registered
    @Column(name = "enrolled_count")
    @Builder.Default
    private Integer enrolledCount = 0;

    // Whether this course is available for registration
    @Column(nullable = false)
    @Builder.Default
    private Boolean active = true;

    @Column(name = "registration_start")
    private LocalDateTime registrationStart;

    @Column(name = "registration_end")
    private LocalDateTime registrationEnd;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }

        if (enrolledCount == null) {
            enrolledCount = 0;
        }

        if (active == null) {
            active = true;
        }
    }
}
