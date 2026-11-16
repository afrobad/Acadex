package com.Afrobad.Acadex.features.course_registration.dto;

import java.util.List;

public record StudentRegistrationOverviewResponse(
        StudentProfileResponse student,
        AcademicSummaryResponse summary,
        List<AcademicHistoryResponse> academicHistory,
        List<CourseEligibilityResponse> courseEligibility
) {}
