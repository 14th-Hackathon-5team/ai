import json
import re
from datetime import date
from pathlib import Path

from app.models import UserProfile


BASE_DIR = Path(__file__).resolve().parent.parent
UNIV_PATH = BASE_DIR / "data" / "univ_info.json"

UNIVERSITY_HIGH_DAYS = 7
UNIVERSITY_MEDIUM_DAYS = 21


with open(UNIV_PATH, "r", encoding="utf-8") as f:
    UNIV_DATA = json.load(f)


def get_topik_level(level: str) -> int:
    match = re.search(r"([1-6])", level)

    if match:
        return int(match.group(1))

    return 0


def get_required_topik(language: str):
    match = re.search(
        r"TOPIK\s*([1-6])\s*급",
        language,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return None


def can_recommend_university(
    user: UserProfile,
) -> bool:
    allowed_status = {
        "BEFORE_ENTRY",
        "LANGUAGE_STUDENT",
    }

    return user.userStatus.upper() in allowed_status


def get_university_priority(
    today: date,
    start: date,
    end: date,
) -> str:
    if today > end:
        return "EXPIRED"

    if start <= today <= end:
        days_until_deadline = (end - today).days

        if days_until_deadline <= UNIVERSITY_HIGH_DAYS:
            return "HIGH"

        if days_until_deadline <= UNIVERSITY_MEDIUM_DAYS:
            return "MEDIUM"

        return "LOW"

    days_until_start = (start - today).days

    if days_until_start <= UNIVERSITY_HIGH_DAYS:
        return "HIGH"

    if days_until_start <= UNIVERSITY_MEDIUM_DAYS:
        return "MEDIUM"

    return "LOW"


def make_result(
    university: dict,
    score: int,
    priority: str,
    reason: str,
):
    eligibility = university.get(
        "admission_eligibility",
        {},
    )

    return {
        "type": "UNIVERSITY",
        "title": university.get("schoolName"),
        "priority": priority,
        "schoolName": university.get("schoolName"),
        "region": university.get("region"),
        "universityType": university.get(
            "university_type"
        ),
        "matchScore": score,
        "reason": reason,
        "applicationSchedule": university.get(
            "application_schedule"
        ),
        "documentSubmissionSchedule": university.get(
            "document_submission_schedule"
        ),
        "interview": university.get("interview"),
        "finalResultDate": university.get(
            "final_result_date"
        ),
        "nationalityRequirement": eligibility.get(
            "nationality"
        ),
        "academicRequirement": eligibility.get(
            "academic"
        ),
        "languageRequirement": eligibility.get(
            "language"
        ),
        "documents": university.get("documents"),
        "evaluationRatio": university.get(
            "evaluation_ratio"
        ),
        "detail": university,
    }


def recommend_universities(
    user: UserProfile,
    limit: int = 5,
):
    if not can_recommend_university(user):
        return []

    recommendations = []
    today = date.today()

    current_topik = get_topik_level(
        user.currentTopikLevel
    )

    for university in UNIV_DATA:
        eligibility = university.get(
            "admission_eligibility",
            {},
        )

        language = eligibility.get(
            "language",
            "",
        )

        required_topik = get_required_topik(
            language
        )

        if (
            required_topik is not None
            and current_topik < required_topik
        ):
            continue

        application = university.get(
            "application_schedule",
            {},
        )

        start_date = application.get("start")
        end_date = application.get("end")

        if not start_date or not end_date:
            continue

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        priority = get_university_priority(
            today=today,
            start=start,
            end=end,
        )

        if priority == "EXPIRED":
            continue

        score = 0
        reasons = []

        if required_topik is not None:
            score += 50
            reasons.append(
                f"현재 TOPIK {current_topik}급으로 "
                f"TOPIK {required_topik}급 이상 조건을 "
                "충족합니다."
            )

        if start <= today <= end:
            days_until_deadline = (
                end - today
            ).days

            score += 30
            reasons.append(
                "현재 원서접수 기간이며 "
                f"마감일까지 {days_until_deadline}일 "
                "남았습니다."
            )

        else:
            days_until_start = (
                start - today
            ).days

            if (
                days_until_start
                <= UNIVERSITY_MEDIUM_DAYS
            ):
                score += 20
            else:
                score += 10

            reasons.append(
                f"원서접수가 {days_until_start}일 후인 "
                f"{start_date}에 시작합니다."
            )

        recommendations.append(
            make_result(
                university=university,
                score=score,
                priority=priority,
                reason=" ".join(reasons),
            )
        )

    priority_order = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
    }

    recommendations.sort(
        key=lambda item: (
            priority_order.get(
                item.get("priority"),
                3,
            ),
            -item.get("matchScore", 0),
        )
    )

    return recommendations[:limit]