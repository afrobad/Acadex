# Acadex Frontend

React + Vite faculty portal starter.

## Run
1. Install Node.js 18+ (Node 20 LTS recommended).
2. Run `npm install`.
3. Start Spring Boot at `http://localhost:8080`.
4. Run `npm run dev` and open `http://localhost:5173`.

Vite proxies `/api` to Spring Boot. Login calls `POST /api/auth/login` and sends `email`, `employeeId`, and `password`. Expected response fields: `accessToken`, `facultyId`, `employeeId`, `fullName`, `email`, `role`.

## Important API mappings to verify
- Login: `POST /api/auth/login` (existing backend endpoint)
- Registration page: `GET /api/faculty/course-registration/students/{studentId}` (example route; change in `src/pages/RegistrationPage.jsx` to match your controller)
- Performance: `GET /api/faculty/performance/{studentId}` (future/example route)
- Early warnings: `GET /api/faculty/performance/early-warnings` (future/example route)

Dashboard counters are placeholders. AI Advisor is a UI preview and does not call an LLM. Academic calculations and faculty/student authorization must be enforced by Spring Boot. The token is stored in `sessionStorage` for this local MVP; production should consider HttpOnly Secure SameSite cookies and strong XSS/CSRF protections. Do not deploy demo credentials.
