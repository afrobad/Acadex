package com.Afrobad.Acadex.features.course_registration.dto;

import java.math.BigDecimal;

/** Overall performance + credit progress for one student. */
public record AcademicSummaryResponse(
        BigDecimal cgpa,
        BigDecimal creditsCompleted,
        BigDecimal creditsRemaining,
        BigDecimal totalProgramCredits,
        int completionPercent,
        String currentTerm
) {}

