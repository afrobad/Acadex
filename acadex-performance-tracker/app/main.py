from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from . import models as m
from . import schemas as s
from .tracker import compute_warnings, compute_student_detail
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

Base.metadata.create_all(engine)
app = FastAPI(title="Acadex - Performance Tracker (FR-03)")

@app.post("/api/auth/register", response_model=s.Token, status_code=status.HTTP_201_CREATED)
def register(payload: s.UserRegister, db: Session = Depends(get_db)):
    email_clean = payload.email.lower().strip()
    existing_user = db.query(m.User).filter(m.User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    user = m.User(
        name=payload.name.strip(),
        email=email_clean,
        hashed_password=hash_password(payload.password),
        role=payload.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": s.UserOut.model_validate(user)
    }

@app.post("/api/auth/login", response_model=s.Token)
def login(payload: s.UserLogin, db: Session = Depends(get_db)):
    email_clean = payload.email.lower().strip()
    user = db.query(m.User).filter(m.User.email == email_clean).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": s.UserOut.model_validate(user)
    }

@app.get("/api/auth/me", response_model=s.UserOut)
def get_me(current_user: m.User = Depends(get_current_user)):
    return s.UserOut.model_validate(current_user)

@app.get("/api/courses")
def my_courses(
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Faculty sees only own courses (RBAC)
    cs = db.query(m.Course).filter_by(faculty_id=current_user.id).all()
    return [{"id": c.id, "code": c.code, "name": c.name} for c in cs]

@app.post("/api/courses", response_model=s.CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: s.CourseCreate,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validation: code unique per faculty
    clean_code = payload.code.strip()
    clean_name = payload.name.strip()
    existing = db.query(m.Course).filter(
        m.Course.faculty_id == current_user.id,
        m.Course.code.ilike(clean_code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already teach a course with code '{clean_code}'."
        )

    # Create Course owned by logged-in faculty
    course = m.Course(
        code=clean_code,
        name=clean_name,
        faculty_id=current_user.id
    )
    db.add(course)
    db.flush()

    # Automatically create the default AssessmentPlan:
    # quiz 15, assignment 5, midterm 30, final 40, presentation 8, attendance 7
    default_plan = [
        ("quiz", 15.0),
        ("assignment", 5.0),
        ("midterm", 30.0),
        ("final", 40.0),
        ("presentation", 8.0),
        ("attendance", 7.0),
    ]
    for cat, max_m in default_plan:
        db.add(m.AssessmentPlan(
            course_id=course.id,
            category=cat,
            max_marks=max_m
        ))

    # Automatically create the default DangerZoneRule:
    # quiz 10.0, midterm 15.0, class_perf 15.0
    db.add(m.DangerZoneRule(
        course_id=course.id,
        quiz_limit=10.0,
        midterm_limit=15.0,
        class_limit=15.0
    ))

    db.commit()
    db.refresh(course)
    return course

@app.post("/api/courses/{course_id}/students", response_model=s.StudentEnrollOut, status_code=status.HTTP_201_CREATED)
def enroll_student(
    course_id: int,
    payload: s.StudentEnroll,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:  # own course only, else 404
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    student_code = payload.student_code.strip()
    student = db.query(m.Student).filter(m.Student.student_code == student_code).first()

    if not student:
        student = m.Student(
            student_code=student_code,
            name=payload.name.strip(),
            email=str(payload.email).strip().lower()
        )
        db.add(student)
        db.flush()

    # Reject duplicate enrollment
    existing_enrollment = db.query(m.Enrollment).filter_by(course_id=course.id, student_id=student.id).first()
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student '{student.student_code}' is already enrolled in course '{course.code}'."
        )

    enrollment = m.Enrollment(student_id=student.id, course_id=course.id)
    db.add(enrollment)
    db.commit()

    return {
        "student_id": student.id,
        "student_code": student.student_code,
        "name": student.name,
        "email": student.email,
        "course_id": course.id,
        "course_code": course.code,
        "message": f"Student {student.name} ({student.student_code}) successfully enrolled in {course.code}."
    }

@app.get("/api/courses/{course_id}/performance-warnings")
def warnings(
    course_id: int,
    attendance_threshold: float = Query(60, ge=0, le=100),
    marks_threshold: float = Query(40, ge=0, le=100),
    only_flagged: bool = False,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:  # faculty sees only own courses (RBAC)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    all_rows = compute_warnings(db, course_id, attendance_threshold, marks_threshold)
    safe_count = sum(1 for r in all_rows if r["level"] in ("safe", "ok"))
    crit_count = sum(1 for r in all_rows if r["level"] == "critical")
    warn_count = sum(1 for r in all_rows if r["level"] == "warning")
    summary = {
        "critical": crit_count,
        "warning": warn_count,
        "safe": safe_count,
        "ok": safe_count,
        "total": len(all_rows),
    }

    danger_zone_counts = {
        "quiz": sum(1 for r in all_rows if "quiz" in r.get("danger_zones", [])),
        "midterm": sum(1 for r in all_rows if "midterm" in r.get("danger_zones", [])),
        "class_perf": sum(1 for r in all_rows if "class_perf" in r.get("danger_zones", [])),
    }

    safe_students = [r for r in all_rows if r["level"] in ("safe", "ok")]
    doing_well = sorted(safe_students, key=lambda s: s.get("percentage_so_far", 0.0), reverse=True)

    critical_students = sorted([r for r in all_rows if r["level"] == "critical"], key=lambda s: s.get("percentage_so_far", 0.0))
    warning_students = sorted([r for r in all_rows if r["level"] == "warning"], key=lambda s: s.get("percentage_so_far", 0.0))
    needs_attention = critical_students + warning_students

    display_rows = [r for r in all_rows if r["level"] not in ("safe", "ok")] if only_flagged else all_rows
    return {
        "course": course.code,
        "attendance_threshold": attendance_threshold,
        "marks_threshold": marks_threshold,
        "summary": summary,
        "danger_zone_counts": danger_zone_counts,
        "doing_well": doing_well,
        "needs_attention": needs_attention,
        "students": display_rows,
        "all_students": all_rows
    }

@app.get("/api/courses/{course_id}/students/{student_code}/performance")
def get_student_performance(
    course_id: int,
    student_code: str,
    attendance_threshold: float = Query(60, ge=0, le=100),
    marks_threshold: float = Query(40, ge=0, le=100),
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:  # faculty sees only own courses (RBAC)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    student = db.query(m.Student).filter(m.Student.student_code == student_code.strip()).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with code '{student_code}' not found"
        )

    enrollment = db.query(m.Enrollment).filter_by(course_id=course_id, student_id=student.id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_code}' is not enrolled in course '{course.code}'"
        )

    detail = compute_student_detail(db, course_id, student, attendance_threshold, marks_threshold)
    return detail

@app.post("/api/courses/{course_id}/attendance", status_code=status.HTTP_201_CREATED)
def record_attendance(
    course_id: int,
    payload: s.AttendanceCreate,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:  # faculty sees only own courses (RBAC)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    student = db.query(m.Student).filter(m.Student.student_code == payload.student_code.strip()).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with code '{payload.student_code}' not found"
        )

    enrollment = db.query(m.Enrollment).filter_by(course_id=course_id, student_id=student.id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student '{payload.student_code}' is not enrolled in course '{course.code}'"
        )

    att = m.Attendance(
        student_id=student.id,
        course_id=course_id,
        date=payload.date,
        present=payload.present
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    return {
        "id": att.id,
        "student_id": student.id,
        "student_code": student.student_code,
        "course_id": course_id,
        "date": str(att.date),
        "present": att.present,
        "message": f"Attendance recorded for {student.name} ({student.student_code})."
    }

@app.post("/api/courses/{course_id}/marks", status_code=status.HTTP_201_CREATED)
def record_mark(
    course_id: int,
    payload: s.MarkCreate,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:  # faculty sees only own courses (RBAC)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    student = db.query(m.Student).filter(m.Student.student_code == payload.student_code.strip()).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with code '{payload.student_code}' not found"
        )

    enrollment = db.query(m.Enrollment).filter_by(course_id=course_id, student_id=student.id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student '{payload.student_code}' is not enrolled in course '{course.code}'"
        )

    mk = m.Mark(
        student_id=student.id,
        course_id=course_id,
        category=payload.category,
        assessment=payload.assessment,
        obtained=payload.obtained,
        total=payload.total
    )
    db.add(mk)
    db.commit()
    db.refresh(mk)

    return {
        "id": mk.id,
        "student_id": student.id,
        "student_code": student.student_code,
        "course_id": course_id,
        "category": mk.category,
        "assessment": mk.assessment,
        "obtained": mk.obtained,
        "total": mk.total,
        "percentage": round(mk.obtained / mk.total * 100, 1),
        "message": f"Mark recorded for {student.name} ({student.student_code}): {mk.assessment} ({mk.obtained}/{mk.total})."
    }

@app.get("/api/courses/{course_id}/assessment-plan")
def get_assessment_plan(
    course_id: int,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:  # faculty sees only own courses (RBAC)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    plans = db.query(m.AssessmentPlan).filter_by(course_id=course_id).all()
    items = [{"category": p.category, "max_marks": p.max_marks} for p in plans]
    total = round(sum(p.max_marks for p in plans), 2)
    return {
        "course_id": course.id,
        "course_code": course.code,
        "items": items,
        "total_max_marks": total
    }

@app.put("/api/courses/{course_id}/assessment-plan")
def update_assessment_plan(
    course_id: int,
    payload: list[s.AssessmentPlanItem],
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:  # faculty sees only own courses (RBAC)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Validate categories: must have all 6 categories, no duplicates, max_marks >= 0
    categories = [item.category.lower().strip() for item in payload]
    if len(categories) != len(set(categories)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Duplicate categories are not allowed in assessment plan."
        )

    required_categories = {"quiz", "assignment", "midterm", "final", "presentation", "attendance"}
    if set(categories) != required_categories:
        missing = required_categories - set(categories)
        extra = set(categories) - required_categories
        msgs = []
        if missing:
            msgs.append(f"Missing categories: {', '.join(sorted(missing))}")
        if extra:
            msgs.append(f"Invalid categories: {', '.join(sorted(extra))}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="; ".join(msgs) if msgs else "All 6 categories must be present."
        )

    for item in payload:
        if item.max_marks < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"max_marks for {item.category} cannot be negative."
            )

    # Upsert each category row
    existing = {p.category.lower(): p for p in db.query(m.AssessmentPlan).filter_by(course_id=course_id).all()}
    for item in payload:
        cat = item.category.lower().strip()
        if cat in existing:
            existing[cat].max_marks = item.max_marks
        else:
            new_plan = m.AssessmentPlan(
                course_id=course_id,
                category=cat,
                max_marks=item.max_marks
            )
            db.add(new_plan)

    db.commit()

    plans = db.query(m.AssessmentPlan).filter_by(course_id=course_id).all()
    items = [{"category": p.category, "max_marks": p.max_marks} for p in plans]
    total = round(sum(p.max_marks for p in plans), 2)
    return {
        "course_id": course.id,
        "course_code": course.code,
        "items": items,
        "total_max_marks": total
    }

@app.get("/api/courses/{course_id}/danger-zone-rules", response_model=s.DangerZoneRuleOut)
def get_danger_zone_rules(
    course_id: int,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    rule = db.query(m.DangerZoneRule).filter_by(course_id=course_id).first()
    if not rule:
        rule = m.DangerZoneRule(
            course_id=course.id,
            quiz_limit=10.0,
            midterm_limit=15.0,
            class_limit=15.0
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

    plans = db.query(m.AssessmentPlan).filter_by(course_id=course_id).all()
    plan_map = {p.category.lower(): p.max_marks for p in plans}
    quiz_max = plan_map.get("quiz", 15.0)
    midterm_max = plan_map.get("midterm", 30.0)
    class_max = plan_map.get("attendance", 7.0) + plan_map.get("assignment", 5.0) + plan_map.get("presentation", 8.0)

    return {
        "course_id": course.id,
        "quiz_limit": rule.quiz_limit,
        "midterm_limit": rule.midterm_limit,
        "class_limit": rule.class_limit,
        "max_possible": {
            "quiz": quiz_max,
            "midterm": midterm_max,
            "class": class_max
        }
    }

@app.put("/api/courses/{course_id}/danger-zone-rules", response_model=s.DangerZoneRuleOut)
def update_danger_zone_rules(
    course_id: int,
    payload: s.DangerZoneRuleUpdate,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    plans = db.query(m.AssessmentPlan).filter_by(course_id=course_id).all()
    plan_map = {p.category.lower(): p.max_marks for p in plans}
    quiz_max = plan_map.get("quiz", 15.0)
    midterm_max = plan_map.get("midterm", 30.0)
    class_max = plan_map.get("attendance", 7.0) + plan_map.get("assignment", 5.0) + plan_map.get("presentation", 8.0)

    if payload.quiz_limit < 0 or payload.quiz_limit > quiz_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Quiz limit must be between 0 and {quiz_max} (plan max)."
        )
    if payload.midterm_limit < 0 or payload.midterm_limit > midterm_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Midterm limit must be between 0 and {midterm_max} (plan max)."
        )
    if payload.class_limit < 0 or payload.class_limit > class_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Class performance limit must be between 0 and {class_max} (combined attendance + assignment + presentation plan max)."
        )

    rule = db.query(m.DangerZoneRule).filter_by(course_id=course_id).first()
    if not rule:
        rule = m.DangerZoneRule(
            course_id=course.id,
            quiz_limit=payload.quiz_limit,
            midterm_limit=payload.midterm_limit,
            class_limit=payload.class_limit
        )
        db.add(rule)
    else:
        rule.quiz_limit = payload.quiz_limit
        rule.midterm_limit = payload.midterm_limit
        rule.class_limit = payload.class_limit

    db.commit()
    db.refresh(rule)

    return {
        "course_id": course.id,
        "quiz_limit": rule.quiz_limit,
        "midterm_limit": rule.midterm_limit,
        "class_limit": rule.class_limit,
        "max_possible": {
            "quiz": quiz_max,
            "midterm": midterm_max,
            "class": class_max
        }
    }

@app.get("/api/courses/{course_id}/marks/grid")
def get_course_marks_grid(
    course_id: int,
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    plans = db.query(m.AssessmentPlan).filter_by(course_id=course_id).all()
    default_plan = {
        "quiz": 15.0,
        "assignment": 5.0,
        "midterm": 30.0,
        "final": 40.0,
        "presentation": 8.0,
        "attendance": 7.0,
    }
    plan_map = {p.category.lower(): p.max_marks for p in plans}
    for k, v in default_plan.items():
        if k not in plan_map:
            plan_map[k] = v

    quiz_max = plan_map["quiz"]
    assignment_max = plan_map["assignment"]
    presentation_max = plan_map["presentation"]
    midterm_max = plan_map["midterm"]
    attendance_max = plan_map["attendance"]
    final_max = plan_map["final"]

    columns = [
        {"key": "quiz_1", "label": "Quiz 1", "category": "quiz", "assessment": "Quiz 1", "max_marks": quiz_max, "disabled": False},
        {"key": "quiz_2", "label": "Quiz 2", "category": "quiz", "assessment": "Quiz 2", "max_marks": quiz_max, "disabled": False},
        {"key": "assignment", "label": "Assignment", "category": "assignment", "assessment": "Assignment", "max_marks": assignment_max, "disabled": False},
        {"key": "presentation", "label": "Presentation", "category": "presentation", "assessment": "Presentation", "max_marks": presentation_max, "disabled": False},
        {"key": "midterm", "label": "Midterm", "category": "midterm", "assessment": "Midterm", "max_marks": midterm_max, "disabled": False},
        {"key": "attendance", "label": "Attendance", "category": "attendance", "assessment": "Attendance", "max_marks": attendance_max, "disabled": False},
        {"key": "final", "label": "Final-Term", "category": "final", "assessment": "Final", "max_marks": final_max, "disabled": True, "pending": True},
    ]

    enrollments = db.query(m.Enrollment).filter_by(course_id=course.id).all()
    enrollments.sort(key=lambda e: e.student.student_code)

    students_data = []
    for e in enrollments:
        st = e.student
        marks = db.query(m.Mark).filter_by(student_id=st.id, course_id=course.id).all()
        att = db.query(m.Attendance).filter_by(student_id=st.id, course_id=course.id).all()

        marks_dict = {}
        for mk in marks:
            cat = (mk.category or "").lower()
            if cat == "quiz":
                col_max = quiz_max
            elif cat == "assignment":
                col_max = assignment_max
            elif cat == "presentation":
                col_max = presentation_max
            elif cat == "midterm":
                col_max = midterm_max
            elif cat == "attendance":
                col_max = attendance_max
            else:
                col_max = mk.total

            if mk.total == col_max:
                val = mk.obtained
            elif mk.total and mk.total > 0:
                val = round((mk.obtained / mk.total) * col_max, 1)
            else:
                val = mk.obtained
            marks_dict[mk.assessment] = val

        # If direct attendance mark wasn't recorded, prefill with attendance calculated from daily records
        if "Attendance" not in marks_dict and att:
            att_pct = sum(a.present for a in att) / len(att)
            marks_dict["Attendance"] = round(att_pct * attendance_max, 1)

        students_data.append({
            "student_id": st.id,
            "student_code": st.student_code,
            "name": st.name,
            "marks": marks_dict
        })

    return {
        "course_id": course.id,
        "course_code": course.code,
        "course_name": course.name,
        "columns": columns,
        "students": students_data
    }

@app.post("/api/courses/{course_id}/marks/bulk")
def save_bulk_marks(
    course_id: int,
    payload: list[s.BulkMarkItem],
    current_user: m.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.get(m.Course, course_id)
    if not course or course.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if not payload:
        return {
            "course_id": course.id,
            "course_code": course.code,
            "saved_count": 0,
            "message": "No mark changes were provided."
        }

    enrollments = db.query(m.Enrollment).filter_by(course_id=course.id).all()
    enrolled_students = {e.student.student_code: e.student for e in enrollments}

    # Step 1: Pre-validate all items before database modification
    for idx, item in enumerate(payload):
        student = enrolled_students.get(item.student_code)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Student '{item.student_code}' is not enrolled in course '{course.code}'."
            )
        if item.total <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Row {idx+1}: Total marks must be greater than 0."
            )
        if item.obtained < 0 or item.obtained > item.total:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Row {idx+1}: Obtained marks ({item.obtained}) must be between 0 and total ({item.total})."
            )
        if item.category.lower() not in s.ALLOWED_PLAN_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Row {idx+1}: Category '{item.category}' is not allowed."
            )

    # Step 2: Atomic Upsert in one transaction
    try:
        saved_count = 0
        for item in payload:
            student = enrolled_students[item.student_code]
            category_clean = item.category.lower().strip()
            assessment_clean = item.assessment.strip()

            existing_mark = db.query(m.Mark).filter(
                m.Mark.student_id == student.id,
                m.Mark.course_id == course.id,
                m.Mark.category == category_clean,
                m.Mark.assessment == assessment_clean
            ).first()

            if existing_mark:
                existing_mark.obtained = float(item.obtained)
                existing_mark.total = float(item.total)
            else:
                new_mark = m.Mark(
                    student_id=student.id,
                    course_id=course.id,
                    category=category_clean,
                    assessment=assessment_clean,
                    obtained=float(item.obtained),
                    total=float(item.total)
                )
                db.add(new_mark)
            saved_count += 1

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save marks: {str(exc)}"
        )

    return {
        "course_id": course.id,
        "course_code": course.code,
        "saved_count": saved_count,
        "message": f"Successfully updated {saved_count} mark{'s' if saved_count != 1 else ''}."
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/login")
def login_page():
    return FileResponse("static/login.html")

@app.get("/login.html")
def login_html():
    return FileResponse("static/login.html")

@app.get("/register")
def register_page():
    return FileResponse("static/register.html")
