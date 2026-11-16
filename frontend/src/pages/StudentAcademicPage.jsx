import { useState } from 'react';
import { Search } from 'lucide-react';

import { apiRequest } from '../services/api';

import StudentOverview from '../components/registration/StudentOverview';
import CourseEligibilityTab from '../components/registration/CourseEligibilityTab';
import AcademicHistoryTab from '../components/registration/AcademicHistoryTab';
import CreditProgressTab from '../components/registration/CreditProgressTab';

import '../styles/studentAcademic.css';

const TABS = [
    ['eligibility', 'Course Eligibility'],
    ['history', 'Academic History'],
    ['credits', 'Credit Progress']
];

export default function StudentAcademicPage() {
    const [id, setId] = useState('');
    const [data, setData] = useState(null);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    const [tab, setTab] = useState('eligibility');

    async function search(e) {
        e.preventDefault();
        setBusy(true);
        setError('');
        setData(null);

        try {
            setData(await apiRequest(
                `/faculty/course-registration/students/${encodeURIComponent(id.trim())}`
                + '?academicYear=2026&semester=Fall'
            ));
            setTab('eligibility');
        } catch (x) {
            setError(x.message);
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="sa">
            <form className="sa-card sa-search" onSubmit={search}>
                <Search size={16} />
                <input
                    value={id}
                    onChange={(e) => setId(e.target.value)}
                    placeholder="Student ID, e.g. 241-35-088"
                    required
                />
                <button disabled={busy}>
                    {busy ? 'Searching…' : 'Search'}
                </button>
            </form>

            {error && <p className="sa-error">{error}</p>}

            {!data && !error && (
                <p className="sa-empty">
                    Enter a student ID to view their academic profile.
                </p>
            )}

            {data && (
                <div className="sa-grid">
                    <StudentOverview
                        student={data.student}
                        summary={data.summary}
                    />

                    <section className="sa-card">
                        <div className="sa-tabs" role="tablist">
                            {TABS.map(([key, label]) => (
                                <button
                                    key={key}
                                    role="tab"
                                    aria-selected={tab === key}
                                    className={tab === key ? 'on' : ''}
                                    onClick={() => setTab(key)}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>

                        {tab === 'eligibility' && (
                            <CourseEligibilityTab
                                courses={data.courseEligibility}
                                term={data.summary.currentTerm}
                            />
                        )}
                        {tab === 'history' && (
                            <AcademicHistoryTab history={data.academicHistory} />
                        )}
                        {tab === 'credits' && (
                            <CreditProgressTab summary={data.summary} />
                        )}
                    </section>
                </div>
            )}
        </div>
    );
}