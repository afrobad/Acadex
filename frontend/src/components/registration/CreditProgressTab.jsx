export default function CreditProgressTab({ summary }) {
    const done = Number(summary.creditsCompleted);
    const total = Number(summary.totalProgramCredits);

    return (
        <div>
            <h4 className="sa-h">Credit completion</h4>
            <p className="sa-note">{total}-credit curriculum</p>

            <div className="sa-progress-row">
                <span>{done} / {total} credits</span>
                <span>{summary.completionPercent}%</span>
            </div>
            <div
                className="sa-bar"
                role="progressbar"
                aria-valuenow={summary.completionPercent}
                aria-valuemin={0}
                aria-valuemax={100}
            >
                <i style={{ width: `${summary.completionPercent}%` }} />
            </div>

            <div className="sa-metrics sa-metrics-spaced">
                <div className="sa-metric">
                    <span>Credits remaining</span>
                    <strong>{Number(summary.creditsRemaining)}</strong>
                </div>
                <div className="sa-metric">
                    <span>Current CGPA</span>
                    <strong>{Number(summary.cgpa).toFixed(2)}</strong>
                </div>
            </div>
        </div>
    );
}
