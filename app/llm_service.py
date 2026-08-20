import json
import os
from functools import lru_cache

from dotenv import load_dotenv
from groq import Groq

from app.models import (
    RecommendationTrigger,
    UserProfile,
)


load_dotenv()


@lru_cache
def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY가 설정되지 않았습니다."
        )

    return Groq(api_key=api_key)


def parse_json_object(content: str):
    text = (content or "").strip()

    if text.startswith("```"):
        text = text.strip("`").strip()

        if text.startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError(
            "JSON 객체를 찾을 수 없습니다."
        )

    return json.loads(text[start:end + 1])


def select_optional_recommendations(
    user: UserProfile,
    trigger: RecommendationTrigger | None,
    required_recommendations: list,
    optional_recommendations: list,
    optional_limit: int,
):
    if (
        optional_limit <= 0
        or not optional_recommendations
    ):
        return []

    try:
        client = get_groq_client()
    except Exception as error:
        print("OPTIONAL RECOMMENDATION CLIENT ERROR:", error)
        return []

    user_data = user.model_dump(
        mode="json"
    )

    trigger_data = (
        trigger.model_dump(mode="json")
        if trigger
        else None
    )

    required_candidates = [
        {
            "type": item.get("type"),
            "title": item.get("title"),
            "priority": item.get(
                "priority"
            ),
            "category": (
                item.get("detail", {})
                .get("category")
            ),
        }
        for item in required_recommendations
    ]

    optional_candidates = [
        {
            "type": item.get("type"),
            "title": item.get("title"),
            "priority": item.get(
                "priority"
            ),
            "reason": item.get("reason"),
            "matchScore": item.get(
                "matchScore"
            ),
            "category": (
                item.get("detail", {})
                .get("category")
            ),
        }
        for item in optional_recommendations
    ]

    prompt = f"""
사용자 프로필:
{json.dumps(user_data, ensure_ascii=False, indent=2)}

Backend가 전달한 trigger:
{json.dumps(trigger_data, ensure_ascii=False, indent=2)}

이미 자동 포함되는 HIGH 추천:
{json.dumps(required_candidates, ensure_ascii=False, indent=2)}

선택 가능한 MEDIUM/LOW 추천:
{json.dumps(optional_candidates, ensure_ascii=False, indent=2)}

Backend가 전달한 trigger를 사용자 상황의 중요한 문맥으로
사용하되 trigger 값을 새로 계산하거나 변경하지 마세요.

제공된 MEDIUM/LOW 후보 중 사용자에게 유용한 항목을
최대 {optional_limit}개 선택하세요.

HIGH 추천은 애플리케이션이 자동으로 포함하므로
반환하지 마세요.

후보에 없는 추천을 생성하지 마세요.
title과 type은 후보의 값을 그대로 사용하세요.
priority, reason, category를 새로 작성하거나 변경하지 마세요.

응답은 JSON 객체 하나만 반환하세요.
설명 문장이나 마크다운은 쓰지 마세요.

반환 형식:
{{
  "recommendations": [
    {{
      "type": "LAW",
      "title": "후보에 존재하는 실제 title"
    }}
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Select only from the provided "
                        "optional recommendation candidates. "
                        "Use the backend trigger as context. "
                        "Never invent or modify titles, "
                        "priorities, reasons, or categories. "
                        "Respond with JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
        )

        content = (
            response.choices[0]
            .message.content
        )

        if not content:
            return []

        parsed = parse_json_object(content)
        recommendations = parsed.get(
            "recommendations",
            [],
        )

        if not isinstance(recommendations, list):
            return []

        return recommendations

    except Exception as error:
        print("OPTIONAL RECOMMENDATION ERROR:", error)
        return []
