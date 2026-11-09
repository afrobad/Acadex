import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
import app.models as m
from app.tracker import compute_student_detail
from seed import seed_database
import datetime

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def setup_module_database():
    seed_database(verbose=False)
    yield
    seed_database(verbose=False)

@pytest.fixture(scope="module")
def faculty1_token():
    r = client.post("/api/auth/login", json={"email": "faculty@diu.edu.bd", "password": "Password123"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]

@pytest.fixture(scope="module")
def faculty2_token():
    r = client.post("/api/auth/login", json={"email": "sadia.faculty@diu.edu.bd", "password": "Password123"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]

# 1. Grid loading endpoint & RBAC
def test_get_marks_grid_success(faculty1_token):
    # Course 1 is owned by faculty1
    r = client.get("/api/courses/1/marks/grid", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["course_id"] == 1
    assert data["course_code"] == "SE 331"
    assert len(data["columns"]) == 7

    col_keys = [c["key"] for c in data["columns"]]
    assert col_keys == ["quiz_1", "quiz_2", "assignment", "presentation", "midterm", "attendance", "final"]

    # Verify column max marks scaled from plan
    col_map = {c["key"]: c for c in data["columns"]}
    assert col_map["quiz_1"]["max_marks"] == 15.0
    assert col_map["quiz_2"]["max_marks"] == 15.0
    assert col_map["assignment"]["max_marks"] == 5.0
    assert col_map["presentation"]["max_marks"] == 8.0
    assert col_map["midterm"]["max_marks"] == 30.0
    assert col_map["attendance"]["max_marks"] == 7.0
    assert col_map["final"]["disabled"] is True
    assert col_map["final"]["pending"] is True

    # Check students list
    assert len(data["students"]) == 12
    first_st = data["students"][0]
    assert "student_code" in first_st
    assert "name" in first_st
    assert "marks" in first_st
    assert "Quiz 1" in first_st["marks"]
    assert "Assignment" in first_st["marks"]

def test_get_marks_grid_rbac_isolation(faculty2_token):
    # Course 1 is owned by faculty1; faculty2 must get 404
    r = client.get("/api/courses/1/marks/grid", headers={"Authorization": f"Bearer {faculty2_token}"})
    assert r.status_code == 404

def test_get_marks_grid_unauthorized():
    r = client.get("/api/courses/1/marks/grid")
    assert r.status_code == 401

# 2. Bulk marks save & upsert (no duplicate rows)
def test_bulk_marks_save_and_upsert(faculty1_token):
    db = SessionLocal()
    st = db.query(m.Student).filter_by(student_code="241-35-101").first()
    assert st is not None

    # Count marks before save
    count_before = db.query(m.Mark).filter_by(student_id=st.id, course_id=1).count()
    db.close()

    payload = [
        {
            "student_code": "241-35-101",
            "category": "quiz",
            "assessment": "Quiz 1",
            "obtained": 14.5,
            "total": 15.0
        },
        {
            "student_code": "241-35-101",
            "category": "assignment",
            "assessment": "Assignment",
            "obtained": 4.8,
            "total": 5.0
        }
    ]

    r = client.post("/api/courses/1/marks/bulk", json=payload, headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r.status_code == 200
    res = r.json()
    assert res["saved_count"] == 2

    # Verify database state: existing mark was updated, count of marks for student must not have increased
    db = SessionLocal()
    count_after = db.query(m.Mark).filter_by(student_id=st.id, course_id=1).count()
    assert count_after == count_before  # No duplicates

    q1 = db.query(m.Mark).filter_by(student_id=st.id, course_id=1, assessment="Quiz 1").first()
    assert q1 is not None
    assert q1.obtained == 14.5
    assert q1.total == 15.0

    assign = db.query(m.Mark).filter_by(student_id=st.id, course_id=1, assessment="Assignment").first()
    assert assign is not None
    assert assign.obtained == 4.8
    assert assign.total == 5.0
    db.close()

# 3. Validation and single transaction rollback (all-or-nothing)
def test_bulk_marks_validation_exceeds_total_rollback(faculty1_token):
    db = SessionLocal()
    st = db.query(m.Student).filter_by(student_code="241-35-102").first()
    original_quiz = db.query(m.Mark).filter_by(student_id=st.id, course_id=1, assessment="Quiz 1").first()
    original_obtained = original_quiz.obtained
    db.close()

    # Payload with 1 valid row and 1 invalid row (obtained > total)
    payload = [
        {
            "student_code": "241-35-102",
            "category": "quiz",
            "assessment": "Quiz 1",
            "obtained": 12.0,
            "total": 15.0
        },
        {
            "student_code": "241-35-102",
            "category": "midterm",
            "assessment": "Midterm",
            "obtained": 35.0,  # Invalid: 35 > 30
            "total": 30.0
        }
    ]

    r = client.post("/api/courses/1/marks/bulk", json=payload, headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r.status_code in (400, 422)

    # Check rollback: Quiz 1 must NOT have changed to 12.0
    db = SessionLocal()
    q_after = db.query(m.Mark).filter_by(student_id=st.id, course_id=1, assessment="Quiz 1").first()
    assert q_after.obtained == original_obtained
    db.close()

def test_bulk_marks_validation_unenrolled_student_rollback(faculty1_token):
    # Student not enrolled in course 1
    payload = [
        {
            "student_code": "999-99-999",
            "category": "quiz",
            "assessment": "Quiz 1",
            "obtained": 10.0,
            "total": 15.0
        }
    ]
    r = client.post("/api/courses/1/marks/bulk", json=payload, headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r.status_code == 400
    assert "not enrolled" in r.text

def test_bulk_marks_validation_foreign_course_404(faculty2_token):
    # Faculty 2 trying to update Course 1 (owned by Faculty 1)
    payload = [
        {
            "student_code": "241-35-101",
            "category": "quiz",
            "assessment": "Quiz 1",
            "obtained": 10.0,
            "total": 15.0
        }
    ]
    r = client.post("/api/courses/1/marks/bulk", json=payload, headers={"Authorization": f"Bearer {faculty2_token}"})
    assert r.status_code == 404

# 4. Attendance Marks Precedence (Direct mark wins over per-day attendance)
def test_direct_attendance_mark_precedence(faculty1_token):
    db = SessionLocal()
    try:
        # Create a test student
        st = m.Student(student_code="TEST-ATT-PRECEDENCE", name="Precedence Student", email="prec@diu.edu.bd")
        db.add(st)
        db.commit()
        db.refresh(st)

        db.add(m.Enrollment(student_id=st.id, course_id=1))

        # Add 20 days of daily attendance where student is present only 4 days (4/20 = 20% -> low / critical)
        for d in range(20):
            db.add(m.Attendance(
                student_id=st.id,
                course_id=1,
                date=datetime.date(2026, 9, 1) + datetime.timedelta(days=d),
                present=1 if d < 4 else 0
            ))
        db.commit()

        # Step 4a: Without direct attendance mark, compute_student_detail uses daily attendance
        detail1 = compute_student_detail(db, 1, st)
        assert detail1["components"]["attendance"]["percentage"] == 20.0
        assert detail1["components"]["attendance"]["obtained_marks"] == 1.4  # 20% of 7 = 1.4
        assert detail1["components"]["attendance"]["status"] == "low"

        # Step 4b: Faculty enters direct attendance mark via bulk marks endpoint: 6.5 out of 7.0
        payload = [
            {
                "student_code": st.student_code,
                "category": "attendance",
                "assessment": "Attendance",
                "obtained": 6.5,
                "total": 7.0
            }
        ]
        r = client.post("/api/courses/1/marks/bulk", json=payload, headers={"Authorization": f"Bearer {faculty1_token}"})
        assert r.status_code == 200

        # Step 4c: Check that compute_student_detail uses direct attendance mark (6.5 / 7.0 = 92.9% -> ok)
        # Even though the 20 daily attendance records still exist!
        detail2 = compute_student_detail(db, 1, st)
        assert detail2["components"]["attendance"]["percentage"] == 92.9
        assert detail2["components"]["attendance"]["obtained_marks"] == 6.5
        assert detail2["components"]["attendance"]["status"] == "ok"

    finally:
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Attendance).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()
