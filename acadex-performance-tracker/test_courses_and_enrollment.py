import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))

from app.main import app
from seed import seed_database
from app.database import SessionLocal
from app import models as m

client = TestClient(app)

def test_course_creation_and_enrollment_suite():
    seed_database(verbose=False)

    # 1. Faculty 1 and Faculty 2 login tokens
    r1 = client.post("/api/auth/login", json={"email": "faculty@diu.edu.bd", "password": "Password123"})
    assert r1.status_code == 200
    token1 = r1.json()["access_token"]
    h1 = {"Authorization": f"Bearer {token1}"}

    r2 = client.post("/api/auth/login", json={"email": "sadia.faculty@diu.edu.bd", "password": "Password123"})
    assert r2.status_code == 200
    token2 = r2.json()["access_token"]
    h2 = {"Authorization": f"Bearer {token2}"}

    # -------------------------------------------------------------
    # SECTION A: POST /api/courses
    # -------------------------------------------------------------
    print("--- Testing POST /api/courses ---")

    # A1. Unauthenticated request -> 401
    r = client.post("/api/courses", json={"code": "CSE 499", "name": "Senior Project"})
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"

    # A2. Validation: Empty or whitespace code -> 422
    r = client.post("/api/courses", headers=h1, json={"code": "   ", "name": "Senior Project"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

    # A3. Validation: Missing code -> 422
    r = client.post("/api/courses", headers=h1, json={"name": "Senior Project"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    # A4. Validation: Empty or whitespace name -> 422
    r = client.post("/api/courses", headers=h1, json={"code": "CSE 499", "name": "  "})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    # A5. Validation: Max length > 100 -> 422
    r = client.post("/api/courses", headers=h1, json={"code": "A" * 101, "name": "Senior Project"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    r = client.post("/api/courses", headers=h1, json={"code": "CSE 499", "name": "B" * 101})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    # A6. Successful course creation by Faculty 1
    r = client.post("/api/courses", headers=h1, json={"code": "CSE 323", "name": "Operating Systems"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    new_course = r.json()
    assert new_course["code"] == "CSE 323"
    assert new_course["name"] == "Operating Systems"
    course_id = new_course["id"]

    # A7. Check default AssessmentPlan automatically created with total 105
    plan_res = client.get(f"/api/courses/{course_id}/assessment-plan", headers=h1)
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["total_max_marks"] == 105.0
    items_map = {item["category"]: item["max_marks"] for item in plan_data["items"]}
    assert items_map == {
        "quiz": 15.0,
        "assignment": 5.0,
        "midterm": 30.0,
        "final": 40.0,
        "presentation": 8.0,
        "attendance": 7.0
    }

    # A8. Duplicate code for SAME faculty -> 400
    r_dup = client.post("/api/courses", headers=h1, json={"code": "CSE 323", "name": "Operating Systems Lab"})
    assert r_dup.status_code == 400, f"Expected 400, got {r_dup.status_code}: {r_dup.text}"
    assert "already teach" in r_dup.json()["detail"].lower()

    # A9. Same code for DIFFERENT faculty -> 201 (unique per faculty)
    r_f2 = client.post("/api/courses", headers=h2, json={"code": "CSE 323", "name": "Operating Systems - Sadia"})
    assert r_f2.status_code == 201, f"Expected 201, got {r_f2.status_code}: {r_f2.text}"
    assert r_f2.json()["faculty_id"] != new_course["faculty_id"]

    # -------------------------------------------------------------
    # SECTION B: POST /api/courses/{course_id}/students
    # -------------------------------------------------------------
    print("--- Testing POST /api/courses/{course_id}/students ---")

    # B1. Unauthenticated request -> 401
    r = client.post(f"/api/courses/{course_id}/students", json={
        "student_code": "241-35-501", "name": "Farhan Ali", "email": "farhan@diu.edu.bd"
    })
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"

    # B2. Cross-faculty attempt: Faculty 2 tries to enroll student into Faculty 1 course -> 404
    r = client.post(f"/api/courses/{course_id}/students", headers=h2, json={
        "student_code": "241-35-501", "name": "Farhan Ali", "email": "farhan@diu.edu.bd"
    })
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"

    # B3. Invalid student_code format (must be like 241-35-101) -> 422
    invalid_codes = ["invalid-code", "24135101", "24-35-101", "241-3-101", "241-35-10", "ABC-35-101"]
    for bad_code in invalid_codes:
        r = client.post(f"/api/courses/{course_id}/students", headers=h1, json={
            "student_code": bad_code, "name": "Test Student", "email": "test@diu.edu.bd"
        })
        assert r.status_code == 422, f"Expected 422 for bad code '{bad_code}', got {r.status_code}: {r.text}"

    # B4. Invalid email format -> 422
    r = client.post(f"/api/courses/{course_id}/students", headers=h1, json={
        "student_code": "241-35-501", "name": "Farhan Ali", "email": "not-an-email"
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    # B5. Empty name -> 422
    r = client.post(f"/api/courses/{course_id}/students", headers=h1, json={
        "student_code": "241-35-501", "name": "   ", "email": "farhan@diu.edu.bd"
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    # B6. Successful enrollment of a NEW student
    r = client.post(f"/api/courses/{course_id}/students", headers=h1, json={
        "student_code": "241-35-501", "name": "Farhan Ali", "email": "farhan@diu.edu.bd"
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["student_code"] == "241-35-501"
    assert data["name"] == "Farhan Ali"
    assert data["email"] == "farhan@diu.edu.bd"
    assert data["course_id"] == course_id

    # Verify student was inserted in students table
    db = SessionLocal()
    st = db.query(m.Student).filter_by(student_code="241-35-501").first()
    assert st is not None
    assert st.name == "Farhan Ali"
    db.close()

    # B7. Duplicate enrollment of the same student in the same course -> 400
    r_dup_enroll = client.post(f"/api/courses/{course_id}/students", headers=h1, json={
        "student_code": "241-35-501", "name": "Farhan Ali", "email": "farhan@diu.edu.bd"
    })
    assert r_dup_enroll.status_code == 400, f"Expected 400, got {r_dup_enroll.status_code}: {r_dup_enroll.text}"
    assert "already enrolled" in r_dup_enroll.json()["detail"].lower()

    # B8. Enroll an EXISTING student (e.g. 241-35-101 from SE 331) into new course CSE 323
    # Check total student count before
    db = SessionLocal()
    total_students_before = db.query(m.Student).count()
    db.close()

    r_existing = client.post(f"/api/courses/{course_id}/students", headers=h1, json={
        "student_code": "241-35-101", "name": "Rafi Ahmed", "email": "s1@diu.edu.bd"
    })
    assert r_existing.status_code == 201, f"Expected 201, got {r_existing.status_code}: {r_existing.text}"
    assert r_existing.json()["student_code"] == "241-35-101"

    # Verify that NO duplicate student record was created
    db = SessionLocal()
    total_students_after = db.query(m.Student).count()
    assert total_students_after == total_students_before, "Existing student should be reused, not duplicated in students table"
    db.close()

    # -------------------------------------------------------------
    # SECTION C: Empty Course Handling
    # -------------------------------------------------------------
    print("--- Testing Empty Course Metrics ---")

    # Create another course with NO students enrolled yet
    r_empty_c = client.post("/api/courses", headers=h1, json={"code": "CSE 490", "name": "Cloud Computing"})
    assert r_empty_c.status_code == 201
    empty_course_id = r_empty_c.json()["id"]

    # Warnings / summary on empty course
    r_warn = client.get(f"/api/courses/{empty_course_id}/performance-warnings", headers=h1)
    assert r_warn.status_code == 200, f"Expected 200, got {r_warn.status_code}: {r_warn.text}"
    warn_data = r_warn.json()
    assert warn_data["summary"] == {"critical": 0, "warning": 0, "ok": 0, "total": 0}
    assert warn_data["students"] == []
    assert warn_data["all_students"] == []

    print("[ALL TESTS PASSED] Course creation, enrollment, and empty state verification succeeded!")
