import json
from datetime import date
from pathlib import Path

from app.models import UserProfile


BASE_DIR = Path(__file__).resolve().parent.parent
LAW_PATH = BASE_DIR / "data" / "law_info.json"

with open(LAW_PATH, "r", encoding="utf-8") as f:
    LAW_DATA = json.load(f)


def normalize_visa(visa_type: str) -> str:
    return visa_type.upper().replace("-", "").replace("_", "").strip()


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


def recommend_laws(user: UserProfile):
    recommendations = []

    today = date.today()
    visa = normalize_visa(user.visaType)

    if (
        user.userStatus != "BEFORE_ENTRY"
        and not user.hasAlienRegistration
    ):
        law = find_law("외국인 등록")

        if law:
            if user.entryDate:
                days_since_entry = (today - user.entryDate).days

                if days_since_entry >= 80:
                    priority = "HIGH"
                elif days_since_entry >= 60:
                    priority = "MEDIUM"
                else:
                    priority = "LOW"

                reason = (
                    f"현재 외국인등록이 완료되지 않았고 "
                    f"입국일로부터 약 {days_since_entry}일이 지났습니다."
                )

            else:
                priority = "MEDIUM"
                reason = "현재 외국인등록이 완료되지 않은 상태입니다."

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

        if days_left <= 60:
            law = find_law("체류기간 만료/연장")

            if law:
                if days_left < 0:
                    priority = "HIGH"
                    reason = (
                        f"프로필에 등록된 체류기간 만료일이 "
                        f"{-days_left}일 지났습니다."
                    )

                elif days_left <= 30:
                    priority = "HIGH"
                    reason = (
                        f"현재 체류기간 만료일까지 "
                        f"{days_left}일 남아 있습니다."
                    )

                else:
                    priority = "MEDIUM"
                    reason = (
                        f"현재 체류기간 만료일까지 "
                        f"{days_left}일 남아 있습니다."
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

    active_part_time_status = {
        "LOOKING",
        "PLANNED",
        "WORKING",
        "JOB_SEEKING",
        "WILL_WORK",
        "IN_PROGRESS",
    }

    if (
        visa in {"D2", "D4"}
        and part_time_status in active_part_time_status
    ):
        law = find_law("유학생 아르바이트 허가")

        if law:
            recommendations.append(
                make_result(
                    law=law,
                    priority="HIGH",
                    reason=(
                        f"현재 {user.visaType} 체류자격이며 "
                        f"아르바이트 상태가 "
                        f"{user.partTimeStatus}로 등록되어 있습니다."
                    ),
                )
            )

    if visa == "D2":
        law = find_law("유학생 비자 종류(D-2)")

        if law:
            recommendations.append(
                make_result(
                    law=law,
                    priority="LOW",
                    reason="현재 프로필의 체류자격이 D-2입니다.",
                )
            )

    elif visa == "D4":
        law = find_law("유학생 비자 종류(D-4)")

        if law:
            recommendations.append(
                make_result(
                    law=law,
                    priority="LOW",
                    reason="현재 프로필의 체류자격이 D-4입니다.",
                )
            )

    return recommendations