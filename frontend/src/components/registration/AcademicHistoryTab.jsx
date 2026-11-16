import { useState } from 'react';

// backend displayStatus -> css/label key
const KEY = {
    COMPLETED: 'completed',
    NOT_COMPLETED: 'not-completed',
    FAILED: 'failed',
    DROPPED: 'dropped',
    RETAKE: 'retake',
    ENROLLED: 'enrolled'
};

const FILTERS = [
    ['all', 'All'],
    ['completed', 'Completed'],
    ['not-completed', 'Not completed'],
    ['failed', 'Failed'],
    ['dropped', 'Dropped'],
    ['retake', 'Retake']
];

export default function AcademicHistoryTab({ history = [] }) {
    const [filter, setFilter] = useState('all');

    if (!history.length) {
        return <p className="sa-empty">No academic history recorded.</p>;
    }

    const rows = history.map((h) => ({
        ...h,
        key: KEY[h.displayStatus] || 'enrolled'
    }));

    const count = (k) =>
        k === 'all' ? rows.length : rows.filter((r) => r.key === k).length;

    const visible = filter === 'all'
        ? rows
        : rows.filter((r) => r.key === filter);

    return (
        <div>

            <div className="sa-filters">
                {FILTERS
                    .filter(([k]) => k === 'all' || count(k) > 0)
                    .map(([k, label]) => (
                        <button
                            key={k}
                            type="button"
                            className={filter === k ? 'on' : ''}
                            onClick={() => setFilter(k)}
                        >
                            {label} <span>{count(k)}</span>
                        </button>
                    ))}
            </div>

            <div className="sa-table-wrap">
                <table className="sa-table">
                    <thead>
                        <tr>
                            <th>Code</th>
                            <th>Course</th>
                            <th>Grade</th>
                            <th>Status</th>
                        </tr>
                    </thead>

                    <tbody>
                        {visible.map((h, i) => {
                            const term = [h.semester, h.academicYear]
                                .filter(Boolean)
                                .join(' ');

                            const meta = [
                                h.credits != null ? `${Number(h.credits)} cr` : null,
                                term || null,
                                h.attemptNumber > 1
                                    ? `attempt ${h.attemptNumber}`
                                    : null
                            ].filter(Boolean).join(' · ');

                            return (
                                <tr key={`${h.courseCode}-${h.attemptNumber}-${i}`}>
                                    <td className="sa-code">{h.courseCode}</td>

                                    <td>
                                        <div>{h.courseName}</div>
                                        {meta && (
                                            <div className="sa-sub">{meta}</div>
                                        )}
                                    </td>

                                    <td className="sa-grade">
                                        {h.letterGrade || '—'}
                                    </td>

                                    <td>
                                        <span className={`sa-badge sa-badge-${h.key}`}>
                                            {h.key}
                                        </span>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {!visible.length && (
                <p className="sa-empty">No courses with this status.</p>
            )}

        </div>
    );
}

