package com.Afrobad.Acadex.features.course_registration.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(
    name = "course_prerequisites",
    uniqueConstraints = {
        @UniqueConstraint(
            name = "uk_course_prerequisite",
            columnNames = {"course_id", "prerequisite_course_id"}
        )
    }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CoursePrerequisite {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // The course a student wants to take
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "course_id", nullable = false)
    private Course course;

    // The course that must be completed first
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "prerequisite_course_id", nullable = false)
    private Course prerequisiteCourse;

}
