import json
import re
from datetime import date
from pathlib import Path

from app.message_service import (
    build_university_reason,
    is_english_language,
)
from app.models import UserProfile


BASE_DIR = Path(__file__).resolve().parent.parent
UNIV_PATH = BASE_DIR / "data" / "univ_info.json"

UNIVERSITY_HIGH_DAYS = 7
UNIVERSITY_MEDIUM_DAYS = 21

SCHOOL_NAME_EN = {
    "한빛국제대학교": "Hanbit International University",
    "미래글로벌대학교": "Mirae Global University",
    "새롬대학교": "Saerom University",
    "청람과학대학교": "Cheongram Science University",
}

TEXT_EN = {
    "부산광역시": "Busan",
    "대전광역시": "Daejeon",
    "광주광역시": "Gwangju",
    "대구광역시": "Daegu",
    "서울특별시": "Seoul",
    "인천광역시": "Incheon",
    "사립": "Private",
    "국립": "National",
    "공립": "Public",
    "온라인 화상 면접": "Online video interview",
    "온라인 개별 면접": "Online individual interview",
    "입학지원서": "Application form",
    "온라인 입학지원서": "Online application form",
    "고등학교 졸업증명서": "High school graduation certificate",
    "졸업증명서": "Graduation certificate",
    "고등학교 전 학년 성적증명서": "High school transcript for all years",
    "고등학교 성적증명서": "High school transcript",
    "지원자와 부모의 여권 사본": "Copies of the applicant's and parents' passports",
    "지원자 및 부모 여권 사본": "Copies of the applicant's and parents' passports",
    "지원자 여권 사본": "Copy of the applicant's passport",
    "부모 여권 사본": "Copies of parents' passports",
    "출생증명서 또는 가족관계증명서": "Birth certificate or family relationship certificate",
    "출생증명서": "Birth certificate",
    "가족관계 확인서류": "Family relationship verification documents",
    "TOPIK 또는 공인영어성적표": "TOPIK or official English proficiency score report",
    "TOPIK 또는 TOEFL 성적표": "TOPIK or TOEFL score report",
    "어학능력 증명서": "Language proficiency certificate",
    "자기소개서": "Personal statement",
    "학업계획서": "Study plan",
    "아포스티유 또는 영사확인 서류": "Apostille or consular confirmation documents",
    "학력인증서류": "Academic credential verification documents",
    "개인정보 제공 동의서": "Consent form for personal information provision",
    "지원자와 부모 모두 대한민국 국적이 아닌 외국인": "The applicant and both parents must be foreign nationals who do not hold Korean nationality.",
    "지원자와 부모 모두 외국 국적을 보유한 자": "The applicant and both parents must hold foreign nationality.",
    "부모와 지원자 모두 외국 국적을 보유한 외국인": "The applicant and both parents must be foreign nationals.",
    "국내외 고등학교 졸업자 또는 졸업예정자": "Graduates or expected graduates of a high school in Korea or abroad.",
    "고등학교 졸업 이상의 학력을 가진 자": "Applicants with a high school diploma or higher academic background.",
    "12년제 초중고 교육과정을 이수하고 고등학교를 졸업한 자": "Applicants who completed a 12-year elementary, middle, and high school curriculum and graduated from high school.",
    "TOPIK 3급 이상 또는 IELTS 5.5 이상": "TOPIK level 3 or higher, or IELTS 5.5 or higher.",
    "TOPIK 4급 이상 또는 TOEFL iBT 71점 이상": "TOPIK level 4 or higher, or TOEFL iBT 71 or higher.",
}


with open(UNIV_PATH, "r", encoding="utf-8") as file:
    UNIV_DATA = json.load(file)


def get_topik_level(level: str) -> int:
    match = re.search(r"([1-6])", level)

    if match:
        return int(match.group(1))

    return 0


def get_required_topik(
    language: str,
):
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
    allowed_statuses = {
        "BEFORE_ENTRY",
        "LANGUAGE_STUDENT",
    }

    return (
        user.userStatus.upper()
        in allowed_statuses
    )


def get_university_priority(
    today: date,
    start: date,
    end: date,
) -> str:
    if today > end:
        return "EXPIRED"

    if start <= today <= end:
        days_until_deadline = (
            end - today
        ).days

        if (
            days_until_deadline
            <= UNIVERSITY_HIGH_DAYS
        ):
            return "HIGH"

        if (
            days_until_deadline
            <= UNIVERSITY_MEDIUM_DAYS
        ):
            return "MEDIUM"

        return "LOW"

    days_until_start = (
        start - today
    ).days

    if (
        days_until_start
        <= UNIVERSITY_HIGH_DAYS
    ):
        return "HIGH"

    if (
        days_until_start
        <= UNIVERSITY_MEDIUM_DAYS
    ):
        return "MEDIUM"

    return "LOW"


def translate_text(
    value,
    language: str | None,
):
    if not is_english_language(language):
        return value

    if isinstance(value, dict):
        return {
            key: translate_text(
                child,
                language,
            )
            for key, child in value.items()
        }

    if isinstance(value, list):
        return [
            translate_text(item, language)
            for item in value
        ]

    if not isinstance(value, str):
        return value

    return TEXT_EN.get(value, value)


def translate_school_name(
    school_name: str | None,
    language: str | None,
):
    if not is_english_language(language):
        return school_name

    return SCHOOL_NAME_EN.get(
        school_name,
        school_name,
    )


def translate_university(
    university: dict,
    language: str | None,
):
    if not is_english_language(language):
        return university

    translated = translate_text(
        university,
        language,
    )

    translated["schoolName"] = translate_school_name(
        university.get("schoolName"),
        language,
    )

    return translated


def make_result(
    university: dict,
    score: int,
    priority: str,
    reason: str,
    language: str | None = "ko",
):
    translated_university = translate_university(
        university,
        language,
    )

    eligibility = (
        translated_university.get(
            "admission_eligibility"
        )
        or {}
    )

    detail = {
        **translated_university,
        "category": "ADMISSION",
    }

    return {
        "type": "UNIVERSITY",
        "title": translated_university.get(
            "schoolName"
        ),
        "priority": priority,
        "schoolName": translated_university.get(
            "schoolName"
        ),
        "region": translated_university.get("region"),
        "universityType": translated_university.get(
            "university_type"
        ),
        "matchScore": score,
        "reason": reason,
        "applicationSchedule": (
            translated_university.get(
                "application_schedule"
            )
        ),
        "documentSubmissionSchedule": (
            translated_university.get(
                "document_submission_schedule"
            )
        ),
        "interview": translated_university.get(
            "interview"
        ),
        "finalResultDate": translated_university.get(
            "final_result_date"
        ),
        "nationalityRequirement": (
            eligibility.get("nationality")
        ),
        "academicRequirement": (
            eligibility.get("academic")
        ),
        "languageRequirement": (
            eligibility.get("language")
        ),
        "documents": translated_university.get(
            "documents"
        ),
        "evaluationRatio": (
            translated_university.get(
                "evaluation_ratio"
            )
        ),
        "detail": detail,
    }


def recommend_universities(
    user: UserProfile,
    limit: int = 5,
):
    if not can_recommend_university(user):
        return []

    recommendations = []
    today = date.today()
    language = getattr(user, "language", "ko")

    current_topik = get_topik_level(
        user.currentTopikLevel
    )

    for university in UNIV_DATA:
        eligibility = (
            university.get(
                "admission_eligibility"
            )
            or {}
        )

        language_requirement = eligibility.get(
            "language",
            "",
        )

        required_topik = get_required_topik(
            language_requirement
        )

        if (
            required_topik is not None
            and current_topik < required_topik
        ):
            continue

        application = (
            university.get(
                "application_schedule"
            )
            or {}
        )

        start_date = application.get(
            "start"
        )
        end_date = application.get("end")

        if not start_date or not end_date:
            continue

        start = date.fromisoformat(
            start_date
        )
        end = date.fromisoformat(
            end_date
        )

        priority = get_university_priority(
            today=today,
            start=start,
            end=end,
        )

        if priority == "EXPIRED":
            continue

        score = 0

        if required_topik is not None:
            score += 50

        if start <= today <= end:
            score += 30
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

        reason = build_university_reason(
            current_topik=current_topik,
            required_topik=required_topik,
            start=start,
            end=end,
            today=today,
            language=language,
        )

        recommendations.append(
            make_result(
                university=university,
                score=score,
                priority=priority,
                reason=reason,
                language=language,
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
            -item.get(
                "matchScore",
                0,
            ),
        )
    )

    return recommendations[:limit]
