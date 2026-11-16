package com.Afrobad.Acadex.features.course_registration.repository;

import com.Afrobad.Acadex.features.course_registration.entity.StudentCourse;
import org.springframework.data.jpa.repository.JpaRepository;
import com.Afrobad.Acadex.features.course_registration.enums.StudentCourseStatus;
import java.util.List;

public interface StudentCourseRepository extends JpaRepository<StudentCourse, Long> {

    List<StudentCourse> findByStudentStudentId(String studentId);

    List<StudentCourse> findByStudentStudentIdAndStatus(
            String studentId,
            StudentCourseStatus status
    );

    List<StudentCourse> findByStudentId(Long studentId);
}
