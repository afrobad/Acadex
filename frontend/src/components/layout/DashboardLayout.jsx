
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

const pages = {
    '/dashboard': [
        'Dashboard',
        'Your academic workspace at a glance'
    ],
    '/registration': [
        'Course registration',
        'Review academic history and verify prerequisites'
    ],
    '/performance': [
        'Performance analysis',
        'Understand student academic performance'
    ],
    '/early-warnings': [
        'Early warnings',
        'Identify students who may need support'
    ],
    '/ai-advisor': [
        'AI academic advisor',
        'Academic information assistance'
    ]
};

export default function DashboardLayout() {
    const [t, s] = pages[useLocation().pathname] || pages['/dashboard'];

    return (
        <div className='shell'>
            <Sidebar />

            <div className='main'>
                <Topbar
                    title={t}
                    subtitle={s}
                />

                <main className='content'>
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
