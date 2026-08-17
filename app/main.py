import json
import textwrap

from fastapi import FastAPI

from app.models import UserProfile
from app.recommender import recommend


app = FastAPI(
    title="AI Buddy API",
    version="1.0.0",
)


LINE_WIDTH = 60

PRIORITY_LABELS = {
    "HIGH": "긴급",
    "MEDIUM": "준비 필요",
    "LOW": "참고",
}

TYPE_LABELS = {
    "LAW": "법률·행정",
    "UNIVERSITY": "대학교",
}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.post("/recommend")
def create_recommendation(
    user: UserProfile,
):
    return recommend(user)


def print_wrapped(
    text: str,
    prefix: str = "",
):
    if not text:
        return

    wrapped_lines = textwrap.wrap(
        str(text),
        width=LINE_WIDTH,
        break_long_words=False,
        break_on_hyphens=False,
    )

    for index, line in enumerate(wrapped_lines):
        if index == 0:
            print(f"{prefix}{line}")
        else:
            print(
                f"{' ' * len(prefix)}{line}"
            )


def print_detail_item(
    label: str,
    value,
):
    if value is None or value == "":
        return

    print_wrapped(
        text=str(value),
        prefix=f"- {label}: ",
    )


def format_schedule(
    schedule: dict | None,
):
    if not isinstance(schedule, dict):
        return None

    start = schedule.get("start")
    end = schedule.get("end")

    if start and end:
        return f"{start} ~ {end}"

    if start:
        return f"{start}부터"

    if end:
        return f"{end}까지"

    return None


def print_law_detail(detail: dict):
    print_detail_item(
        "대상",
        detail.get("target"),
    )

    print_detail_item(
        "해야 할 일",
        detail.get("action"),
    )

    print_detail_item(
        "기한",
        detail.get("deadline"),
    )

    print_detail_item(
        "관련 법률",
        detail.get("lawName"),
    )

    print_detail_item(
        "관련 조항",
        detail.get("article"),
    )

    print_detail_item(
        "출처",
        detail.get("sourceName"),
    )

    penalty = detail.get("penalty")

    if penalty:
        print("\n주의")

        print_wrapped(
            text=penalty,
            prefix="- ",
        )


def print_university_detail(
    detail: dict,
):
    eligibility = (
        detail.get("admission_eligibility")
        or {}
    )

    print_detail_item(
        "지역",
        detail.get("region"),
    )

    print_detail_item(
        "대학 유형",
        detail.get("university_type"),
    )

    print_detail_item(
        "언어 조건",
        eligibility.get("language"),
    )

    print_detail_item(
        "학력 조건",
        eligibility.get("academic"),
    )

    print_detail_item(
        "원서접수",
        format_schedule(
            detail.get(
                "application_schedule"
            )
        ),
    )

    print_detail_item(
        "서류 제출",
        format_schedule(
            detail.get(
                "document_submission_schedule"
            )
        ),
    )

    interview = (
        detail.get("interview")
        or {}
    )

    if interview.get("yn"):
        interview_text = interview.get(
            "date",
        ) or "일정 확인 필요"

        interview_type = interview.get(
            "type",
        )

        if interview_type:
            interview_text = (
                f"{interview_text} "
                f"({interview_type})"
            )

        print_detail_item(
            "면접",
            interview_text,
        )

    else:
        print_detail_item(
            "면접",
            "없음",
        )

    print_detail_item(
        "최종 발표",
        detail.get("final_result_date"),
    )

    documents = (
        detail.get("documents")
        or []
    )

    if documents:
        print("\n주요 제출 서류")

        for document in documents:
            if not document:
                continue

            print_wrapped(
                text=str(document),
                prefix="- ",
            )


def print_recommendation(
    index: int,
    item: dict,
):
    priority = item.get(
        "priority",
        "LOW",
    )

    recommendation_type = item.get(
        "type",
        "UNKNOWN",
    )

    priority_label = PRIORITY_LABELS.get(
        priority,
        priority,
    )

    type_label = TYPE_LABELS.get(
        recommendation_type,
        recommendation_type,
    )

    title = (
        item.get("title")
        or "제목 없음"
    )

    print("\n" + "-" * LINE_WIDTH)

    print(
        f"[{index}] "
        f"[{priority_label} | {type_label}]"
    )

    print(f"\n{title}")

    reason = item.get("reason")

    if reason:
        print("\n추천 이유")

        print_wrapped(
            text=reason,
            prefix="- ",
        )

    detail = item.get("detail")

    if not isinstance(detail, dict):
        return

    print("\n상세 정보")

    if recommendation_type == "LAW":
        print_law_detail(detail)

    elif recommendation_type == "UNIVERSITY":
        print_university_detail(detail)


def print_result(result: dict):
    print("\n" + "=" * LINE_WIDTH)
    print("AI 맞춤 추천 결과")
    print("=" * LINE_WIDTH)

    print(
        f"\n사용자 ID: "
        f"{result.get('userId', '알 수 없음')}"
    )

    print("\n[상황 요약]")

    print_wrapped(
        result.get("summary")
        or "요약 정보가 없습니다."
    )

    recommendations = (
        result.get("recommendations")
        or []
    )

    if not recommendations:
        print(
            "\n현재 표시할 추천 정보가 없습니다."
        )

    else:
        for index, item in enumerate(
            recommendations,
            start=1,
        ):
            if not isinstance(item, dict):
                continue

            print_recommendation(
                index=index,
                item=item,
            )

    print("\n" + "=" * LINE_WIDTH)

    print(
        f"총 {len(recommendations)}개의 "
        "추천 정보가 생성되었습니다."
    )

    print("=" * LINE_WIDTH)


def main():
    with open(
        "user.json",
        "r",
        encoding="utf-8",
    ) as file:
        user_data = json.load(file)

    user = UserProfile(**user_data)

    result = recommend(user)

    with open(
        "result.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print_result(result)

    print("\nresult.json 생성 완료")


if __name__ == "__main__":
    main()
