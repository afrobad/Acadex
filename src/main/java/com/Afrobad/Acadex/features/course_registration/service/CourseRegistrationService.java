package com.Afrobad.Acadex.features.course_registration.service;

import com.Afrobad.Acadex.features.course_registration.dto.*;
import com.Afrobad.Acadex.features.course_registration.entity.*;
import com.Afrobad.Acadex.features.course_registration.enums.StudentCourseStatus;
import com.Afrobad.Acadex.features.course_registration.enums.StudentStatus;
import com.Afrobad.Acadex.features.course_registration.repository.*;

import lombok.RequiredArgsConstructor;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class CourseRegistrationService {

    /** Used when a student has no totalProgramCredits configured. */
    private static final int DEFAULT_PROGRAM_CREDITS = 145;

    private final StudentRepository studentRepository;
    private final StudentCourseRepository studentCourseRepository;
    private final CourseOfferingRepository courseOfferingRepository;
    private final CoursePrerequisiteRepository coursePrerequisiteRepository;

    public StudentRegistrationOverviewResponse getStudentRegistrationOverview(
            String studentId,
            String academicYear,
            String semester
    ) {

        Student student = studentRepository.findByStudentId(studentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Student not found: " + studentId
                ));

        List<StudentCourse> studentCourses =
                studentCourseRepository.findByStudentStudentId(studentId);

        Set<String> completedCourseCodes = codesWithStatus(
                studentCourses, StudentCourseStatus.COMPLETED);

        Set<String> enrolledCourseCodes = codesWithStatus(
                studentCourses, StudentCourseStatus.ENROLLED);

        Map<String, StudentCourse> latestAttempt = latestAttemptPerCourse(studentCourses);

        List<AcademicHistoryResponse> academicHistory = studentCourses.stream()
                .sorted(Comparator
                        .comparing((StudentCourse sc) -> nullSafe(sc.getAcademicYear()))
                        .thenComparing(sc -> nullSafe(sc.getCourse().getCourseCode())))
                .map(this::toHistory)
                .toList();

        List<CourseOffering> offerings =
                courseOfferingRepository
                        .findBySemesterAndAcademicYearAndBatchAndActiveTrue(
                                semester,
                                academicYear,
                                student.getBatch()
                        );

        List<CourseEligibilityResponse> eligibility = offerings.stream()
                .map(offering -> buildEligibility(
                        offering.getCourse(),
                        completedCourseCodes,
                        enrolledCourseCodes,
                        latestAttempt
                ))
                .toList();

        StudentProfileResponse profile = new StudentProfileResponse(
                student.getStudentId(),
                student.getFullName(),
                student.getDepartment(),
                student.getBatch(),
                student.getCurrentSemester(),
                student.getProgramName(),
                (student.getStatus() == null
                        ? StudentStatus.ACTIVE
                        : student.getStatus()).name()
        );

        return new StudentRegistrationOverviewResponse(
                profile,
                buildSummary(student, studentCourses, latestAttempt,
                        academicYear, semester),
                academicHistory,
                eligibility
        );
    }

    // ---------------------------------------------------------------- summary

    private AcademicSummaryResponse buildSummary(
            Student student,
            List<StudentCourse> studentCourses,
            Map<String, StudentCourse> latestAttempt,
            String academicYear,
            String semester
    ) {

        // CGPA = credit-weighted average over each course's latest graded attempt.
        BigDecimal weightedPoints = BigDecimal.ZERO;
        BigDecimal gradedCredits = BigDecimal.ZERO;

        for (StudentCourse sc : latestAttempt.values()) {
            boolean graded = sc.getStatus() == StudentCourseStatus.COMPLETED
                    || sc.getStatus() == StudentCourseStatus.FAILED;
            if (!graded) continue;

            BigDecimal credits = sc.getCourse().getCredits();
            BigDecimal point = sc.getStatus() == StudentCourseStatus.FAILED
                    || sc.getGradePoint() == null
                    ? BigDecimal.ZERO
                    : sc.getGradePoint();

            weightedPoints = weightedPoints.add(point.multiply(credits));
            gradedCredits = gradedCredits.add(credits);
        }

        BigDecimal cgpa = gradedCredits.signum() == 0
                ? BigDecimal.ZERO.setScale(2)
                : weightedPoints.divide(gradedCredits, 2, RoundingMode.HALF_UP);

        // Credits completed = credits of each distinct course the student passed.
        BigDecimal creditsCompleted = studentCourses.stream()
                .filter(sc -> sc.getStatus() == StudentCourseStatus.COMPLETED)
                .collect(Collectors.toMap(
                        sc -> sc.getCourse().getCourseCode(),
                        sc -> sc.getEarnedCredits() != null
                                ? sc.getEarnedCredits()
                                : sc.getCourse().getCredits(),
                        BigDecimal::max))
                .values().stream()
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal total = BigDecimal.valueOf(
                student.getTotalProgramCredits() != null
                        ? student.getTotalProgramCredits()
                        : DEFAULT_PROGRAM_CREDITS);

        BigDecimal remaining = total.subtract(creditsCompleted).max(BigDecimal.ZERO);

        int percent = total.signum() == 0
                ? 0
                : creditsCompleted.multiply(BigDecimal.valueOf(100))
                        .divide(total, 0, RoundingMode.HALF_UP)
                        .min(BigDecimal.valueOf(100))
                        .intValue();

        return new AcademicSummaryResponse(
                cgpa,
                creditsCompleted,
                remaining,
                total,
                percent,
                semester + " " + academicYear
        );
    }

    // --------------------------------------------------------------- history

    private AcademicHistoryResponse toHistory(StudentCourse sc) {
        return new AcademicHistoryResponse(
                sc.getCourse().getCourseCode(),
                sc.getCourse().getCourseTitle(),
                sc.getCourse().getCredits(),
                sc.getStatus().name(),
                displayStatus(sc),
                sc.getGradePoint(),
                letterGrade(sc),
                sc.getEarnedCredits(),
                sc.getAcademicYear(),
                sc.getSemester(),
                sc.getAttemptNumber()
        );
    }

    private String displayStatus(StudentCourse sc) {
        boolean retake = sc.getAttemptNumber() != null && sc.getAttemptNumber() > 1;

        return switch (sc.getStatus()) {
            case COMPLETED -> "COMPLETED";
            case FAILED -> "FAILED";
            case DROPPED -> "DROPPED";
            case INCOMPLETE -> "NOT_COMPLETED";
            case ENROLLED -> retake ? "RETAKE" : "ENROLLED";
        };
    }

    /** 4.00 scale. Failed attempts show F; dropped courses show W. */
    private String letterGrade(StudentCourse sc) {
        if (sc.getStatus() == StudentCourseStatus.FAILED) return "F";
        if (sc.getStatus() == StudentCourseStatus.DROPPED) return "W";
        if (sc.getGradePoint() == null) return null;

        double gp = sc.getGradePoint().doubleValue();
        if (gp >= 4.00) return "A+";
        if (gp >= 3.75) return "A";
        if (gp >= 3.50) return "A-";
        if (gp >= 3.25) return "B+";
        if (gp >= 3.00) return "B";
        if (gp >= 2.75) return "B-";
        if (gp >= 2.50) return "C+";
        if (gp >= 2.25) return "C";
        if (gp >= 2.00) return "D";
        return "F";
    }

    // ----------------------------------------------------------- eligibility

    private CourseEligibilityResponse buildEligibility(
            Course course,
            Set<String> completedCourseCodes,
            Set<String> enrolledCourseCodes,
            Map<String, StudentCourse> latestAttempt
    ) {

        String courseCode = course.getCourseCode();

        List<String> prerequisiteCodes = coursePrerequisiteRepository
                .findByCourseCourseCode(courseCode).stream()
                .map(cp -> cp.getPrerequisiteCourse().getCourseCode())
                .toList();

        // A prerequisite is satisfied only when its course is COMPLETED.
        List<String> missingPrerequisites = prerequisiteCodes.stream()
                .filter(code -> !completedCourseCodes.contains(code))
                .toList();

        boolean alreadyCompleted = completedCourseCodes.contains(courseCode);
        boolean alreadyEnrolled = enrolledCourseCodes.contains(courseCode);

        // No prerequisites => missingPrerequisites is empty => eligible.
        boolean eligible = missingPrerequisites.isEmpty()
                && !alreadyCompleted
                && !alreadyEnrolled;

        StudentCourse previous = latestAttempt.get(courseCode);

        return new CourseEligibilityResponse(
                courseCode,
                course.getCourseTitle(),
                course.getCredits(),
                eligible,
                prerequisiteCodes,
                missingPrerequisites,
                alreadyCompleted,
                alreadyEnrolled,
                previous == null ? null : displayStatus(previous)
        );
    }

    // --------------------------------------------------------------- helpers

    private Set<String> codesWithStatus(List<StudentCourse> list, StudentCourseStatus status) {
        return list.stream()
                .filter(sc -> sc.getStatus() == status)
                .map(sc -> sc.getCourse().getCourseCode())
                .collect(Collectors.toSet());
    }

    private Map<String, StudentCourse> latestAttemptPerCourse(List<StudentCourse> list) {
        return list.stream().collect(Collectors.toMap(
                sc -> sc.getCourse().getCourseCode(),
                sc -> sc,
                (a, b) -> attempt(a) >= attempt(b) ? a : b
        ));
    }

    private int attempt(StudentCourse sc) {
        return sc.getAttemptNumber() == null ? 1 : sc.getAttemptNumber();
    }

    private String nullSafe(String s) {
        return s == null ? "" : s;
    }
}