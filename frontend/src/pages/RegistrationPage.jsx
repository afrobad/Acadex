
import { useState } from 'react';

import { apiRequest } from '../services/api';

import StudentSearch from '../components/registration/StudentSearch';
import StudentProfile from '../components/registration/StudentProfile';
import AcademicHistory from '../components/registration/AcademicHistory';
import CourseEligibility from '../components/registration/CourseEligibility';

export default function RegistrationPage() {

    const [id, setId] = useState('');
    const [data, setData] = useState(null);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);

    async function search(e) {
        e.preventDefault();

        setBusy(true);
        setError('');
        setData(null);

        try {
            const response = await apiRequest(
                `/faculty/course-registration/students/${encodeURIComponent(id.trim())}`
            );

            setData(response);

        } catch (x) {
            setError(x.message);

        } finally {
            setBusy(false);
        }
    }

    const student =
        data?.student ||
        data?.studentProfile ||
        data;

    return (
        <>
            <section className="panel">

                <h3>Find a student</h3>

                <p className="muted">
                    Search using the university student ID
                </p>

                <StudentSearch
                    value={id}
                    onChange={setId}
                    onSearch={search}
                    loading={busy}
                />

                {error && (
                    <p className="error">
                        {error}
                    </p>
                )}

            </section>

            {data && (
                <>
                    <StudentProfile
                        student={student}
                    />

                    <div className="columns">

                        <AcademicHistory
                            courses={
                                data.academicHistory ||
                                data.courses ||
                                []
                            }
                        />

                        <CourseEligibility
                            courses={
                                data.courseEligibility ||
                                data.eligibleCourses ||
                                []
                            }
                        />

                    </div>
                </>
            )}

            {!data && (
                <p className="empty">
                    Enter a student ID to retrieve academic history.
                    This page expects a protected Spring Boot endpoint;
                    update the path to match your controller.
                </p>
            )}
        </>
    );
}
