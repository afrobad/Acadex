from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="faculty", nullable=False)

    courses = relationship("Course", back_populates="faculty")

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    faculty = relationship("User", back_populates="courses")
    assessment_plans = relationship("AssessmentPlan", back_populates="course", cascade="all, delete-orphan")

class AssessmentPlan(Base):
    __tablename__ = "assessment_plans"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    category = Column(String, nullable=False)  # quiz, assignment, midterm, final, presentation, attendance
    max_marks = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("course_id", "category", name="uq_course_assessment_category"),
    )

    course = relationship("Course", back_populates="assessment_plans")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    student_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True)
    student_id = Column(ForeignKey("students.id"), nullable=False)
    course_id = Column(ForeignKey("courses.id"), nullable=False)
    student = relationship("Student")

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    student_id = Column(ForeignKey("students.id"), nullable=False)
    course_id = Column(ForeignKey("courses.id"), nullable=False)
    date = Column(Date, nullable=False)
    present = Column(Integer, nullable=False)  # 1 present, 0 absent

class Mark(Base):
    __tablename__ = "marks"
    id = Column(Integer, primary_key=True)
    student_id = Column(ForeignKey("students.id"), nullable=False)
    course_id = Column(ForeignKey("courses.id"), nullable=False)
    category = Column(String, nullable=False)     # quiz, assignment, presentation, midterm, final
    assessment = Column(String, nullable=False)   # Quiz 1, Midterm ...
    obtained = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
