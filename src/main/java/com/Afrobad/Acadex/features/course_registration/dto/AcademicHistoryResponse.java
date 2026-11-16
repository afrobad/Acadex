package com.Afrobad.Acadex.features.course_registration.dto;

import java.math.BigDecimal;

public record AcademicHistoryResponse(
        String courseCode,
        String courseName,
        BigDecimal credits,
        String status,
        String displayStatus,
        BigDecimal gradePoint,
        String letterGrade,
        BigDecimal earnedCredits,
        String academicYear,
        String semester,
        Integer attemptNumber
) {}
