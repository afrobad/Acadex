package com.Afrobad.Acadex.features.course_registration.service;

import com.Afrobad.Acadex.features.course_registration.dto.*;
import com.Afrobad.Acadex.features.course_registration.entity.*;
import com.Afrobad.Acadex.features.course_registration.enums.StudentCourseStatus;
import com.Afrobad.Acadex.features.course_registration.repository.*;

import lombok.RequiredArgsConstructor;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class CourseRegistrationService {

    private final StudentRepository studentRepository;
    private final StudentCourseRepository studentCourseRepository;
    private final CourseOfferingRepository courseOfferingRepository;
    private final CoursePrerequisiteRepository coursePrerequisiteRepository;

    public StudentRegistrationOverviewResponse getStudentRegistrationOverview(
            String studentId,
            String academicYear,
            String semester
    ) {

        // 1. Find the student.
        Student student = studentRepository.findByStudentId(studentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Student not found: " + studentId
                ));

        // 2. Retrieve the student's complete course history.
        List<StudentCourse> studentCourses =
                studentCourseRepository.findByStudentStudentId(studentId);

        // 3. Collect courses completed by this student.
        Set<String> completedCourseCodes = studentCourses.stream()
                .filter(sc -> sc.getStatus() == StudentCourseStatus.COMPLETED)
                .map(sc -> sc.getCourse().getCourseCode())
                .collect(Collectors.toSet());

        // 4. Collect course codes already enrolled by this student.
        Set<String> enrolledCourseCodes = studentCourses.stream()
                .filter(sc -> sc.getStatus() == StudentCourseStatus.ENROLLED)
                .map(sc -> sc.getCourse().getCourseCode())
                .collect(Collectors.toSet());

        // 5. Convert academic history entities into DTOs.
        List<AcademicHistoryResponse> academicHistory =
                studentCourses.stream()
                        .map(sc -> new AcademicHistoryResponse(
                                sc.getCourse().getCourseCode(),
                                sc.getCourse().getCourseTitle(),
                                sc.getCourse().getCredits(),
                                sc.getStatus().name(),
                                sc.getGradePoint(),
                                sc.getEarnedCredits(),
                                sc.getAcademicYear(),
                                sc.getSemester(),
                                sc.getAttemptNumber()
                        ))
                        .toList();

        // 6. Retrieve active offerings for this student's batch.
        List<CourseOffering> offerings =
                courseOfferingRepository
                        .findBySemesterAndAcademicYearAndBatchAndActiveTrue(
                                semester,
                                academicYear,
                                student.getBatch()
                        );

        // 7. Build course eligibility results.
        List<CourseEligibilityResponse> eligibility =
                offerings.stream()
                        .map(offering -> buildEligibility(
                                offering.getCourse(),
                                completedCourseCodes,
                                enrolledCourseCodes
                        ))
                        .toList();

        // 8. Return the complete response.
        StudentProfileResponse studentProfile =
                new StudentProfileResponse(
                        student.getStudentId(),
                        student.getFullName(),
                        student.getDepartment(),
                        student.getBatch(),
                        student.getCurrentSemester(),
                        student.getProgramName()
                );

        return new StudentRegistrationOverviewResponse(
                studentProfile,
                academicHistory,
                eligibility
        );
    }

    private CourseEligibilityResponse buildEligibility(
            Course course,
            Set<String> completedCourseCodes,
            Set<String> enrolledCourseCodes
    ) {

        String courseCode = course.getCourseCode();

        // Find prerequisites configured for this course.
        List<CoursePrerequisite> prerequisites =
                coursePrerequisiteRepository
                        .findByCourseCourseCode(courseCode);

        // A prerequisite is satisfied only when its course is COMPLETED.
        List<String> missingPrerequisites = prerequisites.stream()
                .map(cp -> cp.getPrerequisiteCourse().getCourseCode())
                .filter(prerequisiteCode ->
                        !completedCourseCodes.contains(prerequisiteCode))
                .toList();

        boolean alreadyCompleted =
                completedCourseCodes.contains(courseCode);

        boolean alreadyEnrolled =
                enrolledCourseCodes.contains(courseCode);

        boolean eligible =
                missingPrerequisites.isEmpty()
                        && !alreadyCompleted
                        && !alreadyEnrolled;

        // Find the most recent status for this course, if any.
        String previousStatus = null;

        // This is populated separately in the next refinement if
        // you want the latest attempt displayed on the eligibility card.

        return new CourseEligibilityResponse(
                courseCode,
                course.getCourseTitle(),
                course.getCredits(),
                eligible,
                missingPrerequisites,
                alreadyCompleted,
                alreadyEnrolled,
                previousStatus
        );
    }
}
