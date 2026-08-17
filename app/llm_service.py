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


def generate_ai_recommendation(
    user: UserProfile,
    required_recommendations: list,
    optional_recommendations: list,
    optional_limit: int,
):
    user_data = user.model_dump(mode="json")

    required_candidates = [
        {
            "type": item.get("type"),
            "title": item.get("title"),
            "priority": item.get("priority"),
            "reason": item.get("reason"),
        }
        for item in required_recommendations
    ]

    optional_candidates = [
        {
            "type": item.get("type"),
            "title": item.get("title"),
            "priority": item.get("priority"),
            "matchScore": item.get("matchScore"),
            "reason": item.get("reason"),
        }
        for item in optional_recommendations
    ]

    prompt = f"""
사용자 프로필:
{json.dumps(user_data, ensure_ascii=False, indent=2)}

반드시 포함되는 HIGH 추천:
{json.dumps(required_candidates, ensure_ascii=False, indent=2)}

선택 가능한 MEDIUM/LOW 추천:
{json.dumps(optional_candidates, ensure_ascii=False, indent=2)}

당신은 한국에 거주하거나 유학하려는 외국인을 위한
정보 추천 AI입니다.

HIGH 추천은 애플리케이션이 자동으로 최종 결과에 포함합니다.
따라서 recommendations에는 HIGH 추천을 반환하지 마세요.

MEDIUM/LOW 후보 중 사용자에게 유용한 항목만 선택하세요.
선택 가능한 추천은 최대 {optional_limit}개입니다.

제공된 후보에 없는 추천을 새로 만들지 마세요.
title은 후보의 실제 title을 그대로 사용하세요.
title을 수정하거나 여러 항목을 하나로 묶지 마세요.

priority는 후보에 제공된 값을 그대로 사용하세요.
priority를 새로 판단하거나 변경하지 마세요.

법률의 실제 내용, 기한, 벌칙, 절차를 생성하지 마세요.
대학의 실제 일정, 서류, 자격을 생성하지 마세요.
사용자 프로필에 없는 정보는 추측하지 마세요.

대학의 TOPIK 조건만 확인된 경우에는
TOPIK 조건을 충족한다고만 표현하세요.
전체 입학 자격을 충족한다고 단정하지 마세요.

summary와 reason은 자연스러운 한국어로 작성하세요.
일본어와 중국어 문자를 혼용하지 마세요.
D2와 D4는 각각 D-2와 D-4 체류자격으로 표현하세요.

응답은 반드시 아래 JSON 형식으로만 반환하세요.

{{
  "summary": "사용자의 현재 상황에 대한 짧은 한국어 설명",
  "recommendations": [
    {{
      "type": "LAW 또는 UNIVERSITY",
      "priority": "MEDIUM 또는 LOW",
      "title": "후보에 존재하는 실제 title",
      "reason": "사용자에게 해당 정보가 유용한 이유"
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
                    "You are a recommendation assistant "
                    "for foreign residents and international "
                    "students in Korea. Select only from the "
                    "provided optional candidates. Never change "
                    "titles or priorities. Respond in natural "
                    "Korean and JSON only."
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

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "Groq API 응답 내용이 비어 있습니다."
        )

    return json.loads(content)