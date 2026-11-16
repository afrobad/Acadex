
import { NavLink } from 'react-router-dom';

import {
    GraduationCap,
    LayoutDashboard,
    BookOpenCheck,
    Activity,
    ShieldAlert,
    BrainCircuit,
    LogOut
} from 'lucide-react';

import { useAuth } from '../../context/AuthContext';

const links = [
    ['/dashboard', 'Dashboard', LayoutDashboard],
    ['/registration', 'Course registration', BookOpenCheck],
    ['/performance', 'Performance analysis', Activity],
    ['/early-warnings', 'Early warnings', ShieldAlert],
    ['/ai-advisor', 'AI academic advisor', BrainCircuit]
];

export default function Sidebar() {
    const { signOut } = useAuth();

    return (
        <aside className="sidebar">

            <div className="logo">
                <GraduationCap />
                acadex<span>.</span>
            </div>

            <small>WORKSPACE</small>

            <nav>
                {links.map(([to, label, Icon]) => (
                    <NavLink key={to} to={to}>
                        <Icon size={18} />
                        {label}
                    </NavLink>
                ))}
            </nav>

            <button className="logout" onClick={signOut}>
                <LogOut size={17} />
                Sign out
            </button>

        </aside>
    );
}
