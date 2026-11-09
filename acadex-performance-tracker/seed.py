"""Synthetic data (proposal: no real student data). Run: python seed.py"""
import random
import datetime
from app.database import Base, engine, SessionLocal
from app import models as m
from app.auth import hash_password

def seed_database(verbose=True):
    random.seed(7)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()

    # 1. Create Demo Faculty User with hashed password
    demo_faculty = m.User(
        name="Dr. Kamrul Hasan",
        email="faculty@diu.edu.bd",
        hashed_password=hash_password("Password123"),
        role="faculty"
    )
    db.add(demo_faculty)

    # 2. Create another faculty member to verify course access isolation (RBAC)
    other_faculty = m.User(
        name="Dr. Sadia Sultana",
        email="sadia.faculty@diu.edu.bd",
        hashed_password=hash_password("Password123"),
        role="faculty"
    )
    db.add(other_faculty)
    db.flush()

    # 3. Create courses:
    # Demo Faculty owns 3 courses: SE 331 (ID 1), SE 311 (ID 3), CSE 221 (ID 4)
    # Other Faculty owns 1 course: SE 412 (ID 2)
    course_se331 = m.Course(code="SE 331", name="Software Engineering Design", faculty_id=demo_faculty.id)
    db.add(course_se331)

    course_se412 = m.Course(code="SE 412", name="Software Architecture & Design Patterns", faculty_id=other_faculty.id)
    db.add(course_se412)

    course_se311 = m.Course(code="SE 311", name="Software Requirement Engineering", faculty_id=demo_faculty.id)
    db.add(course_se311)

    course_cse221 = m.Course(code="CSE 221", name="Data Structures", faculty_id=demo_faculty.id)
    db.add(course_cse221)
    db.flush()

    # 4. Assessment Plans
    # 105 Plan (Quiz 15, Assignment 5, Midterm 30, Final 40, Presentation 8, Attendance 7)
    plan_105 = [
        ("quiz", 15.0),
        ("assignment", 5.0),
        ("midterm", 30.0),
        ("final", 40.0),
        ("presentation", 8.0),
        ("attendance", 7.0),
    ]

    # SE 331 Plan (105)
    for cat, max_m in plan_105:
        db.add(m.AssessmentPlan(course_id=course_se331.id, category=cat, max_marks=max_m))

    # SE 311 Plan (105)
    for cat, max_m in plan_105:
        db.add(m.AssessmentPlan(course_id=course_se311.id, category=cat, max_marks=max_m))

    # CSE 221 Plan (105)
    for cat, max_m in plan_105:
        db.add(m.AssessmentPlan(course_id=course_cse221.id, category=cat, max_marks=max_m))

    # SE 412 Plan (100) - Second Faculty
    plan_100 = [
        ("quiz", 20.0),
        ("assignment", 10.0),
        ("midterm", 25.0),
        ("final", 35.0),
        ("presentation", 5.0),
        ("attendance", 5.0),
    ]
    for cat, max_m in plan_100:
        db.add(m.AssessmentPlan(course_id=course_se412.id, category=cat, max_marks=max_m))
    db.flush()

    # 4b. Danger Zone Rules
    db.add(m.DangerZoneRule(course_id=course_se331.id, quiz_limit=10.0, midterm_limit=15.0, class_limit=15.0))
    db.add(m.DangerZoneRule(course_id=course_se311.id, quiz_limit=10.0, midterm_limit=15.0, class_limit=15.0))
    db.add(m.DangerZoneRule(course_id=course_cse221.id, quiz_limit=10.0, midterm_limit=15.0, class_limit=15.0))
    db.add(m.DangerZoneRule(course_id=course_se412.id, quiz_limit=12.0, midterm_limit=15.0, class_limit=15.0))
    db.flush()

    # 5. Helper function to seed attendance and marks for a course cohort
    def seed_cohort(course_obj, student_profile_pairs, start_date):
        for s, p in student_profile_pairs:
            db.add(m.Enrollment(student_id=s.id, course_id=course_obj.id))

            att_rate = 0.4 if p in ("poor_att", "both") else 0.9
            for d in range(20):
                db.add(m.Attendance(
                    student_id=s.id,
                    course_id=course_obj.id,
                    date=start_date + datetime.timedelta(days=d * 2),
                    present=int(random.random() < att_rate)
                ))

            low = p in ("poor_marks", "both")
            assessments = [
                ("quiz", "Quiz 1", 10),
                ("quiz", "Quiz 2", 10),
                ("assignment", "Assignment", 20),
                ("presentation", "Presentation", 10),
                ("midterm", "Midterm", 50),
            ]
            for cat, a, tot in assessments:
                pct = random.uniform(0.15, 0.38) if low else random.uniform(0.60, 0.95)
                db.add(m.Mark(
                    student_id=s.id,
                    course_id=course_obj.id,
                    category=cat,
                    assessment=a,
                    obtained=round(pct * tot, 1),
                    total=tot
                ))

    # Initial pool of 12 students for SE 331
    names_100 = [
        "Rafi Ahmed", "Nusrat Jahan", "Tanvir Hasan", "Sadia Islam", "Mahin Chowdhury", "Farhana Akter",
        "Imran Hossain", "Mim Sultana", "Arif Rahman", "Tasnim Ara", "Shakib Khan", "Jannat Ferdous"
    ]
    students_100 = []
    for i, n in enumerate(names_100, 1):
        s = m.Student(student_code=f"241-35-{100+i}", name=n, email=f"s{i}@diu.edu.bd")
        db.add(s)
        students_100.append(s)
    db.flush()

    # SE 331 cohort (12 students: 2 critical, 4 warning, 6 ok)
    profiles_se331 = [
        "good", "good", "poor_att", "poor_marks", "both", "good",
        "poor_att", "good", "poor_marks", "both", "good", "good"
    ]
    seed_cohort(course_se331, list(zip(students_100, profiles_se331)), datetime.date(2026, 9, 1))

    # SE 412 cohort (Second faculty: 5 students)
    profiles_se412 = ["good", "poor_att", "poor_marks", "good", "both"]
    seed_cohort(course_se412, list(zip(students_100[:5], profiles_se412)), datetime.date(2026, 9, 1))

    # Create new students with 241-35-2xx codes for SE 311 and CSE 221
    names_200 = [
        ("241-35-201", "Hasibul Hasan", "hasib.201@diu.edu.bd"),
        ("241-35-202", "Mehedi Hasan", "mehedi.202@diu.edu.bd"),
        ("241-35-203", "Anika Tabassum", "anika.203@diu.edu.bd"),
        ("241-35-204", "Kazi Nazmul", "nazmul.204@diu.edu.bd"),
        ("241-35-205", "Sabrina Sharmin", "sabrina.205@diu.edu.bd"),
        ("241-35-206", "Tariqul Islam", "tariq.206@diu.edu.bd"),
        ("241-35-207", "Lamia Rahman", "lamia.207@diu.edu.bd"),
        ("241-35-208", "Fahim Faisal", "fahim.208@diu.edu.bd"),
        ("241-35-209", "Rifat Jahan", "rifat.209@diu.edu.bd"),
        ("241-35-210", "Shahriar Kabir", "shahriar.210@diu.edu.bd"),
    ]
    students_200 = {}
    for code, name, email in names_200:
        s = m.Student(student_code=code, name=name, email=email)
        db.add(s)
        students_200[code] = s
    db.flush()

    # SE 311 cohort (11 students: 6 reused from SE 331 + 5 new students with 241-35-2xx):
    # Profiles designed to give a distinct summary:
    # 3 critical, 3 warning, 5 ok
    students_se311 = [
        students_100[0], students_100[1], students_100[2],
        students_100[3], students_100[4], students_100[5],
        students_200["241-35-201"], students_200["241-35-202"],
        students_200["241-35-203"], students_200["241-35-204"],
        students_200["241-35-205"]
    ]
    profiles_se311 = [
        "both", "both", "both", "poor_att", "poor_marks",
        "poor_att", "good", "good", "good", "good", "good"
    ]
    seed_cohort(course_se311, list(zip(students_se311, profiles_se311)), datetime.date(2026, 9, 2))

    # CSE 221 cohort (10 students: 5 reused from SE 331 + 5 new students with 241-35-2xx):
    # Profiles designed to give another distinct summary:
    # 1 critical, 4 warning, 5 ok
    students_cse221 = [
        students_100[6], students_100[7], students_100[8],
        students_100[9], students_100[10],
        students_200["241-35-206"], students_200["241-35-207"],
        students_200["241-35-208"], students_200["241-35-209"],
        students_200["241-35-210"]
    ]
    profiles_cse221 = [
        "both", "poor_marks", "poor_att", "poor_marks",
        "poor_att", "good", "good", "good", "good", "good"
    ]
    seed_cohort(course_cse221, list(zip(students_cse221, profiles_cse221)), datetime.date(2026, 9, 3))

    db.commit()
    if verbose:
        print("Seeding completed successfully.")
        print("Demo Faculty: faculty@diu.edu.bd (Password: Password123) -> Owns SE 331, SE 311, CSE 221 (Plans: 105)")
        print("Other Faculty: sadia.faculty@diu.edu.bd (Password: Password123) -> Owns SE 412 (Plan: 100)")
    return db

db = seed_database(verbose=False)

if __name__ == "__main__":
    seed_database(verbose=True)
