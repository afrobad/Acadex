package com.Afrobad.Acadex.features.performance_analysis.controller;

import com.Afrobad.Acadex.features.performance_analysis.dto.PerformanceProfileResponse;
import com.Afrobad.Acadex.features.performance_analysis.service.PerformanceService;

import lombok.RequiredArgsConstructor;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/faculty/performance")
@RequiredArgsConstructor
public class PerformanceController {

    private final PerformanceService performanceService;

    @GetMapping("/students/{studentId}")
    public PerformanceProfileResponse getStudentPerformance(
            @PathVariable String studentId,

            @RequestParam(defaultValue = "2026")
            String academicYear,

            @RequestParam(defaultValue = "Fall")
            String semester
    ) {
        return performanceService.getProfile(studentId, academicYear, semester);
    }
}