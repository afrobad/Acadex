package com.Afrobad.Acadex.features.course_registration.controller;

import com.Afrobad.Acadex.features.course_registration.dto.StudentRegistrationOverviewResponse;
import com.Afrobad.Acadex.features.course_registration.service.CourseRegistrationService;

import lombok.RequiredArgsConstructor;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/faculty/course-registration")
@RequiredArgsConstructor
public class CourseRegistrationController {

    private final CourseRegistrationService courseRegistrationService;

    @GetMapping("/students/{studentId}")
    public StudentRegistrationOverviewResponse getStudentRegistrationOverview(
            @PathVariable String studentId,

            @RequestParam(defaultValue = "2026")
            String academicYear,

            @RequestParam(defaultValue = "Fall")
            String semester
    ) {

        return courseRegistrationService.getStudentRegistrationOverview(
                studentId,
                academicYear,
                semester
        );
    }
}
