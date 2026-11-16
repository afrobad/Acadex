package com.Afrobad.Acadex.features.course_registration.dto;

public record StudentProfileResponse(
        String studentId,
        String fullName,
        String department,
        String batch,
        Integer currentSemester,
        String programName
) {}
