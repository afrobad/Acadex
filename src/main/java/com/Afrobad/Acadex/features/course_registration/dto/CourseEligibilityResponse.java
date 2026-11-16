package com.Afrobad.Acadex.features.course_registration.dto;

import java.math.BigDecimal;
import java.util.List;

public record CourseEligibilityResponse(
        String courseCode,
        String courseName,
        BigDecimal credits,
        boolean eligible,
        List<String> missingPrerequisites,
        boolean alreadyCompleted,
        boolean alreadyEnrolled,
        String previousStatus
) {}
