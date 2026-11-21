package com.Afrobad.Acadex.features.performance_analysis.repository;

import com.Afrobad.Acadex.features.performance_analysis.entity.StudentPerformance;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface StudentPerformanceRepository extends JpaRepository<StudentPerformance, Long> {

    Optional<StudentPerformance> findByStudentStudentIdAndAcademicYearAndSemester(
            String studentId,
            String academicYear,
            String semester
    );
}