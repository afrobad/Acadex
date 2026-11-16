
import { Bell, Search } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function Topbar({ title, subtitle }) {
    const { faculty } = useAuth();

    const initials = (faculty?.fullName || 'F')
        .split(' ')
        .map((x) => x[0])
        .slice(0, 2)
        .join('')
        .toUpperCase();

    return (
        <header className="topbar">
            <div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>

            <div className="top-actions">
                <Search />
                <Bell />

                <div className="avatar">
                    {initials}
                </div>

                <div>
                    <b>{faculty?.fullName}</b>
                    <small>{faculty?.role}</small>
                </div>
            </div>
        </header>
    );
}
