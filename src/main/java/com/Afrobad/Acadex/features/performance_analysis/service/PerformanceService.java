package com.Afrobad.Acadex.features.performance_analysis.service;

import com.Afrobad.Acadex.features.course_registration.entity.Student;
import com.Afrobad.Acadex.features.course_registration.repository.StudentRepository;
import com.Afrobad.Acadex.features.performance_analysis.dto.PerformanceProfileResponse;
import com.Afrobad.Acadex.features.performance_analysis.entity.StudentPerformance;
import com.Afrobad.Acadex.features.performance_analysis.repository.StudentPerformanceRepository;

import lombok.RequiredArgsConstructor;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class PerformanceService {

    // Alert thresholds (percent)
    private static final int ATTENDANCE_THRESHOLD = 60;
    private static final int COMPONENT_THRESHOLD = 45;
    // "Monitor" thresholds, softer than alert thresholds
    private static final int WATCH_ATTENDANCE = 70;
    private static final int WATCH_COMPONENT = 60;

    private final StudentRepository studentRepository;
    private final StudentPerformanceRepository performanceRepository;

    public PerformanceProfileResponse getProfile(
            String studentId,
            String academicYear,
            String semester
    ) {

        Student student = studentRepository.findByStudentId(studentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Student not found: " + studentId
                ));

        StudentPerformance p = performanceRepository
                .findByStudentStudentIdAndAcademicYearAndSemester(
                        studentId, academicYear, semester)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "No performance record for " + studentId
                                + " in " + semester + " " + academicYear
                ));

        List<String> alerts = new ArrayList<>();

        if (below(p.getAttendancePercent(), ATTENDANCE_THRESHOLD)) {
            alerts.add("Attendance below configured " + ATTENDANCE_THRESHOLD + "% threshold.");
        }
        if (below(p.getQuizPercent(), COMPONENT_THRESHOLD)) {
            alerts.add("Quiz score below " + COMPONENT_THRESHOLD + "%.");
        }
        if (below(p.getMidtermPercent(), COMPONENT_THRESHOLD)) {
            alerts.add("Midterm score below " + COMPONENT_THRESHOLD + "%.");
        }
        if (below(p.getLabPercent(), COMPONENT_THRESHOLD)) {
            alerts.add("Lab score below " + COMPONENT_THRESHOLD + "%.");
        }
        if (p.getMissingAssessments() != null && p.getMissingAssessments() > 0) {
            alerts.add(p.getMissingAssessments() + " missing assessment"
                    + (p.getMissingAssessments() == 1 ? "." : "s."));
        }

        boolean watch =
                below(p.getAttendancePercent(), WATCH_ATTENDANCE)
                || below(p.getQuizPercent(), WATCH_COMPONENT)
                || below(p.getMidtermPercent(), WATCH_COMPONENT)
                || below(p.getLabPercent(), WATCH_COMPONENT);

        String level;
        String recommendation;

        if (alerts.size() >= 2) {
            level = "URGENT_REVIEW";
            recommendation = "Faculty review and student communication recommended.";
        } else if (alerts.size() == 1 || watch) {
            level = "MONITOR";
            recommendation = "Keep monitoring this student's progress over the next few weeks.";
        } else {
            level = "ON_TRACK";
            recommendation = "No action needed. The student is performing within expected ranges.";
        }

        if (alerts.isEmpty()) {
            alerts.add("No alerts. All indicators are above configured thresholds.");
        }

        return new PerformanceProfileResponse(
                student.getStudentId(),
                student.getFullName(),
                student.getDepartment(),
                student.getCurrentSemester(),
                semester + " " + academicYear,
                p.getAttendancePercent(),
                p.getQuizPercent(),
                p.getMidtermPercent(),
                p.getLabPercent(),
                p.getMissingAssessments() == null ? 0 : p.getMissingAssessments(),
                level,
                alerts,
                recommendation,
                ATTENDANCE_THRESHOLD,
                COMPONENT_THRESHOLD
        );
    }

    private boolean below(BigDecimal value, int threshold) {
        return value != null && value.compareTo(BigDecimal.valueOf(threshold)) < 0;
    }
}