package com.Afrobad.Acadex.features.course_registration.repository;

import com.Afrobad.Acadex.features.course_registration.entity.CoursePrerequisite;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CoursePrerequisiteRepository extends JpaRepository<CoursePrerequisite, Long> {

    List<CoursePrerequisite> findByCourseCourseCode(String courseCode);
}
