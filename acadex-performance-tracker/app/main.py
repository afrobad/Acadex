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
    summary = {
        "critical": sum(1 for r in all_rows if r["level"] == "critical"),
        "warning": sum(1 for r in all_rows if r["level"] == "warning"),
        "ok": sum(1 for r in all_rows if r["level"] == "ok"),
        "total": len(all_rows),
    }
    display_rows = [r for r in all_rows if r["level"] != "ok"] if only_flagged else all_rows
    return {
        "course": course.code,
        "attendance_threshold": attendance_threshold,
        "marks_threshold": marks_threshold,
        "summary": summary,
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
