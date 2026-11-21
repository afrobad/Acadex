package com.Afrobad.Acadex.features.performance_analysis.dto;
import java.math.BigDecimal;
import java.util.List;

public record PerformanceProfileResponse(
        String studentId,
        String fullName,
        String department,
        Integer currentSemester,
        String term,
        BigDecimal attendance,
        BigDecimal quiz,
        BigDecimal midterm,
        BigDecimal lab,
        int missingAssessments,
        /** URGENT_REVIEW, MONITOR or ON_TRACK */
        String alertLevel,
        List<String> alerts,
        String recommendation,
        int attendanceThreshold,
        int componentThreshold
) {}