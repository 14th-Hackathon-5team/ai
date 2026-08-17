import json
from datetime import date
from pathlib import Path

from app.models import UserProfile


BASE_DIR = Path(__file__).resolve().parent.parent
LAW_PATH = BASE_DIR / "data" / "law_info.json"

LEGAL_HIGH_DAYS = 14
LEGAL_MEDIUM_DAYS = 60

PART_TIME_HIGH_DAYS = 14
PART_TIME_MEDIUM_DAYS = 60


with open(LAW_PATH, "r", encoding="utf-8") as f:
    LAW_DATA = json.load(f)


def normalize_visa(visa_type: str) -> str:
    return (
        visa_type.upper()
        .replace("-", "")
        .replace("_", "")
        .strip()
    )


def format_visa(visa_type: str) -> str:
    normalized = normalize_visa(visa_type)

    if normalized == "D2":
        return "D-2"

    if normalized == "D4":
        return "D-4"

    return visa_type


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


def get_legal_priority(days_left: int) -> str:
    if days_left <= LEGAL_HIGH_DAYS:
        return "HIGH"

    if days_left <= LEGAL_MEDIUM_DAYS:
        return "MEDIUM"

    return "LOW"


def get_part_time_priority(days_left: int) -> str:
    if days_left <= PART_TIME_HIGH_DAYS:
        return "HIGH"

    if days_left <= PART_TIME_MEDIUM_DAYS:
        return "MEDIUM"

    return "LOW"


def recommend_laws(user: UserProfile):
    recommendations = []

    today = date.today()
    visa = normalize_visa(user.visaType)
    display_visa = format_visa(user.visaType)

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

            priority = get_legal_priority(days_left)

            if days_left < 0:
                reason = (
                    "외국인등록이 완료되지 않았으며 "
                    f"90일 등록 기한이 {-days_left}일 지났습니다."
                )

            elif days_left == 0:
                reason = (
                    "외국인등록이 완료되지 않았으며 "
                    "90일 등록 기한이 오늘까지입니다."
                )

            else:
                reason = (
                    "외국인등록이 완료되지 않았으며 "
                    f"90일 등록 기한까지 약 {days_left}일 남았습니다."
                )

            recommendations.append(
                make_result(
                    law=law,
                    priority=priority,
                    reason=reason,
                )
            )

    if user.stayExpirationDate:
        days_left = (
            user.stayExpirationDate - today
        ).days

        if days_left <= LEGAL_MEDIUM_DAYS:
            law = find_law("체류기간 만료/연장")

            if law:
                priority = get_legal_priority(days_left)

                if days_left < 0:
                    reason = (
                        "프로필에 등록된 체류기간이 "
                        f"{-days_left}일 전에 만료되었습니다."
                    )

                elif days_left == 0:
                    reason = "체류기간 만료일이 오늘입니다."

                else:
                    reason = (
                        "현재 체류기간 만료일까지 "
                        f"{days_left}일 남았습니다."
                    )

                recommendations.append(
                    make_result(
                        law=law,
                        priority=priority,
                        reason=reason,
                    )
                )

    part_time_status = (
        user.partTimeStatus.upper()
        if user.partTimeStatus
        else ""
    )

    part_time_target_statuses = {
        "LOOKING",
        "PLANNED",
        "WORKING",
        "JOB_SEEKING",
        "WILL_WORK",
        "IN_PROGRESS",
    }

    if (
        visa in {"D2", "D4"}
        and part_time_status in part_time_target_statuses
        and user.hasPartTimePermit is not True
    ):
        law = find_law("유학생 아르바이트 허가")

        if law:
            if part_time_status in {
                "WORKING",
                "IN_PROGRESS",
            }:
                priority = "HIGH"
                reason = (
                    f"현재 {display_visa} 체류자격으로 "
                    "아르바이트 중이지만 허가 완료 여부가 "
                    "확인되지 않아 즉시 확인이 필요합니다."
                )

            elif user.partTimeStartDate:
                days_left = (
                    user.partTimeStartDate - today
                ).days
                priority = get_part_time_priority(
                    days_left
                )

                if days_left < 0:
                    reason = (
                        f"현재 {display_visa} 체류자격이며 "
                        "아르바이트 시작 예정일이 "
                        f"{-days_left}일 지났습니다. "
                        "허가 여부를 즉시 확인해야 합니다."
                    )

                elif days_left == 0:
                    reason = (
                        f"현재 {display_visa} 체류자격이며 "
                        "아르바이트 시작 예정일이 오늘입니다. "
                        "근무 전에 허가 여부를 확인해야 합니다."
                    )

                else:
                    reason = (
                        f"현재 {display_visa} 체류자격이며 "
                        "아르바이트 시작 예정일까지 "
                        f"{days_left}일 남았습니다. "
                        "근무 전에 허가를 준비해야 합니다."
                    )

            else:
                priority = "MEDIUM"
                reason = (
                    f"현재 {display_visa} 체류자격이며 "
                    f"아르바이트 상태가 "
                    f"{user.partTimeStatus}로 등록되어 있습니다. "
                    "시작일은 등록되지 않았으므로 "
                    "근무 전에 허가를 준비해야 합니다."
                )

            recommendations.append(
                make_result(
                    law=law,
                    priority=priority,
                    reason=reason,
                )
            )

    if visa == "D2":
        law = find_law("유학생 비자 종류(D-2)")

        if law:
            recommendations.append(
                make_result(
                    law=law,
                    priority="LOW",
                    reason="현재 체류자격이 D-2입니다.",
                )
            )

    elif visa == "D4":
        law = find_law("유학생 비자 종류(D-4)")

        if law:
            recommendations.append(
                make_result(
                    law=law,
                    priority="LOW",
                    reason="현재 체류자격이 D-4입니다.",
                )
            )

    return recommendations