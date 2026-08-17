import json
from datetime import date
from pathlib import Path

from app.message_service import (
    build_part_time_reason,
    build_registration_reason,
    build_stay_extension_reason,
    normalize_visa,
)
from app.models import UserProfile


BASE_DIR = Path(__file__).resolve().parent.parent
LAW_PATH = BASE_DIR / "data" / "law_info.json"

LEGAL_HIGH_DAYS = 14
LEGAL_MEDIUM_DAYS = 60

PART_TIME_HIGH_DAYS = 14
PART_TIME_MEDIUM_DAYS = 60


with open(LAW_PATH, "r", encoding="utf-8") as file:
    LAW_DATA = json.load(file)


def find_law(title: str):
    for law in LAW_DATA:
        if law.get("title") == title:
            return law

    return None


def make_result(
    law: dict,
    priority: str,
    reason: str,
):
    return {
        "type": "LAW",
        "title": law.get("title"),
        "priority": priority,
        "reason": reason,
        "detail": law,
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
                        days_left
                    ),
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
                                days_left
                            )
                        ),
                    )
                )

    part_time_status = (
        user.partTimeStatus.upper()
        if user.partTimeStatus
        else ""
    )

    target_statuses = {
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
                    ),
                )
            )

    if visa == "D2":
        law = find_law(
            "유학생 비자 종류(D-2)"
        )

        if law:
            recommendations.append(
                make_result(
                    law=law,
                    priority="LOW",
                    reason=(
                        "현재 프로필의 체류자격이 "
                        "D-2로 등록되어 있습니다."
                    ),
                )
            )

    elif visa == "D4":
        law = find_law(
            "유학생 비자 종류(D-4)"
        )

        if law:
            recommendations.append(
                make_result(
                    law=law,
                    priority="LOW",
                    reason=(
                        "현재 프로필의 체류자격이 "
                        "D-4로 등록되어 있습니다."
                    ),
                )
            )

    return recommendations