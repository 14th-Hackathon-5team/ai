import json
from datetime import date
from pathlib import Path

from app.message_service import (
    build_part_time_reason,
    build_registration_reason,
    build_stay_extension_reason,
    is_english_language,
    normalize_visa,
)
from app.models import UserProfile


BASE_DIR = Path(__file__).resolve().parent.parent
LAW_PATH = BASE_DIR / "data" / "law_info.json"

LEGAL_HIGH_DAYS = 14
LEGAL_MEDIUM_DAYS = 60

PART_TIME_HIGH_DAYS = 14
PART_TIME_MEDIUM_DAYS = 60

LAW_CATEGORY_BY_TITLE = {
    "외국인 등록": "ENTRY",
    "체류기간 만료/연장": "VISA",
    "유학생 아르바이트 허가": "PART_TIME",
    "유학생 비자 종류(D-2)": "VISA",
    "유학생 비자 종류(D-4)": "VISA",
}

LAW_TITLE_EN = {
    "외국인 등록": "Alien Registration",
    "체류기간 만료/연장": "Stay Period Expiration/Extension",
    "유학생 아르바이트 허가": "Part-Time Work Permit for International Students",
    "유학생 비자 종류(D-2)": "Student Visa Type (D-2)",
    "유학생 비자 종류(D-4)": "Student Visa Type (D-4)",
}

LAW_DETAIL_EN_BY_TITLE = {
    "외국인 등록": {
        "title": "Alien Registration",
        "target": "Foreign nationals who intend to stay in the Republic of Korea for more than 90 days from the date of entry.",
        "situation": "When a foreign national enters Korea and intends to stay for more than 90 days.",
        "action": "Register as a foreign resident with the head of the local immigration office that has jurisdiction over the place of stay.",
        "deadline": "Within 90 days from the date of entry. If the person receives status of stay and will stay for more than 90 days from that date, registration must be completed when the status is granted. If the person receives permission to change status and will stay for more than 90 days from the date of entry, registration must be completed when the change is permitted.",
        "penalty": "Failure to register may result in imprisonment for up to one year or a fine of up to 10 million KRW.",
        "details": "Certain people, such as staff and family members of foreign diplomatic missions or international organizations, people and family members who enjoy privileges and immunities similar to diplomats or consuls under intergovernmental agreements, and people invited by the Korean government, may be exempt from registration as prescribed by Ministry of Justice rules. After registration, an alien registration number is issued. The Immigration Act text does not specify the exact required documents.",
        "trigger": "If the profile shows the entry date, planned stay period, and alien registration status, and the user plans to stay for more than 90 days after entry but has not completed alien registration, the service provides proactive guidance.",
        "sourceName": "Korean Law Information Center",
        "lawName": "Immigration Act",
        "article": "Article 31, Article 95 Subparagraph 7",
    },
    "체류기간 만료/연장": {
        "title": "Stay Period Expiration/Extension",
        "target": "Foreign nationals who wish to continue staying in the Republic of Korea beyond the permitted period of stay.",
        "situation": "When the current permitted stay period is about to end but the person wishes to continue staying in Korea.",
        "action": "Obtain permission to extend the period of stay from the Minister of Justice.",
        "deadline": "Before the current permitted stay period ends.",
        "penalty": "Continuing to stay beyond the permitted period without extension permission may result in imprisonment for up to three years or a fine of up to 30 million KRW.",
        "details": "The procedure for stay period extension is prescribed by Presidential Decree, and the review criteria are prescribed by Ministry of Justice rules. The Immigration Act text does not specify the exact required documents.",
        "trigger": "If the stay expiration date saved in the profile is approaching and the user plans to continue staying but extension permission is not completed, the service provides proactive guidance.",
        "sourceName": "Korean Law Information Center",
        "lawName": "Immigration Act",
        "article": "Article 25, Article 94 Subparagraph 17",
    },
    "유학생 아르바이트 허가": {
        "title": "Part-Time Work Permit for International Students",
        "target": "International students staying in Korea with D-2 student status or D-4 general training status who want to work part-time or engage in activities outside their current status of stay.",
        "situation": "When a student with D-2 or D-4 status wants to start part-time work while continuing study or training.",
        "action": "Apply for and receive permission to engage in activities outside the current status of stay before starting part-time work.",
        "deadline": "Permission must be obtained before starting part-time work or any other activity outside the current status. HiKorea visit reservations can be made within the stay period up to one day before the intended visit date, and the activity cannot be performed before permission is granted.",
        "penalty": "Engaging in activities under another status of stay without permission may result in imprisonment for up to three years or a fine of up to 30 million KRW under Article 94 Subparagraph 12 of the Immigration Act.",
        "details": "Common required documents under HiKorea guidance include the application form and passport or foreigner entry permit. Additional documents by status of stay must be checked in HiKorea's status-specific guidance manual. For in-person applications, make a visit reservation on HiKorea and visit the competent immigration office or branch office on the reserved date. Processing generally takes about three weeks to three months, and the fee for part-time work permission recognized by the Minister of Justice for D-2 or D-4 status holders is 20,000 KRW.",
        "trigger": "If a user with D-2 or D-4 status changes their part-time work status to job seeking, planned work, or working, or enters workplace, job type, or start date information, the service checks whether permission for activities outside the status of stay has been completed and provides guidance before work starts if permission is not confirmed.",
        "sourceName": "HiKorea, Korean Law Information Center",
        "lawName": "Immigration Act, Enforcement Rules of the Immigration Act",
        "article": "Immigration Act Article 20 and Article 94 Subparagraph 12; Enforcement Rules Article 29, Article 72 Subparagraph 2, Article 76 Paragraph 2, and Attached Table 5-2",
    },
    "유학생 비자 종류(D-2)": {
        "title": "Student Visa Type (D-2)",
        "target": "Foreign nationals who intend to receive regular education or conduct specific research at a junior college or higher education institution or academic research institution.",
        "situation": "When a person intends to stay in Korea for regular study at a junior college or higher institution or for research at an academic research institution.",
        "action": "Obtain D-2 student status and engage in education or research activities within the permitted status and stay period. A person already staying in Korea under another status must obtain permission to change status before beginning D-2 activities as the main activity.",
        "deadline": "Before starting D-2 study or research activities. The visa type itself has no separate reporting deadline, but a person already staying under another status must obtain permission to change status before beginning activities under another status.",
        "penalty": "The D-2 visa classification itself has no independent penalty. However, staying outside the permitted status or period, or engaging in another status activity without required change-of-status permission, may result in punishment under Article 94 of the Immigration Act.",
        "details": "Under Attached Table 1-2 of the Enforcement Decree of the Immigration Act, D-2 student status is a long-term status for people who receive regular education or conduct specific research at junior colleges or higher education institutions or academic research institutions. Required documents for visa issuance must be checked under the Enforcement Rules and status-specific attached tables.",
        "trigger": "If the profile shows school type, degree or education program, research status, admission or research start date, and current status of stay, and the user appears to need D-2 status but D-2 acquisition or change is not confirmed, the service provides proactive guidance before the activity begins.",
        "sourceName": "Korean Law Information Center",
        "lawName": "Immigration Act, Enforcement Decree of the Immigration Act, Enforcement Rules of the Immigration Act",
        "article": "Immigration Act Articles 10, 10-2, 17, 24, and 94; Enforcement Decree Article 12 and Attached Table 1-2; Enforcement Rules Articles 9 and 76",
    },
    "유학생 비자 종류(D-4)": {
        "title": "Student Visa Type (D-4)",
        "target": "Foreign nationals who intend to receive education or training or engage in research activities at institutions, companies, or organizations that meet requirements set by the Minister of Justice, excluding people who fall under D-2 student status or D-3 industrial training status.",
        "situation": "When a person intends to stay in Korea for education, training, or research at an institution, company, or organization rather than a regular degree program under D-2.",
        "action": "Obtain D-4 general training status and engage in education, training, or research activities within the permitted status and stay period. A person already staying in Korea under another status must obtain permission to change status before beginning D-4 activities as the main activity.",
        "deadline": "Before starting D-4 education, training, or research activities. The visa type itself has no separate reporting deadline, but a person already staying under another status must obtain permission to change status before beginning activities under another status.",
        "penalty": "The D-4 visa classification itself has no independent penalty. However, staying outside the permitted status or period, or engaging in another status activity without required change-of-status permission, may result in punishment under Article 94 of the Immigration Act.",
        "details": "Under Attached Table 1-2 of the Enforcement Decree of the Immigration Act, D-4 general training status applies to people who receive education or training or engage in research activities at eligible institutions, companies, or organizations. Required documents for visa issuance must be checked under the Enforcement Rules and status-specific attached tables.",
        "trigger": "If the profile shows language training, non-degree education, training, research status, training institution type, training start date, and current status of stay, and the user appears to need D-4 status but D-4 acquisition or change is not confirmed, the service provides proactive guidance before the activity begins.",
        "sourceName": "Korean Law Information Center",
        "lawName": "Immigration Act, Enforcement Decree of the Immigration Act, Enforcement Rules of the Immigration Act",
        "article": "Immigration Act Articles 10, 10-2, 17, 24, and 94; Enforcement Decree Article 12 and Attached Table 1-2; Enforcement Rules Articles 9 and 76",
    },
}


with open(LAW_PATH, "r", encoding="utf-8") as file:
    LAW_DATA = json.load(file)


def find_law(title: str):
    for law in LAW_DATA:
        if law.get("title") == title:
            return law

    return None


def translate_law_title(
    title: str,
    language: str | None,
):
    if is_english_language(language):
        return LAW_TITLE_EN.get(title, title)

    return title


def build_law_detail(
    law: dict,
    category: str,
    language: str | None,
):
    title = law.get("title")

    if is_english_language(language):
        translated = LAW_DETAIL_EN_BY_TITLE.get(
            title,
            {},
        )

        detail = {
            **law,
            **translated,
            "category": category,
        }

        return detail

    return {
        **law,
        "category": category,
    }


def make_result(
    law: dict,
    priority: str,
    reason: str,
    language: str | None = "ko",
):
    title = law.get("title")

    category = LAW_CATEGORY_BY_TITLE.get(
        title,
        "LEGAL",
    )

    detail = build_law_detail(
        law=law,
        category=category,
        language=language,
    )

    return {
        "type": "LAW",
        "title": translate_law_title(
            title,
            language,
        ),
        "priority": priority,
        "reason": reason,
        "detail": detail,
    }


def get_legal_priority(
    days_left: int,
) -> str:
    if days_left <= LEGAL_HIGH_DAYS:
        return "HIGH"

    if days_left <= LEGAL_MEDIUM_DAYS:
        return "MEDIUM"

    return "LOW"


def get_part_time_priority(
    days_left: int,
) -> str:
    if days_left <= PART_TIME_HIGH_DAYS:
        return "HIGH"

    if days_left <= PART_TIME_MEDIUM_DAYS:
        return "MEDIUM"

    return "LOW"


def recommend_laws(
    user: UserProfile,
):
    recommendations = []

    today = date.today()
    visa = normalize_visa(user.visaType)
    language = getattr(user, "language", "ko")

    if (
        user.userStatus.upper() != "BEFORE_ENTRY"
        and not user.hasAlienRegistration
    ):
        law = find_law("외국인 등록")

        if law:
            days_since_entry = (
                today - user.entryDate
            ).days
            days_left = 90 - days_since_entry

            recommendations.append(
                make_result(
                    law=law,
                    priority=get_legal_priority(
                        days_left
                    ),
                    reason=build_registration_reason(
                        days_left,
                        language=language,
                    ),
                    language=language,
                )
            )

    if user.stayExpirationDate:
        days_left = (
            user.stayExpirationDate - today
        ).days

        if days_left <= LEGAL_MEDIUM_DAYS:
            law = find_law(
                "체류기간 만료/연장"
            )

            if law:
                recommendations.append(
                    make_result(
                        law=law,
                        priority=get_legal_priority(
                            days_left
                        ),
                        reason=(
                            build_stay_extension_reason(
                                days_left,
                                language=language,
                            )
                        ),
                        language=language,
                    )
                )

    part_time_status = (
        user.partTimeStatus.upper()
        if user.partTimeStatus
        else ""
    )

    target_statuses = {
        "SEARCHING",
        "LOOKING",
        "PLANNED",
        "WORKING",
        "JOB_SEEKING",
        "WILL_WORK",
        "IN_PROGRESS",
    }

    if (
        visa in {"D2", "D4"}
        and part_time_status in target_statuses
        and user.hasPartTimePermit is not True
    ):
        law = find_law(
            "유학생 아르바이트 허가"
        )

        if law:
            days_left = None

            if user.partTimeStartDate:
                days_left = (
                    user.partTimeStartDate - today
                ).days

            if part_time_status in {
                "WORKING",
                "IN_PROGRESS",
            }:
                priority = "HIGH"

            elif days_left is not None:
                priority = get_part_time_priority(
                    days_left
                )

            else:
                priority = "MEDIUM"

            recommendations.append(
                make_result(
                    law=law,
                    priority=priority,
                    reason=build_part_time_reason(
                        visa_type=user.visaType,
                        status=user.partTimeStatus,
                        has_permit=(
                            user.hasPartTimePermit
                        ),
                        days_left=days_left,
                        language=language,
                    ),
                    language=language,
                )
            )

    if visa == "D2":
        law = find_law(
            "유학생 비자 종류(D-2)"
        )

        if law:
            reason = (
                "Your profile currently lists D-2 as your status of stay."
                if is_english_language(language)
                else (
                    "현재 프로필의 체류자격이 "
                    "D-2로 등록되어 있습니다."
                )
            )

            recommendations.append(
                make_result(
                    law=law,
                    priority="LOW",
                    reason=reason,
                    language=language,
                )
            )

    elif visa == "D4":
        law = find_law(
            "유학생 비자 종류(D-4)"
        )

        if law:
            reason = (
                "Your profile currently lists D-4 as your status of stay."
                if is_english_language(language)
                else (
                    "현재 프로필의 체류자격이 "
                    "D-4로 등록되어 있습니다."
                )
            )

            recommendations.append(
                make_result(
                    law=law,
                    priority="LOW",
                    reason=reason,
                    language=language,
                )
            )

    return recommendations
