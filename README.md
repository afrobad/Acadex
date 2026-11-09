# Acadex FR-04 — Centralized Assessment & Marks Management

Standalone, integration-ready prototype based on `Acadex_SRS_With_4_Diagrams.docx`.

## SRS scope implemented
- Faculty entry of theory/lab assessment marks
- CSV/XLSX import with student/section and score-range validation
- Deterministic totals (sum of assessment components; no AI grading)
- Student-wise marking sheet and CSV/XLSX export
- Synthetic demo dataset; no connection to DIU systems
- Audit events for mark creation/update/import/export actions

## Technology
- Frontend: Next.js, React, TypeScript
- Backend: Python, FastAPI, SQLAlchemy
- Database: PostgreSQL

## Quick start (Docker recommended)
1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Run: `docker compose up --build`
4. Frontend: http://localhost:3000
5. API docs: http://localhost:8000/docs

The backend creates its tables and seeds synthetic demo courses, students, and assessments on first start.

## Local development without Docker
Backend (Python 3.11+):
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Set DATABASE_URL to a running PostgreSQL database
uvicorn app.main:app --reload
```
Frontend (Node.js 20+):
```bash
cd frontend
npm install
npm run dev
```
Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` if needed.

## Demo data
- Demo course: SWE-331 — Software Requirements Engineering
- Demo section: 61_A
- Demo faculty: demo.faculty@acadex.local
- Students are synthetic. Do not use real student information.

## Import format
CSV/XLSX columns (header names are case-insensitive): `student_id`, `section`, `assessment_code`, `obtained_marks`.
Each assessment code must already exist for the selected course. Scores must satisfy `0 <= obtained_marks <= max_marks`.

## Important limitations
This is a runnable academic prototype, not a production university system. Authentication is represented by a demo faculty context; production OAuth/SSO, full RBAC, encryption/key management, institutional integration, formal privacy review and deployment hardening remain required. Imported rows are validated before they are saved. Official transcript/final-grade changes are not supported.

## Tests
```bash
cd backend
pytest
```
