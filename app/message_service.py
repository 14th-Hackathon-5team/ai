from datetime import date

from app.models import UserProfile


PART_TIME_PLANNED_STATUSES = {
    "SEARCHING",
    "LOOKING",
    "PLANNED",
    "JOB_SEEKING",
    "WILL_WORK",
}

PART_TIME_WORKING_STATUSES = {
    "WORKING",
    "IN_PROGRESS",
}


def format_korean_date(value: date) -> str:
    return (
        f"{value.year}년 "
        f"{value.month}월 "
        f"{value.day}일"
    )


def normalize_visa(visa_type: str) -> str:
    return (
        visa_type.upper()
        .replace("-", "")
        .replace("_", "")
        .strip()
    )


def format_visa(visa_type: str) -> str:
    normalized = normalize_visa(visa_type)

    labels = {
        "D2": "D-2",
        "D4": "D-4",
    }

    return labels.get(
        normalized,
        visa_type,
    )


def build_registration_reason(
    days_left: int,
) -> str:
    if days_left < 0:
        return (
            "외국인등록 기한이 "
            f"{-days_left}일 지났습니다. "
            "등록 상태와 필요한 절차를 "
            "가능한 빨리 확인해 주세요."
        )

    if days_left == 0:
        return (
            "외국인등록 기한이 오늘까지입니다. "
            "기한 내 등록 가능 여부를 바로 확인해 주세요."
        )

    return (
        "외국인등록이 아직 완료되지 않았습니다. "
        f"등록 기한까지 약 {days_left}일 남아 있으므로 "
        "기한 내 신청을 준비해 주세요."
    )


def build_stay_extension_reason(
    days_left: int,
) -> str:
    if days_left < 0:
        return (
            "프로필에 등록된 체류기간 만료일이 "
            f"{-days_left}일 지났습니다. "
            "현재 체류 상태와 필요한 절차를 "
            "바로 확인해 주세요."
        )

    if days_left == 0:
        return (
            "체류기간 만료일이 오늘입니다. "
            "계속 체류할 예정이라면 "
            "연장 가능 여부를 바로 확인해 주세요."
        )

    return (
        f"체류기간 만료일까지 {days_left}일 남았습니다. "
        "계속 체류할 예정이라면 연장에 필요한 "
        "절차와 서류를 확인해 주세요."
    )


def build_part_time_reason(
    visa_type: str,
    status: str | None,
    has_permit: bool | None,
    days_left: int | None,
) -> str:
    visa = format_visa(visa_type)

    normalized_status = (
        status.upper()
        if status
        else ""
    )

    if normalized_status in PART_TIME_WORKING_STATUSES:
        if has_permit is False:
            return (
                f"현재 {visa} 체류자격으로 "
                "아르바이트 중이며 허가가 완료되지 않은 "
                "상태로 등록되어 있습니다. "
                "근무 가능 여부를 바로 확인해 주세요."
            )

        return (
            f"현재 {visa} 체류자격으로 "
            "아르바이트 중인 것으로 등록되어 있지만 "
            "허가 완료 여부는 확인되지 않았습니다. "
            "필요한 허가 상태를 확인해 주세요."
        )

    if days_left is not None:
        if days_left < 0:
            return (
                f"현재 {visa} 체류자격이며 "
                "프로필에 등록된 아르바이트 시작일이 "
                f"{-days_left}일 지났습니다. "
                "근무 전 허가가 완료되었는지 확인해 주세요."
            )

        if days_left == 0:
            return (
                f"현재 {visa} 체류자격이며 "
                "아르바이트 시작 예정일이 오늘입니다. "
                "근무를 시작하기 전에 "
                "필요한 허가를 확인해 주세요."
            )

        return (
            f"현재 {visa} 체류자격으로 "
            "아르바이트를 계획하고 있습니다. "
            f"시작 예정일까지 {days_left}일 남았으므로 "
            "근무 전에 필요한 허가를 확인해 주세요."
        )

    return (
        f"현재 {visa} 체류자격으로 "
        "아르바이트를 계획하고 있습니다. "
        "시작일은 등록되지 않았으므로 "
        "근무 전에 필요한 허가를 준비해 주세요."
    )


def build_university_reason(
    current_topik: int,
    required_topik: int | None,
    start: date,
    end: date,
    today: date,
) -> str:
    messages = []

    if required_topik is not None:
        messages.append(
            f"현재 TOPIK {current_topik}급으로 "
            "등록되어 있어 해당 대학의 "
            f"TOPIK {required_topik}급 이상 "
            "어학 조건에 부합합니다."
        )
    else:
        messages.append(
            "프로필 정보와 대학의 지원 일정을 "
            "기준으로 확인할 수 있는 대학입니다."
        )

    if start <= today <= end:
        days_until_deadline = (
            end - today
        ).days

        if days_until_deadline == 0:
            messages.append(
                "원서접수 마감일이 오늘이므로 "
                "지원 여부와 제출 상태를 바로 확인해 주세요."
            )
        else:
            messages.append(
                "현재 원서접수 기간이며 "
                f"마감일까지 {days_until_deadline}일 "
                "남았습니다. 필요한 서류와 "
                "제출 일정을 확인해 주세요."
            )

    else:
        days_until_start = (
            start - today
        ).days
        formatted_start = format_korean_date(
            start
        )

        if days_until_start > 21:
            messages.append(
                f"원서접수까지 {days_until_start}일 "
                "남아 있어 미리 참고할 수 있습니다."
            )
        else:
            messages.append(
                f"원서접수는 {days_until_start}일 후인 "
                f"{formatted_start}에 시작됩니다. "
                "필요한 서류를 미리 확인해 주세요."
            )

    return " ".join(messages)


def build_summary(
    user: UserProfile,
    today: date,
) -> str:
    messages = []

    visa = format_visa(user.visaType)
    user_status = user.userStatus.upper()

    if user_status == "BEFORE_ENTRY":
        messages.append(
            f"현재 {visa} 체류자격으로 "
            "한국 입국을 준비하고 있습니다."
        )
    else:
        messages.append(
            f"현재 {visa} 체류자격으로 "
            "한국에서 유학 중입니다."
        )

    if (
        user_status != "BEFORE_ENTRY"
        and not user.hasAlienRegistration
    ):
        days_since_entry = (
            today - user.entryDate
        ).days
        days_left = 90 - days_since_entry

        if days_left >= 0:
            messages.append(
                "외국인등록이 아직 완료되지 않았으며 "
                f"등록 기한까지 약 {days_left}일 남았습니다."
            )
        else:
            messages.append(
                "프로필 기준으로 외국인등록 기한이 "
                f"{-days_left}일 지난 상태입니다."
            )

    if user.stayExpirationDate:
        expiration = format_korean_date(
            user.stayExpirationDate
        )

        messages.append(
            "프로필에 등록된 체류기간은 "
            f"{expiration}까지입니다."
        )

    part_time_status = (
        user.partTimeStatus.upper()
        if user.partTimeStatus
        else ""
    )

    if part_time_status in PART_TIME_PLANNED_STATUSES:
        if user.hasPartTimePermit is not True:
            messages.append(
                "현재 아르바이트를 계획하고 있어 "
                "근무 전에 관련 허가 확인이 필요합니다."
            )

    elif part_time_status in PART_TIME_WORKING_STATUSES:
        if user.hasPartTimePermit is False:
            messages.append(
                "현재 아르바이트 중이며 허가가 완료되지 않은 "
                "상태로 등록되어 있어 즉시 확인이 필요합니다."
            )

        elif user.hasPartTimePermit is None:
            messages.append(
                "현재 아르바이트 중이며 허가 완료 여부가 "
                "등록되지 않아 확인이 필요합니다."
            )

    topik_level = "".join(
        character
        for character in user.currentTopikLevel
        if character.isdigit()
    )

    if topik_level:
        messages.append(
            f"현재 TOPIK {topik_level}급으로 "
            "등록되어 있습니다."
        )

    return " ".join(messages)