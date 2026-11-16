import { Navigate, Route, Routes } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

import LoginPage from '../pages/LoginPage';
import DashboardLayout from '../components/layout/DashboardLayout';
import DashboardPage from '../pages/DashboardPage';
import RegistrationPage from '../pages/RegistrationPage';
import StudentAcademicPage from '../pages/StudentAcademicPage';
import PerformancePage from '../pages/PerformancePage';
import EarlyWarningsPage from '../pages/EarlyWarningsPage';
import AIAdvisorPage from '../pages/AIAdvisorPage';

function Guard() {
    const { isAuthenticated } = useAuth();

    return isAuthenticated
        ? <DashboardLayout />
        : <Navigate to="/login" replace />;
}

function LoginGuard() {
    const { isAuthenticated } = useAuth();

    return isAuthenticated
        ? <Navigate to="/dashboard" />
        : <LoginPage />;
}

export default function AppRoutes() {
    return (
        <Routes>

            <Route
                path="/login"
                element={<LoginGuard />}
            />

            <Route element={<Guard />}>

                <Route
                    path="/dashboard"
                    element={<DashboardPage />}
                />

                <Route
                    path="/registration"
                    element={<RegistrationPage />}
                />

                <Route
                    path="/student-academic"
                    element={<StudentAcademicPage />}
                />

                <Route
                    path="/performance"
                    element={<PerformancePage />}
                />

                <Route
                    path="/early-warnings"
                    element={<EarlyWarningsPage />}
                />

                <Route
                    path="/ai-advisor"
                    element={<AIAdvisorPage />}
                />

            </Route>

            <Route
                path="/"
                element={<Navigate to="/dashboard" />}
            />

            <Route
                path="*"
                element={<Navigate to="/" />}
            />

        </Routes>
    );
}