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
    assert r.status_code == 200
    return r.json()["access_token"]

@pytest.fixture(scope="module")
def faculty2_token():
    r = client.post("/api/auth/login", json={"email": "sadia.faculty@diu.edu.bd", "password": "Password123"})
    assert r.status_code == 200
    return r.json()["access_token"]

# 1. API CRUD & Validation
def test_danger_zone_rules_api_crud_and_validation(faculty1_token, faculty2_token):
    # 1a. Unauthorized access -> 401
    r_unauth = client.get("/api/courses/1/danger-zone-rules")
    assert r_unauth.status_code == 401

    # 1b. Forbidden course (Faculty 2 tries to access Course 1) -> 404
    r_forbid = client.get("/api/courses/1/danger-zone-rules", headers={"Authorization": f"Bearer {faculty2_token}"})
    assert r_forbid.status_code == 404

    # 1c. Get default danger zone rules for Course 1 (SE 331)
    r_get = client.get("/api/courses/1/danger-zone-rules", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r_get.status_code == 200
    data = r_get.json()
    assert data["course_id"] == 1
    assert data["quiz_limit"] == 10.0
    assert data["midterm_limit"] == 15.0
    assert data["class_limit"] == 15.0
    assert data["max_possible"]["quiz"] == 15.0
    assert data["max_possible"]["midterm"] == 30.0
    assert data["max_possible"]["class"] == 20.0  # 7 att + 5 asgn + 8 pres = 20

    # 1d. Validation: Quiz limit exceeds plan max (16 > 15) -> 422
    r_val1 = client.put("/api/courses/1/danger-zone-rules", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "quiz_limit": 16.0, "midterm_limit": 15.0, "class_limit": 15.0
    })
    assert r_val1.status_code == 422
    assert "quiz limit" in r_val1.text.lower()

    # 1e. Validation: Midterm limit exceeds plan max (35 > 30) -> 422
    r_val2 = client.put("/api/courses/1/danger-zone-rules", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "quiz_limit": 10.0, "midterm_limit": 35.0, "class_limit": 15.0
    })
    assert r_val2.status_code == 422
    assert "midterm limit" in r_val2.text.lower()

    # 1f. Validation: Class limit exceeds combined max (25 > 20) -> 422
    r_val3 = client.put("/api/courses/1/danger-zone-rules", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "quiz_limit": 10.0, "midterm_limit": 15.0, "class_limit": 25.0
    })
    assert r_val3.status_code == 422
    assert "class performance limit" in r_val3.text.lower()

    # 1g. Validation: Negative limits -> 422
    r_neg = client.put("/api/courses/1/danger-zone-rules", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "quiz_limit": -1.0, "midterm_limit": 15.0, "class_limit": 15.0
    })
    assert r_neg.status_code == 422

    # 1h. Valid update
    r_put = client.put("/api/courses/1/danger-zone-rules", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "quiz_limit": 9.5, "midterm_limit": 16.0, "class_limit": 14.5
    })
    assert r_put.status_code == 200
    res_data = r_put.json()
    assert res_data["quiz_limit"] == 9.5
    assert res_data["midterm_limit"] == 16.0
    assert res_data["class_limit"] == 14.5

    # Reset back to standard defaults for subsequent tests
    client.put("/api/courses/1/danger-zone-rules", headers={"Authorization": f"Bearer {faculty1_token}"}, json={
        "quiz_limit": 10.0, "midterm_limit": 15.0, "class_limit": 15.0
    })

# 2. Each zone alone -> 1 zone -> Warning
def test_danger_zone_each_alone_is_warning():
    db = SessionLocal()
    st = m.Student(student_code="TEST-DZ-ALONE", name="Single Danger Zone Student")
    db.add(st)
    db.commit()
    db.refresh(st)
    db.add(m.Enrollment(student_id=st.id, course_id=1))
    db.commit()

    try:
        # Case 2a: Only Quiz in danger (8/15 < 10.0), Midterm safe (20/30 >= 15.0), Class safe (18/20 >= 15.0)
        # Attendance 7/7, Assignment 5/5, Presentation 6/8 = 18.0 / 20.0
        db.add(m.Mark(student_id=st.id, course_id=1, category="attendance", assessment="Attendance", obtained=7.0, total=7.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="assignment", assessment="Assignment", obtained=5.0, total=5.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="presentation", assessment="Presentation", obtained=6.0, total=8.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=20.0, total=30.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=8.0, total=15.0))
        db.commit()

        d_quiz = compute_student_detail(db, 1, st)
        assert d_quiz["danger_zones"] == ["quiz"]
        assert d_quiz["level"] == "warning"
        assert len(d_quiz["reasons"]) == 1
        assert "Quiz 8.0/15 is below the danger limit 10" in d_quiz["reasons"][0]

        # Case 2b: Only Midterm in danger (12/30 < 15.0), Quiz safe (12/15 >= 10.0), Class safe (18/20 >= 15.0)
        db.query(m.Mark).filter_by(student_id=st.id, category="quiz").delete()
        db.query(m.Mark).filter_by(student_id=st.id, category="midterm").delete()
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=12.0, total=15.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=12.0, total=30.0))
        db.commit()

        d_mid = compute_student_detail(db, 1, st)
        assert d_mid["danger_zones"] == ["midterm"]
        assert d_mid["level"] == "warning"
        assert len(d_mid["reasons"]) == 1
        assert "Midterm 12.0/30 is below the danger limit 15" in d_mid["reasons"][0]

        # Case 2c: Only Class in danger (13/20 < 15.0), Quiz safe (12/15 >= 10.0), Midterm safe (20/30 >= 15.0)
        # Lower class marks: Attendance 5/7, Assignment 3/5, Presentation 5/8 = 13.0 / 20.0 (< 15.0)
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.add(m.Mark(student_id=st.id, course_id=1, category="attendance", assessment="Attendance", obtained=5.0, total=7.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="assignment", assessment="Assignment", obtained=3.0, total=5.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="presentation", assessment="Presentation", obtained=5.0, total=8.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=12.0, total=15.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=20.0, total=30.0))
        db.commit()

        d_cls = compute_student_detail(db, 1, st)
        assert d_cls["danger_zones"] == ["class_perf"]
        assert d_cls["level"] == "warning"
        assert len(d_cls["reasons"]) == 1
        assert "Class performance 13.0/20" in d_cls["reasons"][0]

    finally:
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 3. Two zones in danger -> Critical
def test_danger_zone_two_zones_is_critical():
    db = SessionLocal()
    st = m.Student(student_code="TEST-DZ-TWO", name="Two Danger Zones Student")
    db.add(st)
    db.commit()
    db.refresh(st)
    db.add(m.Enrollment(student_id=st.id, course_id=1))
    db.commit()

    try:
        # Quiz in danger (8/15 < 10) AND Midterm in danger (12/30 < 15), Class safe (18/20 >= 15)
        db.add(m.Mark(student_id=st.id, course_id=1, category="attendance", assessment="Attendance", obtained=7.0, total=7.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="assignment", assessment="Assignment", obtained=5.0, total=5.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="presentation", assessment="Presentation", obtained=6.0, total=8.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=8.0, total=15.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=12.0, total=30.0))
        db.commit()

        detail = compute_student_detail(db, 1, st)
        assert set(detail["danger_zones"]) == {"quiz", "midterm"}
        assert detail["level"] == "critical"
        assert len(detail["reasons"]) == 2

    finally:
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 4. Three zones in danger -> Critical
def test_danger_zone_three_zones_is_critical():
    db = SessionLocal()
    st = m.Student(student_code="TEST-DZ-THREE", name="Three Danger Zones Student")
    db.add(st)
    db.commit()
    db.refresh(st)
    db.add(m.Enrollment(student_id=st.id, course_id=1))
    db.commit()

    try:
        # Quiz in danger (7/15), Midterm in danger (10/30), Class in danger (5/20)
        db.add(m.Mark(student_id=st.id, course_id=1, category="attendance", assessment="Attendance", obtained=2.0, total=7.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="assignment", assessment="Assignment", obtained=1.0, total=5.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="presentation", assessment="Presentation", obtained=2.0, total=8.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=7.0, total=15.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=10.0, total=30.0))
        db.commit()

        detail = compute_student_detail(db, 1, st)
        assert set(detail["danger_zones"]) == {"quiz", "midterm", "class_perf"}
        assert detail["level"] == "critical"
        assert len(detail["reasons"]) == 3

    finally:
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 5. None in danger -> Safe
def test_danger_zone_none_is_safe():
    db = SessionLocal()
    st = m.Student(student_code="TEST-DZ-SAFE", name="All Safe Student")
    db.add(st)
    db.commit()
    db.refresh(st)
    db.add(m.Enrollment(student_id=st.id, course_id=1))
    db.commit()

    try:
        # All above limits: Quiz 12 >= 10, Midterm 22 >= 15, Class 18 >= 15
        db.add(m.Mark(student_id=st.id, course_id=1, category="attendance", assessment="Attendance", obtained=6.5, total=7.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="assignment", assessment="Assignment", obtained=4.5, total=5.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="presentation", assessment="Presentation", obtained=7.0, total=8.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=12.0, total=15.0))
        db.add(m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=22.0, total=30.0))
        db.commit()

        detail = compute_student_detail(db, 1, st)
        assert detail["danger_zones"] == []
        assert detail["level"] == "safe"
        assert len(detail["reasons"]) == 0

    finally:
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 6. Boundary values exactly at the limit
def test_danger_zone_exact_boundary():
    db = SessionLocal()
    st = m.Student(student_code="TEST-DZ-BOUNDARY", name="Boundary Student")
    db.add(st)
    db.commit()
    db.refresh(st)
    db.add(m.Enrollment(student_id=st.id, course_id=1))
    db.commit()

    try:
        # Exactly at limit: Quiz = 10.0, Midterm = 15.0, Class = 15.0 (5.0 + 4.0 + 6.0)
        q_mark = m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=10.0, total=15.0)
        m_mark = m.Mark(student_id=st.id, course_id=1, category="midterm", assessment="Midterm", obtained=15.0, total=30.0)
        a_mark = m.Mark(student_id=st.id, course_id=1, category="attendance", assessment="Attendance", obtained=5.0, total=7.0)
        as_mark = m.Mark(student_id=st.id, course_id=1, category="assignment", assessment="Assignment", obtained=4.0, total=5.0)
        p_mark = m.Mark(student_id=st.id, course_id=1, category="presentation", assessment="Presentation", obtained=6.0, total=8.0)
        db.add_all([q_mark, m_mark, a_mark, as_mark, p_mark])
        db.commit()

        # At the exact limit, student is NOT in danger (boundary value is safe)
        d_exact = compute_student_detail(db, 1, st)
        assert d_exact["danger_zones"] == []
        assert d_exact["level"] == "safe"

        # Lower Quiz by 0.1 to 9.9 -> strictly below limit -> triggers Quiz danger zone!
        q_mark.obtained = 9.9
        db.commit()

        d_lower_q = compute_student_detail(db, 1, st)
        assert d_lower_q["danger_zones"] == ["quiz"]
        assert d_lower_q["level"] == "warning"

        # Lower Midterm by 0.1 to 14.9 -> triggers Midterm danger zone -> 2 zones -> critical!
        m_mark.obtained = 14.9
        db.commit()

        d_lower_m = compute_student_detail(db, 1, st)
        assert set(d_lower_m["danger_zones"]) == {"quiz", "midterm"}
        assert d_lower_m["level"] == "critical"

    finally:
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 7. Pending / Not Assessed parts do NOT trigger danger
def test_danger_zone_pending_not_assessed():
    db = SessionLocal()
    st = m.Student(student_code="TEST-DZ-PENDING", name="Pending Student")
    db.add(st)
    db.commit()
    db.refresh(st)
    db.add(m.Enrollment(student_id=st.id, course_id=1))
    db.commit()

    try:
        # Only Quiz recorded (12/15 >= 10.0). Midterm, Class parts, and Final-Term are ALL pending/unassessed.
        db.add(m.Mark(student_id=st.id, course_id=1, category="quiz", assessment="Quiz 1", obtained=12.0, total=15.0))
        db.commit()

        detail = compute_student_detail(db, 1, st)
        # Midterm is pending -> not danger
        # Class performance has no marks -> not danger
        # Final-Term is pending -> never danger
        assert detail["danger_zones"] == []
        assert detail["level"] == "safe"
        assert detail["zones"]["midterm"]["in_danger"] is False
        assert detail["zones"]["class_perf"]["in_danger"] is False

    finally:
        db.query(m.Mark).filter_by(student_id=st.id).delete()
        db.query(m.Enrollment).filter_by(student_id=st.id).delete()
        db.delete(st)
        db.commit()
        db.close()

# 8. Performance Warnings API includes danger_zone_counts and split lists
def test_performance_warnings_danger_zone_payload(faculty1_token):
    r = client.get("/api/courses/1/performance-warnings", headers={"Authorization": f"Bearer {faculty1_token}"})
    assert r.status_code == 200
    data = r.json()

    # Check danger_zone_counts
    assert "danger_zone_counts" in data
    counts = data["danger_zone_counts"]
    assert "quiz" in counts
    assert "midterm" in counts
    assert "class_perf" in counts
    assert all(isinstance(v, int) for v in counts.values())

    # Check doing_well list (safe students sorted highest percentage_so_far first)
    assert "doing_well" in data
    doing_well = data["doing_well"]
    for s in doing_well:
        assert s["level"] in ("safe", "ok")
        assert len(s.get("danger_zones", [])) == 0
    # Verify descending sort order by percentage_so_far
    scores = [s["percentage_so_far"] for s in doing_well]
    assert scores == sorted(scores, reverse=True)

    # Check needs_attention list (critical first, then warning, lowest score first)
    assert "needs_attention" in data
    needs_att = data["needs_attention"]
    seen_warning = False
    for s in needs_att:
        assert s["level"] in ("critical", "warning")
        if s["level"] == "warning":
            seen_warning = True
        elif s["level"] == "critical":
            assert not seen_warning, "Critical students must appear before warning students"

    # Check danger_zones and zones details in students table rows
    first_st = data["students"][0]
    assert "danger_zones" in first_st
    assert "zones" in first_st
    assert "quiz" in first_st["zones"]
    assert "midterm" in first_st["zones"]
    assert "class_perf" in first_st["zones"]
