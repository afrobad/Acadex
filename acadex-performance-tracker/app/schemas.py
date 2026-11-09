import re
import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, ConfigDict
from typing import Optional

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name of the faculty member")
    email: EmailStr = Field(..., description="Valid institutional or personal email")
    password: str = Field(..., description="Password (min 8 chars, 1 letter, 1 number)")
    role: str = Field(default="faculty", description="Role: faculty")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number.")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters.")
        return cleaned

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class AttendanceCreate(BaseModel):
    student_code: str = Field(..., min_length=1, description="Student code / ID")
    date: datetime.date = Field(..., description="Date of attendance")
    present: int = Field(default=1, ge=0, le=1, description="1 for present, 0 for absent")

    @field_validator("student_code")
    @classmethod
    def validate_student_code(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Student ID cannot be empty.")
        return cleaned

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: datetime.date) -> datetime.date:
        if v > datetime.date.today():
            raise ValueError("Date cannot be in the future.")
        return v

class MarkCreate(BaseModel):
    student_code: str = Field(..., min_length=1, description="Student code / ID")
    category: str = Field(..., description="quiz, assignment, presentation, or midterm")
    assessment: str = Field(..., min_length=1, description="Assessment display name")
    obtained: float = Field(..., description="Obtained marks")
    total: float = Field(..., description="Total possible marks")

    @field_validator("student_code")
    @classmethod
    def validate_student_code(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Student ID cannot be empty.")
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {"quiz", "assignment", "presentation", "midterm", "final"}
        cleaned = v.strip().lower()
        if cleaned not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(sorted(allowed))}")
        return cleaned

    @field_validator("assessment")
    @classmethod
    def validate_assessment(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Assessment name cannot be empty.")
        return cleaned

    @field_validator("total")
    @classmethod
    def validate_total(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Total marks must be greater than 0.")
        return v

    @field_validator("obtained")
    @classmethod
    def validate_obtained(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Obtained marks cannot be negative.")
        return v

    @model_validator(mode="after")
    def validate_obtained_vs_total(self):
        if self.obtained > self.total:
            raise ValueError(f"Obtained marks ({self.obtained}) cannot exceed total marks ({self.total}).")
        return self

ALLOWED_PLAN_CATEGORIES = {"quiz", "assignment", "midterm", "final", "presentation", "attendance"}

class BulkMarkItem(BaseModel):
    student_code: str = Field(..., min_length=1, description="Student code / ID")
    category: str = Field(..., description="quiz, assignment, presentation, midterm, attendance, or final")
    assessment: str = Field(..., min_length=1, description="Assessment display name")
    obtained: float = Field(..., description="Obtained marks")
    total: float = Field(..., description="Total possible marks")

    @field_validator("student_code")
    @classmethod
    def validate_student_code(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Student ID cannot be empty.")
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ALLOWED_PLAN_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(sorted(ALLOWED_PLAN_CATEGORIES))}")
        return cleaned

    @field_validator("assessment")
    @classmethod
    def validate_assessment(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Assessment name cannot be empty.")
        return cleaned

    @field_validator("total")
    @classmethod
    def validate_total(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Total marks must be greater than 0.")
        return v

    @field_validator("obtained")
    @classmethod
    def validate_obtained(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Obtained marks cannot be negative.")
        return v

    @model_validator(mode="after")
    def validate_obtained_vs_total(self):
        if self.obtained > self.total:
            raise ValueError(f"Obtained marks ({self.obtained}) cannot exceed total marks ({self.total}).")
        return self

class AssessmentPlanItem(BaseModel):
    category: str = Field(..., description="quiz, assignment, midterm, final, presentation, or attendance")
    max_marks: float = Field(..., ge=0, description="Maximum marks weight (must be >= 0)")

    @field_validator("category")
    @classmethod
    def validate_plan_category(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ALLOWED_PLAN_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(sorted(ALLOWED_PLAN_CATEGORIES))}")
        return cleaned

class AssessmentPlanResponse(BaseModel):
    course_id: int
    course_code: str
    items: list[AssessmentPlanItem]
    total_max_marks: float

class CourseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100, description="Course code (e.g. CSE 323)")
    name: str = Field(..., min_length=1, max_length=100, description="Course name (e.g. Operating Systems)")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Course code cannot be empty.")
        if len(cleaned) > 100:
            raise ValueError("Course code cannot exceed 100 characters.")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Course name cannot be empty.")
        if len(cleaned) > 100:
            raise ValueError("Course name cannot exceed 100 characters.")
        return cleaned

class CourseOut(BaseModel):
    id: int
    code: str
    name: str
    faculty_id: int

    model_config = ConfigDict(from_attributes=True)

class StudentEnroll(BaseModel):
    student_code: str = Field(..., description="Student code format like 241-35-101")
    name: str = Field(..., min_length=1, max_length=100, description="Student full name")
    email: EmailStr = Field(..., description="Student institutional or contact email")

    @field_validator("student_code")
    @classmethod
    def validate_student_code_format(cls, v: str) -> str:
        cleaned = v.strip()
        if not re.match(r"^\d{3}-\d{2}-\d{3}$", cleaned):
            raise ValueError("Student code must match format like 241-35-101 (e.g. 3 digits - 2 digits - 3 digits).")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_student_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Student name cannot be empty.")
        if len(cleaned) > 100:
            raise ValueError("Student name cannot exceed 100 characters.")
        return cleaned

class StudentEnrollOut(BaseModel):
    student_id: int
    student_code: str
    name: str
    email: Optional[str] = None
    course_id: int
    course_code: str
    message: str

class DangerZoneRuleOut(BaseModel):
    course_id: int
    quiz_limit: float
    midterm_limit: float
    class_limit: float
    max_possible: dict[str, float]

class DangerZoneRuleUpdate(BaseModel):
    quiz_limit: float = Field(..., ge=0, description="Quiz danger threshold")
    midterm_limit: float = Field(..., ge=0, description="Midterm danger threshold")
    class_limit: float = Field(..., ge=0, description="Class performance danger threshold")
