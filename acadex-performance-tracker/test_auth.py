import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
import app.models as m
from app.auth import get_current_user, create_access_token
from seed import seed_database
import datetime

client = TestClient(app)

def test_full_auth_flow():
    seed_database(verbose=False)
    print("--- 1. Testing Registration Validation ---")

    # 1a. Password too short (<8)
    r = client.post("/api/auth/register", json={
        "name": "Test Faculty",
        "email": "test@diu.edu.bd",
        "password": "Pass1",
        "role": "faculty"
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
    print("[OK] Rejected short password")

    # 1b. Password missing digit
    r = client.post("/api/auth/register", json={
        "name": "Test Faculty",
        "email": "test@diu.edu.bd",
        "password": "PasswordOnly",
        "role": "faculty"
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
    print("[OK] Rejected password without digits")

    # 1c. Invalid email
    r = client.post("/api/auth/register", json={
        "name": "Test Faculty",
        "email": "not-an-email",
        "password": "Password123",
        "role": "faculty"
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
    print("[OK] Rejected invalid email")

    # 1d. Duplicate email (already seeded faculty@diu.edu.bd)
    r = client.post("/api/auth/register", json={
        "name": "Dr. Duplicate",
        "email": "faculty@diu.edu.bd",
        "password": "Password123",
        "role": "faculty"
    })
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "already registered" in r.json()["detail"].lower()
    print("[OK] Rejected duplicate email with clear message")

    # 1e. Successful registration
    r = client.post("/api/auth/register", json={
        "name": "Dr. New User",
        "email": "new.user@diu.edu.bd",
        "password": "SecurePassword1",
        "role": "faculty"
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == "new.user@diu.edu.bd"
    print("[OK] Registered new user with JWT token")

    print("\n--- 2. Testing Login ---")
    # 2a. Wrong password
    r = client.post("/api/auth/login", json={
        "email": "faculty@diu.edu.bd",
        "password": "WrongPassword1"
    })
    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"
    print("[OK] Rejected invalid password")

    # 2b. Unknown email
    r = client.post("/api/auth/login", json={
        "email": "unknown@diu.edu.bd",
        "password": "Password123"
    })
    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"
    print("[OK] Rejected unknown email")

    # 2c. Successful login for Faculty 1
    r = client.post("/api/auth/login", json={
        "email": "faculty@diu.edu.bd",
        "password": "Password123"
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    faculty1_token = r.json()["access_token"]
    assert faculty1_token is not None
    print("[OK] Faculty 1 logged in successfully")

    # 2d. Successful login for Faculty 2
    r2 = client.post("/api/auth/login", json={
        "email": "sadia.faculty@diu.edu.bd",
        "password": "Password123"
    })
    assert r2.status_code == 200, f"Expected 200, got {r2.status_code}: {r2.text}"
    faculty2_token = r2.json()["access_token"]
    assert faculty2_token is not None
    print("[OK] Faculty 2 logged in successfully")

    print("\n--- 3. Testing Protected Endpoints without Token ---")
    # 3a. /api/auth/me without token -> 401
    r_unauth = client.get("/api/auth/me")
    assert r_unauth.status_code == 401
    print("[OK] /api/auth/me rejects unauthenticated requests")

    # 3b. /api/courses without token -> 401
    r_unauth_courses = client.get("/api/courses")
    assert r_unauth_courses.status_code == 401
    print("[OK] /api/courses rejects unauthenticated requests")

    # 3c. /api/courses/1/performance-warnings without token -> 401
    r_unauth_warn = client.get("/api/courses/1/performance-warnings")
    assert r_unauth_warn.status_code == 401
    print("[OK] /api/courses/1/performance-warnings rejects unauthenticated requests")

    print("\n--- 4. Testing Identity & RBAC Course Isolation ---")
    # 4a. /api/auth/me returns current user profile
    r_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r_me.status_code == 200
    me_data = r_me.json()
    assert me_data["email"] == "faculty@diu.edu.bd"
    assert me_data["name"] == "Dr. Kamrul Hasan"
    assert me_data["role"] == "faculty"
    print("[OK] /api/auth/me verified Faculty 1 profile")

    # 4b. Faculty 1 gets own courses (owns SE 331, SE 311, CSE 221)
    r_courses1 = client.get("/api/courses", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r_courses1.status_code == 200
    c1_list = r_courses1.json()
    c1_codes = [c["code"] for c in c1_list]
    assert "SE 331" in c1_codes
    assert "SE 412" not in c1_codes, "Faculty 1 must NOT see Faculty 2's course SE 412"
    print("[OK] Faculty 1 only sees their own courses")

    # 4c. Faculty 2 gets own courses (owns SE 412)
    r_courses2 = client.get("/api/courses", headers={"Authorization": f"Bearer {faculty2_token}"})
    assert r_courses2.status_code == 200
    c2_list = r_courses2.json()
    c2_codes = [c["code"] for c in c2_list]
    assert "SE 412" in c2_codes
    assert "SE 331" not in c2_codes, "Faculty 2 must NOT see Faculty 1's course SE 331"
    print("[OK] Faculty 2 only sees their own courses")

    # 4d. Faculty 1 accesses own course warnings (id=1, SE 331)
    r_warn = client.get("/api/courses/1/performance-warnings", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r_warn.status_code == 200
    warn_data = r_warn.json()
    assert warn_data["course"] == "SE 331"
    assert len(warn_data["students"]) == 12
    assert "summary" in warn_data, "summary missing from response"
    summary = warn_data["summary"]
    assert summary["total"] == 12
    safe_ok_count = summary.get("safe", summary.get("ok"))
    assert safe_ok_count > 0
    assert summary["critical"] + summary["warning"] + safe_ok_count == summary["total"]
    print("[OK] Faculty 1 can access own course performance warnings with summary")

    # Test only_flagged=true bugfix: summary must keep all counts, table only flagged
    r_flagged = client.get("/api/courses/1/performance-warnings?only_flagged=true", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r_flagged.status_code == 200
    flagged_data = r_flagged.json()
    assert flagged_data["summary"]["ok"] == summary["ok"], "Summary OK count changed under only_flagged filter"
    assert flagged_data["summary"]["total"] == summary["total"]
    assert all(s["level"] not in ("safe", "ok") for s in flagged_data["students"]), "Filtered rows should not include safe/ok students"
    print("[OK] Summary preserves full cohort counts even when only_flagged=true")

    # Test components object and level calculation
    for s in warn_data["students"]:
        assert "components" in s, "components object missing"
        comp = s["components"]
        for key in ["attendance", "quiz", "assignment", "presentation", "midterm", "final"]:
            assert key in comp, f"component {key} missing"
            assert "obtained_marks" in comp[key]
            assert "max_marks" in comp[key]
            assert "status" in comp[key]
            assert comp[key]["status"] in ("ok", "low", "pending")

        assert comp["final"]["status"] == "pending"
        assert s["total_assessed_max"] == 65.0
        assert s["total_plan_max"] == 105.0
        assert s["overall_score"] == s["percentage_so_far"]

        danger_count = len(s.get("danger_zones", []))
        if s["level"] == "critical":
            assert danger_count >= 2, "Critical student must have 2 or more danger zones"
        elif s["level"] == "warning":
            assert danger_count == 1, "Warning student must have exactly 1 danger zone"
        elif s["level"] in ("safe", "ok"):
            assert danger_count == 0, "Safe student must have 0 danger zones"
            assert len(s["reasons"]) == 0
    print("[OK] Verified components object, pending status, plan weighting & level rules across all students")

    # Faculty 1 attempts to access Faculty 2's course warnings (id=2)
    r_forbidden = client.get("/api/courses/2/performance-warnings", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r_forbidden.status_code == 404, f"Expected 404, got {r_forbidden.status_code}"
    print("[OK] Faculty 1 is forbidden from accessing Faculty 2's course")

    # Faculty 2 attempts to access Faculty 1's course warnings (id=1)
    r_forbidden2 = client.get("/api/courses/1/performance-warnings", headers={"Authorization": f"Bearer {faculty2_token}"})
    assert r_forbidden2.status_code == 404, f"Expected 404, got {r_forbidden2.status_code}"
    print("[OK] Faculty 2 is forbidden from accessing Faculty 1's course")

    # Student detail endpoint RBAC
    r_st = client.get("/api/courses/1/students/241-35-101/performance", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r_st.status_code == 200
    st_data = r_st.json()
    assert st_data["code"] == "241-35-101"
    print("[OK] Faculty 1 can access enrolled student detail")

    r_st_forbidden = client.get("/api/courses/1/students/241-35-101/performance", headers={"Authorization": f"Bearer {faculty2_token}"})
    assert r_st_forbidden.status_code == 404
    print("[OK] Faculty 2 cannot access student detail in Faculty 1's course")

    # Attendance creation RBAC
    r_att_forbidden = client.post("/api/courses/1/attendance", headers={"Authorization": f"Bearer {faculty2_token}"}, json={
        "student_code": "241-35-101",
        "date": "2026-10-15",
        "present": 1
    })
    assert r_att_forbidden.status_code == 404
    print("[OK] Faculty 2 cannot log attendance for Faculty 1's course")

    # Mark creation RBAC
    r_mk_forbidden = client.post("/api/courses/1/marks", headers={"Authorization": f"Bearer {faculty2_token}"}, json={
        "student_code": "241-35-101",
        "category": "quiz",
        "assessment": "Quiz 3",
        "obtained": 8.0,
        "total": 10.0
    })
    assert r_mk_forbidden.status_code == 404
    print("[OK] Faculty 2 cannot record marks for Faculty 1's course")

    print("\n--- 5. Testing Attendance & Mark Input Validation ---")
    # Attendance: empty student code -> 422
    r = client.post("/api/courses/1/attendance", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "",
        "date": "2026-10-15",
        "present": 1
    })
    assert r.status_code == 422

    # Attendance: future date -> 422
    future_date = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    r = client.post("/api/courses/1/attendance", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "241-35-101",
        "date": future_date,
        "present": 1
    })
    assert r.status_code == 422
    assert "future" in r.text.lower()
    print("[OK] Attendance rejects future dates")

    # Attendance: invalid student code (not enrolled in course 1) -> 404
    r = client.post("/api/courses/1/attendance", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "UNKNOWN-999",
        "date": "2026-10-15",
        "present": 1
    })
    assert r.status_code == 404
    print("[OK] Attendance rejects unknown student code")

    # Mark: invalid category -> 422
    r = client.post("/api/courses/1/marks", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "241-35-101",
        "category": "bonus",
        "assessment": "Bonus Task",
        "obtained": 5.0,
        "total": 10.0
    })
    assert r.status_code == 422
    assert "category" in r.text.lower()
    print("[OK] Mark rejects unallowed category")

    # Mark: total <= 0 -> 422
    r = client.post("/api/courses/1/marks", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "241-35-101",
        "category": "quiz",
        "assessment": "Zero Total Quiz",
        "obtained": 0.0,
        "total": 0.0
    })
    assert r.status_code == 422
    assert "greater than 0" in r.text.lower()
    print("[OK] Mark rejects total <= 0")

    # Mark: negative obtained -> 422
    r = client.post("/api/courses/1/marks", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "241-35-101",
        "category": "quiz",
        "assessment": "Negative Quiz",
        "obtained": -2.0,
        "total": 10.0
    })
    assert r.status_code == 422
    print("[OK] Mark rejects negative obtained")

    # Mark: obtained > total -> 422
    r = client.post("/api/courses/1/marks", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "241-35-101",
        "category": "quiz",
        "assessment": "Over Quiz",
        "obtained": 15.0,
        "total": 10.0
    })
    assert r.status_code == 422
    assert "cannot exceed total" in r.text.lower()
    print("[OK] Mark rejects obtained > total")

    # Valid mark recording
    r = client.post("/api/courses/1/marks", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "241-35-101",
        "category": "quiz",
        "assessment": "Quiz 3",
        "obtained": 8.5,
        "total": 10.0
    })
    assert r.status_code == 201
    assert r.json()["obtained"] == 8.5
    print("[OK] Valid mark recorded successfully")

    # Valid attendance recording
    r = client.post("/api/courses/1/attendance", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "student_code": "241-35-101",
        "date": "2026-10-15",
        "present": 1
    })
    assert r.status_code == 201
    print("[OK] Valid attendance recorded successfully")
    print("\nALL AUTH & RBAC TESTS PASSED!")
