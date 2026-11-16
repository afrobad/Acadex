import { useEffect, useState } from 'react';

function cardState(c, isEnrolled) {
    if (c.alreadyCompleted) return ['completed', 'Completed'];
    if (isEnrolled) return ['enrolled', 'Enrolled'];
    if (c.eligible) return ['eligible', 'Eligible'];
    return ['blocked', 'Blocked'];
}

export default function CourseEligibilityTab({
    courses = [],
    term = 'Fall 2026',
    onEnrollmentChange
}) {
    const [enrolledCourses, setEnrolledCourses] = useState(() => new Set());

    useEffect(() => {
        setEnrolledCourses(new Set());
    }, [courses]);

    const handleCourseClick = (course) => {
        if (!course.eligible || course.alreadyCompleted) {
            return;
        }

        const isCurrentlyEnrolled = enrolledCourses.has(course.courseCode);
        const nextStatus = isCurrentlyEnrolled ? 'ELIGIBLE' : 'ENROLLED';

        setEnrolledCourses(prev => {
            const updated = new Set(prev);
            if (isCurrentlyEnrolled) {
                updated.delete(course.courseCode);
            } else {
                updated.add(course.courseCode);
            }
            return updated;
        });

        onEnrollmentChange?.({
            courseCode: course.courseCode,
            status: nextStatus,
            term
        });
    };

    const counts = courses.reduce((acc, c) => {
        if (c.alreadyCompleted) {
            // Completed is ignored or can be skipped since we only show 3
        } else if (enrolledCourses.has(c.courseCode)) {
            acc.enrolled++;
        } else if (c.eligible) {
            acc.eligible++;
        } else {
            acc.blocked++;
        }
        return acc;
    }, {
        enrolled: 0,
        eligible: 0,
        blocked: 0
    });

    return (
        <div>
            {/* Semester Header */}
            <div className="sa-semester-header">
                <div>
                    <span className="sa-muted">Current Registration Semester</span>
                    <h3>{term}</h3>
                </div>
                <span className="sa-semester-badge">Current Semester</span>
            </div>

            {/* Course Summary (3 items adjusted) */}
            <div className="sa-course-summary-3">
                <div>
                    <b>{counts.eligible}</b>
                    <span>Eligible</span>
                </div>
                <div>
                    <b>{counts.enrolled}</b>
                    <span>Enrolled</span>
                </div>
                <div>
                    <b>{counts.blocked}</b>
                    <span>Blocked</span>
                </div>
            </div>

            <p className="sa-note">
                Prerequisites are evaluated against the student&apos;s
                academic history. Select an eligible course to
                enroll the student. Select an enrolled course
                again to revert its status.
            </p>

            {!courses.length && (
                <p className="sa-empty">
                    No courses are offered to this student&apos;s batch in {term}.
                </p>
            )}

            {/* Course List */}
            <div className="sa-list">
                {courses.map((c) => {
                    const isEnrolled = enrolledCourses.has(c.courseCode);
                    const [key, label] = cardState(c, isEnrolled);

                    const prereqs = c.prerequisites || [];
                    const missing = c.missingPrerequisites || [];
                    const failed = c.failedPrerequisites || [];
                    const clickable = key !== 'blocked';

                    return (
                        <button
                            type="button"
                            className={`sa-course sa-course-${key}`}
                            key={c.courseCode}
                            onClick={() => handleCourseClick(c)}
                            disabled={!clickable}
                            aria-label={`${c.courseCode}: ${label}`}
                            style={{
                                width: '100%',
                                textAlign: 'left',
                                cursor: clickable ? 'pointer' : 'not-allowed'
                            }}
                        >
                            <div className="sa-course-content">
                                <h4>
                                    <b>{c.courseCode}</b>
                                    {' · '}
                                    {c.courseName}
                                </h4>

                                <p className="sa-prereq">
                                    Prerequisites:{' '}
                                    {prereqs.length ? prereqs.join(', ') : 'None'}
                                </p>

                                {missing.length > 0 && (
                                    <p className="sa-bad">
                                        Missing: {missing.join(', ')}
                                    </p>
                                )}

                                {failed.length > 0 && (
                                    <p className="sa-bad">
                                        Failed: {failed.join(', ')}
                                    </p>
                                )}

                                {key === 'blocked' && (
                                    <p className="sa-bad">
                                        Student does not satisfy all prerequisites.
                                    </p>
                                )}

                                {key === 'eligible' && (
                                    <p className="sa-good">
                                        All requirements satisfied. Click to enroll.
                                    </p>
                                )}

                                {key === 'enrolled' && (
                                    <p className="sa-good">
                                        Enrolled in {term}. Click to revert.
                                    </p>
                                )}

                                {key === 'completed' && (
                                    <p className="sa-muted">
                                        Already completed.
                                    </p>
                                )}
                            </div>

                            <span className={`sa-badge sa-badge-${key}`}>
                                {label}
                            </span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}