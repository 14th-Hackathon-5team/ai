import json
import os

from dotenv import load_dotenv
from groq import Groq

from app.models import UserProfile


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY가 없습니다. "
        "프로젝트 루트의 .env 파일에 입력하세요."
    )

client = Groq(api_key=api_key)


def select_optional_recommendations(
    user: UserProfile,
    required_recommendations: list,
    optional_recommendations: list,
    optional_limit: int,
):
    if (
        optional_limit <= 0
        or not optional_recommendations
    ):
        return []

    user_data = user.model_dump(
        mode="json"
    )

    required_candidates = [
        {
            "type": item.get("type"),
            "title": item.get("title"),
            "priority": item.get(
                "priority"
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
        }
        for item in optional_recommendations
    ]

    prompt = f"""
사용자 프로필:
{json.dumps(user_data, ensure_ascii=False, indent=2)}

이미 자동 포함되는 HIGH 추천:
{json.dumps(required_candidates, ensure_ascii=False, indent=2)}

선택 가능한 MEDIUM/LOW 추천:
{json.dumps(optional_candidates, ensure_ascii=False, indent=2)}

제공된 MEDIUM/LOW 후보 중 사용자에게 유용한 항목을
최대 {optional_limit}개 선택하세요.

HIGH 추천은 애플리케이션이 자동으로 포함하므로
반환하지 마세요.

후보에 없는 추천을 생성하지 마세요.
title과 type은 후보의 값을 그대로 사용하세요.
priority와 reason을 새로 작성하지 마세요.

응답은 반드시 다음 JSON 형식으로만 반환하세요.

{{
  "recommendations": [
    {{
      "type": "LAW 또는 UNIVERSITY",
      "title": "후보에 존재하는 실제 title"
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Select only from the provided "
                    "optional recommendation candidates. "
                    "Never invent or modify titles. "
                    "Respond with JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.1,
        response_format={
            "type": "json_object",
        },
    )

    content = (
        response.choices[0]
        .message.content
    )

    if not content:
        raise ValueError(
            "Groq API 응답 내용이 비어 있습니다."
        )

    parsed = json.loads(content)

    return parsed.get(
        "recommendations",
        [],
    )