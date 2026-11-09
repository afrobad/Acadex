import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
import app.models as m
from app.tracker import compute_student_detail, compute_warnings
from seed import seed_database
import datetime

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def setup_module_database():
    """Ensure database has pristine seeded state for SE 331 (total 105) and clean up after."""
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

# 1. Plan with total 105
def test_assessment_plan_total_105(faculty1_token):
    r = client.get("/api/courses/1/assessment-plan", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["course_id"] == 1
    assert data["total_max_marks"] == 105.0

    items_map = {item["category"].lower(): item["max_marks"] for item in data["items"]}
    expected_weights = {
        "quiz": 15.0,
        "assignment": 5.0,
        "midterm": 30.0,
        "final": 40.0,
        "presentation": 8.0,
        "attendance": 7.0,
    }
    assert items_map == expected_weights
    assert sum(expected_weights.values()) == 105.0

# 2. Pending final
def test_pending_final(faculty1_token):
    # In seeded SE 331, course is running and no final-term marks are created
    r = client.get("/api/courses/1/students/241-35-101/performance", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r.status_code == 200
    data = r.json()

    final_comp = data["components"]["final"]
    assert final_comp["status"] == "pending"
    assert final_comp["percentage"] is None
    assert final_comp["low"] is False
    assert final_comp["max_marks"] == 40.0
    assert final_comp["obtained_marks"] == 0.0

    # Final must not trigger any warning reason
    assert not any("final" in reason.lower() for reason in data["reasons"])

    # Final max (40.0) must be excluded from total_assessed_max: 105 - 40 = 65.0
    assert data["total_assessed_max"] == 65.0
    assert data["total_plan_max"] == 105.0
    expected_so_far = round(data["total_obtained"] / 65.0 * 100, 1)
    assert data["percentage_so_far"] == expected_so_far

# 3. Quiz scaling: two quizzes averaged then scaled to 15
def test_quiz_scaling():
    db = SessionLocal()
    try:
        # Create a dedicated student for deterministic math testing
        st = m.Student(student_code="TEST-QUIZ-SCALE", name="Quiz Scale Student")
        db.add(st)
        db.commit()
        db.refresh(st)

        # Enroll in course 1 (SE 331, quiz max marks = 15.0)
        db.add(m.Enrollment(student_id=st.id, course_id=1))

        # Two quizzes: Quiz 1: 8/10 (80%), Quiz 2: 9/10 (90%)
        # Average percentage: (80 + 90) / 2 = 85.0%
        # Scaled marks: 85% of 15.0 = 12.75
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=8.0, total=10.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 2", obtained=9.0, total=10.0))
        db.commit()

        detail = compute_student_detail(db, 1, st, attendance_threshold=60.0, marks_threshold=40.0)
        quiz_comp = detail["components"]["quiz"]

        assert quiz_comp["percentage"] == 85.0
        assert quiz_comp["max_marks"] == 15.0
        assert quiz_comp["obtained_marks"] == 12.75
        assert quiz_comp["status"] == "ok"
        assert quiz_comp["low"] is False

    finally:
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 4. Attendance scaling to 7
def test_attendance_scaling():
    db = SessionLocal()
    try:
        st = m.Student(student_code="TEST-ATT-SCALE", name="Attendance Scale Student")
        db.add(st)
        db.commit()
        db.refresh(st)

        db.add(m.Enrollment(student_id=st.id, course_id=1))

        # 17 present out of 20 days -> 17 / 20 = 85.0%
        # Scaled to attendance max 7.0: 85% of 7.0 = 5.95
        for d in range(20):
            present = 1 if d < 17 else 0
            db.add(m.Attendance(
                student_id=st.id,
                course_id=1,
                date=datetime.date(2026, 9, 1) + datetime.timedelta(days=d),
                present=present
            ))
        db.commit()

        detail = compute_student_detail(db, 1, st, attendance_threshold=60.0, marks_threshold=40.0)
        att_comp = detail["components"]["attendance"]

        assert att_comp["percentage"] == 85.0
        assert att_comp["max_marks"] == 7.0
        assert att_comp["obtained_marks"] == 5.95
        assert att_comp["status"] == "ok"
        assert att_comp["low"] is False

    finally:
        db.query(m.Attendance).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 5. Low presentation only -> Class performance below limit -> Warning (1 danger zone)
def test_low_presentation_only():
    db = SessionLocal()
    try:
        st = m.Student(student_code="TEST-LOW-PRES", name="Low Presentation Student")
        db.add(st)
        db.commit()
        db.refresh(st)

        db.add(m.Enrollment(student_id=st.id, course_id=1))

        # Good attendance (10/10 = 100% -> 7.0/7)
        for d in range(10):
            db.add(m.Attendance(student_id=st.id, course_id=1, date=datetime.date(2026, 9, 1) + datetime.timedelta(days=d), present=1))

        # Good quiz (10/10 = 100% -> 15.0/15)
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=10.0, total=10.0))
        # Good assignment (20/20 = 100% -> 5.0/5)
        db.add(m.Mark(student_id=st.id, course_id=1, category="assignment", assessment="Assignment", obtained=20.0, total=20.0))
        # Good midterm (45/50 = 90% -> 27.0/30)
        db.add(m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=45.0, total=50.0))
        # LOW presentation: 3/10 = 30.0% (scaled = 2.4/8)
        # Class performance sum: 7.0 + 5.0 + 2.4 = 14.4 / 20.0 (< 15.0 danger limit)
        db.add(m.Mark(student_id=st.id, course_id=1, category="presentation", assessment="Presentation", obtained=3.0, total=10.0))
        db.commit()

        detail = compute_student_detail(db, 1, st, attendance_threshold=60.0, marks_threshold=40.0)

        assert detail["components"]["presentation"]["status"] == "low"
        assert detail["components"]["presentation"]["obtained_marks"] == 2.4

        # Exactly 1 danger zone (class_perf), so this is WARNING, NOT critical!
        assert detail["level"] == "warning"
        assert detail["danger_zones"] == ["class_perf"]

        # Check readable danger zone reason
        assert any("Class performance" in r and "danger limit" in r for r in detail["reasons"])

    finally:
        db.query(m.Attendance).filter_by(student_id=st.id).delete()
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 6. Combined critical: 2 or more danger zones -> Critical
def test_combined_critical():
    db = SessionLocal()
    try:
        st = m.Student(student_code="TEST-COMBINED-CRIT", name="Critical Student")
        db.add(st)
        db.commit()
        db.refresh(st)

        db.add(m.Enrollment(student_id=st.id, course_id=1))

        # LOW attendance (4/10 = 40.0% -> 2.8/7)
        for d in range(10):
            db.add(m.Attendance(student_id=st.id, course_id=1, date=datetime.date(2026, 9, 1) + datetime.timedelta(days=d), present=1 if d < 4 else 0))

        # LOW presentation (3/10 = 30.0% -> 2.4/8)
        # Class performance: 2.8 + 2.4 = 5.2 / 20 (< 15.0 -> Zone 1 in danger)
        db.add(m.Mark(student_id=st.id, course_id=1, category="presentation", assessment="Presentation", obtained=3.0, total=10.0))

        # LOW midterm: 10/50 = 20% -> 6.0/30 (< 15.0 -> Zone 2 in danger)
        db.add(m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=10.0, total=50.0))
        db.commit()

        detail = compute_student_detail(db, 1, st, attendance_threshold=60.0, marks_threshold=40.0)

        # 2 danger zones (class_perf + midterm) -> CRITICAL level
        assert len(detail["danger_zones"]) >= 2
        assert detail["level"] == "critical"

        # Check readable reasons for danger zones
        assert any("Class performance" in r for r in detail["reasons"])
        assert any("Midterm" in r for r in detail["reasons"])

    finally:
        db.query(m.Attendance).filter_by(student_id=st.id).delete()
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 7. Student with no data
def test_student_with_no_data(faculty1_token):
    db = SessionLocal()
    try:
        st = m.Student(student_code="NO-DATA-001", name="No Data Student")
        db.add(st)
        db.commit()
        db.refresh(st)

        db.add(m.Enrollment(student_id=st.id, course_id=1))
        db.commit()

        # Test via python function
        detail = compute_student_detail(db, 1, st, attendance_threshold=60.0, marks_threshold=40.0)
        assert detail["level"] in ("safe", "ok")
        assert detail["danger_zones"] == []
        assert detail["total_obtained"] == 0.0
        assert detail["total_assessed_max"] == 0.0
        assert detail["total_plan_max"] == 105.0
        assert detail["percentage_so_far"] == 0.0
        assert detail["overall_score"] == 0.0
        assert detail["reasons"] == []
        assert detail["assessments"] == []

        for cat in ["attendance", "quiz", "assignment", "presentation", "midterm", "final"]:
            comp = detail["components"][cat]
            assert comp["status"] == "pending"
            assert comp["percentage"] is None
            assert comp["low"] is False
            assert comp["obtained_marks"] == 0.0

        # What-if calculation handles 0 data gracefully
        assert detail["what_if"]["target_percentage"] == 40.0
        assert detail["what_if"]["target_marks"] == 42.0
        assert detail["what_if"]["status"] == "Not reachable"

        # Also test via API endpoint
        r = client.get(f"/api/courses/1/students/{st.student_code}/performance", headers={"Authorization": f"Bearer {faculty1_token}"})
        assert r.status_code == 200
        api_data = r.json()
        assert api_data["level"] in ("safe", "ok")
        assert api_data["total_obtained"] == 0.0
        assert api_data["total_assessed_max"] == 0.0
        assert api_data["percentage_so_far"] == 0.0
        assert api_data["components"]["attendance"]["status"] == "pending"

    finally:
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 8. PUT assessment-plan validation: missing category returns 422
def test_put_assessment_plan_validation_missing_category(faculty1_token):
    # Only 5 categories, missing 'final'
    incomplete_plan = [
        {"category": "quiz", "max_marks": 15.0},
        {"category": "assignment", "max_marks": 5.0},
        {"category": "midterm", "max_marks": 30.0},
        {"category": "presentation", "max_marks": 8.0},
        {"category": "attendance", "max_marks": 7.0},
    ]
    r = client.put("/api/courses/1/assessment-plan", headers={"Authorization": f"Bearer {faculty1_token}"}, json=incomplete_plan)
    assert r.status_code == 422
    detail_str = str(r.json()["detail"]).lower()
    assert "missing" in detail_str
    assert "final" in detail_str

# 9. PUT assessment-plan validation: negative marks returns 422
def test_put_assessment_plan_validation_negative_marks(faculty1_token):
    negative_plan = [
        {"category": "quiz", "max_marks": -10.0},
        {"category": "assignment", "max_marks": 5.0},
        {"category": "midterm", "max_marks": 30.0},
        {"category": "final", "max_marks": 40.0},
        {"category": "presentation", "max_marks": 8.0},
        {"category": "attendance", "max_marks": 7.0},
    ]
    r = client.put("/api/courses/1/assessment-plan", headers={"Authorization": f"Bearer {faculty1_token}"}, json=negative_plan)
    assert r.status_code == 422
    detail_str = str(r.json()["detail"]).lower()
    assert "negative" in detail_str or "greater than or equal to 0" in detail_str

# 10. PUT assessment-plan validation: another faculty's course returns 404
def test_put_assessment_plan_validation_another_faculty_course_404(faculty1_token):
    # Course 2 is owned by Faculty 2 (sadia.faculty@diu.edu.bd)
    valid_plan = [
        {"category": "quiz", "max_marks": 20.0},
        {"category": "assignment", "max_marks": 10.0},
        {"category": "midterm", "max_marks": 25.0},
        {"category": "final", "max_marks": 35.0},
        {"category": "presentation", "max_marks": 5.0},
        {"category": "attendance", "max_marks": 5.0},
    ]
    r = client.put("/api/courses/2/assessment-plan", headers={"Authorization": f"Bearer {faculty1_token}"}, json=valid_plan)
    assert r.status_code == 404
    detail_str = str(r.json()["detail"]).lower()
    assert "course not found" in detail_str

# 11. Demo faculty owns three courses with distinct summary counts
def test_demo_faculty_three_courses_with_distinct_summaries(faculty1_token, faculty2_token):
    # Demo faculty sees exactly three courses
    r1 = client.get("/api/courses", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r1.status_code == 200
    courses = r1.json()
    assert len(courses) == 3
    code_map = {c["code"]: c["id"] for c in courses}
    assert set(code_map.keys()) == {"SE 331", "SE 311", "CSE 221"}

    # Check each course assessment plan has total 105
    for code, cid in code_map.items():
        r_plan = client.get(f"/api/courses/{cid}/assessment-plan", headers={"Authorization": f"Bearer {faculty1_token}"})
        assert r_plan.status_code == 200
        assert r_plan.json()["total_max_marks"] == 105.0

    # Check each course shows different summary counts
    summaries = {}
    for code, cid in code_map.items():
        r_warn = client.get(f"/api/courses/{cid}/performance-warnings", headers={"Authorization": f"Bearer {faculty1_token}"})
        assert r_warn.status_code == 200
        summ = r_warn.json()["summary"]
        summaries[code] = (summ["critical"], summ["warning"], summ["ok"], summ["total"])

    # All three summaries must be distinct
    unique_summaries = set(summaries.values())
    assert len(unique_summaries) == 3, f"Expected 3 distinct summaries, got: {summaries}"

    # Isolation: Faculty 2 still sees only SE 412
    r2 = client.get("/api/courses", headers={"Authorization": f"Bearer {faculty2_token}"})
    assert r2.status_code == 200
    f2_courses = r2.json()
    assert len(f2_courses) == 1
    assert f2_courses[0]["code"] == "SE 412"
