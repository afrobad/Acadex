# Acadex - Performance Tracker (FR-03)
Marks + attendance theke at-risk warning (explainable, rule-based) with JWT authentication and RBAC.

## Setup & Running

```bash
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

## Demo Credentials (from `seed.py`)
- **Faculty 1**: `faculty@diu.edu.bd` / `Password123` (Owner of `SE 331`)
- **Faculty 2**: `sadia.faculty@diu.edu.bd` / `Password123` (Owner of `SE 412`)

## Pages
- `/` - Main Performance Tracker dashboard (requires login)
- `/login` - Faculty login page
- `/register` - Faculty registration page

## API Endpoints
- `POST /api/auth/register` - Register a new faculty account
- `POST /api/auth/login` - Authenticate and get JWT Bearer token
- `GET /api/auth/me` - Get profile of the authenticated user
- `GET /api/courses` - List courses owned by the authenticated faculty member
- `GET /api/courses/{id}/performance-warnings?attendance_threshold=60&marks_threshold=40&only_flagged=false` - Compute explainable performance warnings and overall scores for students in the faculty's course
- `GET /api/courses/{id}/students/{code}/performance` - Retrieve in-depth student performance breakdown, per-category components, overall score, and itemized assessment marks
- `POST /api/courses/{id}/attendance` - Record a student attendance entry (student_code, date, present)
- `POST /api/courses/{id}/marks` - Record an assessment mark (student_code, category, assessment, obtained, total)
- `GET /api/courses/{id}/assessment-plan` - Retrieve course assessment weightings and total plan marks
- `PUT /api/courses/{id}/assessment-plan` - Configure and update all 6 category weights (quiz, assignment, midterm, final, presentation, attendance)

## Environment Variables (`.env`)
- `SECRET_KEY` - Cryptographic secret key used to sign JWT access tokens
- `ALGORITHM` - Token signing algorithm (default `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time in minutes (default `1440`)
