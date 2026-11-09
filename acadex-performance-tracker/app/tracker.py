"""Performance Tracker logic. Deterministic Python only (AI-03): no LLM does the math."""
from sqlalchemy.orm import Session
from . import models as m

def _format_pct(val: float) -> str:
    """Format percentage value cleanly: 30.0 -> '30%', 32.5 -> '32.5%'."""
    if val is None:
        return ""
    if val == int(val):
        return f"{int(val)}%"
    return f"{val:.1f}%"

def _fmt_score(val: float) -> str:
    """Format obtained score cleanly: 3.0 -> '3.0', 3.75 -> '3.75'."""
    if val is None:
        return "0"
    if val == int(val):
        return f"{val:.1f}"
    return f"{val:.2f}".rstrip("0")

def _fmt_max(val: float) -> str:
    """Format max score cleanly: 8.0 -> '8', 15.0 -> '15'."""
    if val is None:
        return "0"
    return str(int(val)) if val == int(val) else str(val)

def compute_student_detail(db: Session, course_id: int, student: m.Student,
                           attendance_threshold: float = 60.0,
                           marks_threshold: float = 40.0):
    """Compute detailed performance metrics using the course Assessment Plan and Danger Zone Rules."""
    # 1. Load course Assessment Plan (with fallback defaults if unconfigured)
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

    # 2. Query student attendance and marks
    att = db.query(m.Attendance).filter_by(student_id=student.id, course_id=course_id).all()
    marks = db.query(m.Mark).filter_by(student_id=student.id, course_id=course_id).all()

    components = {}

    # Attendance: attendance percentage scaled to plan's attendance max marks
    # If a direct attendance mark exists, it wins over per-day attendance records
    att_max = plan_map.get("attendance", 7.0)
    direct_att_mark = next((mk for mk in marks if (getattr(mk, "category", "") or "").lower() == "attendance"), None)
    if direct_att_mark is not None and direct_att_mark.total:
        att_pct = round(direct_att_mark.obtained / direct_att_mark.total * 100, 1)
        att_obtained = round(direct_att_mark.obtained / direct_att_mark.total * att_max, 2)
        att_status = "low" if att_pct < attendance_threshold else "ok"
    elif not att:
        att_pct = None
        att_obtained = 0.0
        att_status = "pending"
    else:
        att_pct = round(sum(a.present for a in att) / len(att) * 100, 1)
        att_obtained = round(att_pct / 100.0 * att_max, 2)
        att_status = "low" if att_pct < attendance_threshold else "ok"

    components["attendance"] = {
        "obtained_marks": att_obtained,
        "max_marks": att_max,
        "percentage": att_pct,
        "status": att_status,
        "value": att_pct,                 # Backward-compatible alias
        "low": (att_status == "low"),     # Backward-compatible alias
    }

    # Quiz: average percentage of all quizzes, scaled to plan's quiz max marks
    quiz_max = plan_map.get("quiz", 15.0)
    quiz_marks = [mk for mk in marks if (getattr(mk, "category", None) or "").lower() == "quiz" and mk.total]
    if not quiz_marks:
        quiz_pct = None
        quiz_obtained = 0.0
        quiz_status = "pending"
    else:
        quiz_raw_ratio = sum(mk.obtained / mk.total for mk in quiz_marks) / len(quiz_marks)
        quiz_pct = round(quiz_raw_ratio * 100, 1)
        quiz_obtained = round(quiz_raw_ratio * quiz_max, 2)
        quiz_status = "low" if quiz_pct < marks_threshold else "ok"

    components["quiz"] = {
        "obtained_marks": quiz_obtained,
        "max_marks": quiz_max,
        "percentage": quiz_pct,
        "status": quiz_status,
        "value": quiz_pct,
        "low": (quiz_status == "low"),
    }

    # Other mark categories: assignment, presentation, midterm, final
    for cat in ["assignment", "presentation", "midterm", "final"]:
        cat_max = plan_map.get(cat, default_plan.get(cat, 10.0))
        cat_marks = [mk for mk in marks if (getattr(mk, "category", None) or "").lower() == cat and mk.total]
        if not cat_marks:
            cat_pct = None
            cat_obtained = 0.0
            cat_status = "pending"
        else:
            tot_ob = sum(mk.obtained for mk in cat_marks)
            tot_pos = sum(mk.total for mk in cat_marks)
            cat_ratio = tot_ob / tot_pos if tot_pos else 0.0
            cat_pct = round(cat_ratio * 100, 1)
            cat_obtained = round(cat_ratio * cat_max, 2)
            cat_status = "low" if cat_pct < marks_threshold else "ok"

        components[cat] = {
            "obtained_marks": cat_obtained,
            "max_marks": cat_max,
            "percentage": cat_pct,
            "status": cat_status,
            "value": cat_pct,
            "low": (cat_status == "low"),
        }

    # 3. Cumulative Standing (Excluding Pending categories from so-far calculation)
    non_pending = [c for c in components.values() if c["status"] != "pending"]
    total_obtained = round(sum(c["obtained_marks"] for c in non_pending), 2)
    total_assessed_max = round(sum(c["max_marks"] for c in non_pending), 2)
    all_categories = ["quiz", "assignment", "midterm", "final", "presentation", "attendance"]
    total_plan_max = round(sum(plan_map.get(k, 0.0) for k in all_categories), 2)

    percentage_so_far = round(total_obtained / total_assessed_max * 100, 1) if total_assessed_max > 0 else 0.0
    overall_score = percentage_so_far

    # Overall average marks across all assessed marks
    pcts = [round(mk.obtained / mk.total * 100, 1) for mk in marks if mk.total]
    avg = round(sum(pcts) / len(pcts), 1) if pcts else None

    # Individual assessments list
    assessments = [
        {
            "category": mk.category,
            "name": mk.assessment,
            "obtained": mk.obtained,
            "total": mk.total,
            "percentage": round(mk.obtained / mk.total * 100, 1) if mk.total else 0.0
        }
        for mk in marks
    ]

    # 4. Danger Zone Evaluation (Deterministic Python rules)
    rule = db.query(m.DangerZoneRule).filter_by(course_id=course_id).first()
    quiz_limit = rule.quiz_limit if rule else 10.0
    midterm_limit = rule.midterm_limit if rule else 15.0
    class_limit = rule.class_limit if rule else 15.0

    # Zone 1: Quiz (total quiz marks scaled to plan's quiz max below quiz_limit is danger)
    quiz_comp = components["quiz"]
    quiz_assessed = (quiz_comp["status"] != "pending")
    quiz_in_danger = quiz_assessed and (quiz_comp["obtained_marks"] < quiz_limit)

    # Zone 2: Midterm (midterm marks scaled to plan max below midterm_limit is danger)
    midterm_comp = components["midterm"]
    midterm_assessed = (midterm_comp["status"] != "pending")
    midterm_in_danger = midterm_assessed and (midterm_comp["obtained_marks"] < midterm_limit)

    # Zone 3: Class performance group (attendance + assignment + presentation combined below class_limit is danger)
    class_cats = ["attendance", "assignment", "presentation"]
    class_assessed = any(components[k]["status"] != "pending" for k in class_cats)
    class_obtained = round(sum(components[k]["obtained_marks"] for k in class_cats), 2)
    class_max = round(sum(components[k]["max_marks"] for k in class_cats), 2)
    class_in_danger = class_assessed and (class_obtained < class_limit)

    active_danger_zones = []
    reasons = []

    if quiz_in_danger:
        active_danger_zones.append("quiz")
        reasons.append(
            f"Quiz {_fmt_score(quiz_comp['obtained_marks'])}/{_fmt_max(quiz_comp['max_marks'])} is below the danger limit {_fmt_score(quiz_limit)}"
        )

    if midterm_in_danger:
        active_danger_zones.append("midterm")
        reasons.append(
            f"Midterm {_fmt_score(midterm_comp['obtained_marks'])}/{_fmt_max(midterm_comp['max_marks'])} is below the danger limit {_fmt_score(midterm_limit)}"
        )

    if class_in_danger:
        active_danger_zones.append("class_perf")
        reasons.append(
            f"Class performance {_fmt_score(class_obtained)}/{_fmt_max(class_max)} is below the danger limit {_fmt_score(class_limit)}"
        )

    # Status per student: no danger zones = Safe, one danger zone = Warning, two or more = Critical
    if len(active_danger_zones) >= 2:
        level = "critical"
    elif len(active_danger_zones) == 1:
        level = "warning"
    else:
        level = "safe"

    zones = {
        "quiz": {
            "name": "Quiz",
            "obtained": quiz_comp["obtained_marks"],
            "max": quiz_comp["max_marks"],
            "limit": quiz_limit,
            "in_danger": quiz_in_danger,
            "status": quiz_comp["status"],
            "badge_text": f"Quiz {_fmt_score(quiz_comp['obtained_marks'])}/{_fmt_score(quiz_limit)}"
        },
        "midterm": {
            "name": "Midterm",
            "obtained": midterm_comp["obtained_marks"],
            "max": midterm_comp["max_marks"],
            "limit": midterm_limit,
            "in_danger": midterm_in_danger,
            "status": midterm_comp["status"],
            "badge_text": f"Mid {_fmt_score(midterm_comp['obtained_marks'])}/{_fmt_score(midterm_limit)}"
        },
        "class_perf": {
            "name": "Class Performance",
            "obtained": class_obtained,
            "max": class_max,
            "limit": class_limit,
            "in_danger": class_in_danger,
            "status": "assessed" if class_assessed else "pending",
            "badge_text": f"Class {_fmt_score(class_obtained)}/{_fmt_score(class_limit)}",
            "breakdown": {
                "attendance": {
                    "obtained": components["attendance"]["obtained_marks"],
                    "max": components["attendance"]["max_marks"]
                },
                "assignment": {
                    "obtained": components["assignment"]["obtained_marks"],
                    "max": components["assignment"]["max_marks"]
                },
                "presentation": {
                    "obtained": components["presentation"]["obtained_marks"],
                    "max": components["presentation"]["max_marks"]
                }
            }
        }
    }

    danger_badges = [zones[z]["badge_text"] for z in active_danger_zones]

    # 5. "What-if" Final-Term Helper (Advisory Estimate)
    # Target: reach 40% of the total plan marks
    final_max = plan_map.get("final", default_plan.get("final", 40.0))
    target_overall_pct = 40.0
    target_marks = round((target_overall_pct / 100.0) * total_plan_max, 2)
    needed_final = round(target_marks - total_obtained, 2)

    if total_obtained >= target_marks:
        what_if_status = "Already safe"
        min_final_marks = 0.0
        min_final_pct = 0.0
        what_if_message = (
            f"Already safe: Current total ({_fmt_score(total_obtained)}/{_fmt_max(total_plan_max)}) "
            f"already reaches the {target_overall_pct:.0f}% course threshold ({_fmt_score(target_marks)} marks)."
        )
    elif final_max <= 0 or needed_final > final_max:
        what_if_status = "Not reachable"
        min_final_marks = None
        min_final_pct = None
        max_possible = round(total_obtained + final_max, 2)
        max_possible_pct = round((max_possible / total_plan_max) * 100, 1) if total_plan_max > 0 else 0.0
        what_if_message = (
            f"Not reachable: Even with maximum Final-Term marks ({_fmt_max(final_max)}), "
            f"highest achievable score is {_fmt_score(max_possible)}/{_fmt_max(total_plan_max)} ({max_possible_pct}%), "
            f"which cannot reach {target_overall_pct:.0f}% ({_fmt_score(target_marks)} marks)."
        )
    else:
        what_if_status = f"Needs {_fmt_score(needed_final)} / {_fmt_max(final_max)}"
        min_final_marks = needed_final
        min_final_pct = round((needed_final / final_max) * 100, 1) if final_max > 0 else 0.0
        what_if_message = (
            f"Needs at least {_fmt_score(needed_final)} / {_fmt_max(final_max)} ({min_final_pct}%) in Final-Term "
            f"to reach {target_overall_pct:.0f}% of total plan marks ({_fmt_score(target_marks)} marks)."
        )

    what_if = {
        "status": what_if_status,
        "result": "Already safe" if total_obtained >= target_marks else ("Not reachable" if (final_max <= 0 or needed_final > final_max) else "Achievable"),
        "target_percentage": target_overall_pct,
        "target_marks": target_marks,
        "total_obtained": total_obtained,
        "total_plan_max": total_plan_max,
        "final_max_marks": final_max,
        "min_final_marks_needed": min_final_marks,
        "min_final_percentage_needed": min_final_pct,
        "message": what_if_message,
        "is_estimate": True,
        "advisory_label": "Estimate only · Advisory only",
    }

    return {
        "name": student.name,
        "code": student.student_code,
        "attendance_pct": att_pct,
        "average_marks_pct": avg,
        "overall_score": overall_score,
        "total_obtained": total_obtained,
        "total_assessed_max": total_assessed_max,
        "total_plan_max": total_plan_max,
        "percentage_so_far": percentage_so_far,
        "assessments": assessments,
        "components": components,
        "level": level,
        "status": level,
        "danger_zones": active_danger_zones,
        "danger_badges": danger_badges,
        "zones": zones,
        "reasons": reasons,
        "what_if": what_if,
    }

def compute_warnings(db: Session, course_id: int,
                     attendance_threshold: float = 60.0,
                     marks_threshold: float = 40.0,
                     repeated_low_count: int = 2):
    enrolled = db.query(m.Enrollment).filter_by(course_id=course_id).all()
    results = []
    for e in enrolled:
        detail = compute_student_detail(db, course_id, e.student, attendance_threshold, marks_threshold)
        results.append({
            "student_id": e.student.id,
            "student_code": detail["code"],
            "name": detail["name"],
            "attendance_pct": detail["attendance_pct"],
            "average_marks_pct": detail["average_marks_pct"],
            "overall_score": detail["overall_score"],
            "total_obtained": detail["total_obtained"],
            "total_assessed_max": detail["total_assessed_max"],
            "total_plan_max": detail["total_plan_max"],
            "percentage_so_far": detail["percentage_so_far"],
            "level": detail["level"],
            "status": detail["status"],
            "danger_zones": detail["danger_zones"],
            "danger_badges": detail["danger_badges"],
            "zones": detail["zones"],
            "reasons": detail["reasons"],
            "components": detail["components"],
            "what_if": detail["what_if"],
        })

    order = {"critical": 0, "warning": 1, "safe": 2, "ok": 2}
    results.sort(key=lambda r: (order.get(r["level"], 2), r["name"]))
    return results
