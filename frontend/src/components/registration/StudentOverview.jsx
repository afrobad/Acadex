import { useNavigate } from 'react-router-dom';

const STATUS_LABEL = {
    ACTIVE: 'Active',
    INACTIVE: 'Inactive',
    DROPPED_OUT: 'Dropped out'
};

export default function StudentOverview({ student, summary }) {
    const navigate = useNavigate();

    const initials = (student.fullName || '?')
        .split(' ')
        .map((w) => w[0])
        .slice(0, 2)
        .join('')
        .toUpperCase();

    const status = student.status || 'ACTIVE';

    return (
        <section className="sa-card sa-overview">

            <div className="sa-overview-head">
                <div className="sa-avatar">{initials}</div>

                <div>
                    <h3>{student.fullName}</h3>
                    <p>
                        {student.studentId}
                        {student.department ? ` · ${student.department}` : ''}
                        {student.currentSemester
                            ? ` · Semester ${student.currentSemester}`
                            : ''}
                    </p>

                    <div className="sa-pills">
                        <span className={`sa-pill sa-status-${status.toLowerCase()}`}>
                            {STATUS_LABEL[status] || status}
                        </span>
                    </div>
                </div>
            </div>

            <div className="sa-metrics">
                <div className="sa-metric">
                    <span>CGPA</span>
                    <strong>{Number(summary.cgpa).toFixed(2)}/4</strong>
                </div>

                <div className="sa-metric">
                    <span>Completed credits</span>
                    <strong>{Number(summary.creditsCompleted)}</strong>
                </div>
            </div>

            <div className="sa-overview-actions">
                <button
                    type="button"
                    className="sa-link-btn"
                    onClick={() =>
                        navigate(`/performance?studentId=${encodeURIComponent(student.studentId)}`)
                    }
                >
                    View academic performance →
                </button>
            </div>

        </section>
    );
}