import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { apiRequest } from '../services/api';

import PerformanceProfile from '../components/performance/PerformanceProfile';

import '../styles/studentAcademic.css';
import '../styles/performanceProfile.css';

export default function PerformancePage() {

    const [params, setParams] = useSearchParams();
    const urlId = params.get('studentId') || '';

    const [id, setId] = useState(urlId);
    const [profile, setProfile] = useState(null);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);

    const load = useCallback(async (studentId) => {
        setBusy(true);
        setError('');
        setProfile(null);

        try {
            setProfile(await apiRequest(
                `/faculty/performance/students/${encodeURIComponent(studentId)}`
                + '?academicYear=2026&semester=Fall'
            ));
        } catch (x) {
            setError(x.message);
        } finally {
            setBusy(false);
        }
    }, []);

    // Opened from Course Registration (?studentId=...): load right away.
    // Opened from the sidebar (no id): show only the search bar.
    useEffect(() => {
        setId(urlId);

        if (urlId) {
            load(urlId);
        } else {
            setProfile(null);
            setError('');
        }
    }, [urlId, load]);

    function search(e) {
        e.preventDefault();

        const next = id.trim();
        if (!next) return;

        if (next === urlId) {
            load(next);            // same id: just refresh
        } else {
            setParams({ studentId: next });
        }
    }

    return (
        <div className="sa">

            <form className="sa-card sa-search" onSubmit={search}>

                <input
                    value={id}
                    onChange={(e) => setId(e.target.value)}
                    placeholder="Student ID, e.g. 241-35-088"
                    required
                />

                <button disabled={busy}>
                    {busy ? 'Loading…' : 'Analyze'}
                </button>

            </form>

            {urlId && (
                <p className="sp-back">
                    <Link to="/registration">← Back to course registration</Link>
                </p>
            )}

            {error && <p className="sa-error">{error}</p>}

            {!urlId && !error && (
                <p className="sa-empty">
                    Enter a student ID to see their performance analysis.
                </p>
            )}

            {busy && !profile && !error && (
                <p className="sa-empty">Loading performance analysis…</p>
            )}

            {profile && (
                <div className="sp-wrap">
                    <PerformanceProfile profile={profile} />
                </div>
            )}

        </div>
    );
}