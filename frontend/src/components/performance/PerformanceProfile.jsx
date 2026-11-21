import { useState } from 'react';
import { Mail, LifeBuoy } from 'lucide-react';

const LEVEL = {
    URGENT_REVIEW: ['Urgent review', 'urgent'],
    MONITOR: ['Monitor', 'monitor'],
    ON_TRACK: ['On track', 'ontrack']
};

function Bar({ label, value, threshold }) {
    const v = Math.round(Number(value));
    const low = v < threshold;

    return (
        <div className="sp-row">
            <div className="sp-row-head">
                <span>{label}</span>
                <b>{v}%</b>
            </div>
            <div className="sp-track">
                <i
                    className={low ? 'low' : ''}
                    style={{ width: `${Math.min(100, Math.max(0, v))}%` }}
                />
            </div>
        </div>
    );
}

export default function PerformanceProfile({ profile }) {
    const [requested, setRequested] = useState(false);

    const [levelLabel, levelKey] = LEVEL[profile.alertLevel] || LEVEL.ON_TRACK;

    const hasIssues = profile.alertLevel !== 'ON_TRACK';

    const emailHref =
        'mailto:?subject=' +
        encodeURIComponent(`Academic performance update (${profile.term})`) +
        '&body=' +
        encodeURIComponent(
            `Dear ${profile.fullName},\n\n` +
            `I am writing about your performance in ${profile.term}:\n\n` +
            `- Attendance: ${Math.round(profile.attendance)}%\n` +
            `- Quiz: ${Math.round(profile.quiz)}%\n` +
            `- Midterm: ${Math.round(profile.midterm)}%\n` +
            `- Lab: ${Math.round(profile.lab)}%\n\n` +
            (hasIssues
                ? 'Points of concern:\n' + profile.alerts.map((a) => `- ${a}`).join('\n') + '\n\n'
                : '') +
            'Please get in touch if you would like to discuss this.\n\nRegards'
        );

    return (
        <section className="sa-card sp-card">

            <div className="sp-head">
                <div>
                    <h3>Performance Profile · {profile.fullName}</h3>
                    <p>
                        {profile.studentId}
                        {profile.department ? ` · ${profile.department}` : ''}
                        {' · '}{profile.term}
                    </p>
                </div>

                <span className={`sp-level sp-level-${levelKey}`}>
                    {levelLabel}
                </span>
            </div>

            <div className="sp-body">

                <div className="sp-bars">
                    <Bar label="Attendance" value={profile.attendance} threshold={profile.attendanceThreshold} />
                    <Bar label="Quiz"       value={profile.quiz}       threshold={profile.componentThreshold} />
                    <Bar label="Midterm"    value={profile.midterm}    threshold={profile.componentThreshold} />
                    <Bar label="Lab"        value={profile.lab}        threshold={profile.componentThreshold} />
                </div>

                <div className="sp-alerts">
                    <h4>Explainable alerts</h4>

                    <ul>
                        {profile.alerts.map((a) => (
                            <li key={a}>
                                {hasIssues && <span className="sp-warn">⚠</span>}
                                {a}
                            </li>
                        ))}
                    </ul>

                    <p className="sp-reco">{profile.recommendation}</p>
                </div>

            </div>

            <div className="sp-actions">
                <a className="sp-btn sp-btn-primary" href={emailHref}>
                    <Mail size={15} /> Draft student email
                </a>

                <button
                    type="button"
                    className="sp-btn"
                    onClick={() => setRequested(true)}
                    disabled={requested}
                >
                    <LifeBuoy size={15} />
                    {requested ? 'Counselling requested' : 'Request counselling'}
                </button>
            </div>

            {requested && (
                <p className="sa-note sp-note">
                    Marked as requested on this screen only. It is not saved or
                    sent anywhere yet.
                </p>
            )}

        </section>
    );
}