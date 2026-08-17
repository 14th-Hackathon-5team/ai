import json
import os

from dotenv import load_dotenv
from groq import Groq

from app.models import UserProfile


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY를 찾을 수 없습니다.")

client = Groq(api_key=api_key)


def generate_ai_recommendation(
    user: UserProfile,
    legal_recommendations: list,
    university_recommendations: list,
):
    user_data = user.model_dump(mode="json")

    law_candidates = [
        {
            "type": item.get("type"),
            "title": item.get("title"),
            "priority": item.get("priority"),
            "reason": item.get("reason"),
        }
        for item in legal_recommendations
    ]

    university_candidates = [
        {
            "type": item.get("type"),
            "title": item.get("title"),
            "priority": item.get("priority"),
            "matchScore": item.get("matchScore"),
            "reason": item.get("reason"),
        }
        for item in university_recommendations
    ]

    prompt = f"""
사용자 프로필:
{json.dumps(user_data, ensure_ascii=False, indent=2)}

법률 추천 후보:
{json.dumps(law_candidates, ensure_ascii=False, indent=2)}

대학 추천 후보:
{json.dumps(university_candidates, ensure_ascii=False, indent=2)}

당신은 한국에 거주하거나 유학하려는 외국인을 위한 정보 추천 AI입니다.

당신의 역할은 제공된 추천 후보 중 사용자에게 의미 있는 항목을 선택하고,
왜 해당 정보가 관련 있는지 간단하게 설명하는 것입니다.

법률의 실제 내용, 기한, 벌칙, 절차, 법 조항은 직접 생성하지 마세요.
대학의 실제 일정, 지원서류, 지원자격도 직접 생성하지 마세요.
이 정보들은 애플리케이션이 원본 데이터에서 별도로 제공합니다.

반드시 제공된 사용자 프로필과 추천 후보만 사용하세요.

사용자 프로필에 없는 정보는 추측하지 마세요.

허가 여부, 신청 완료 여부, 전체 입학자격 충족 여부 등
확인할 수 없는 내용을 단정하지 마세요.

TOPIK 조건을 충족했다고 해서
전체 대학 지원자격을 충족한다고 표현하지 마세요.

LAW의 title은 반드시 법률 추천 후보의 실제 title을 그대로 사용하세요.

UNIVERSITY의 title은 반드시 대학 추천 후보의 실제 title을 그대로 사용하세요.

title을 새로 만들거나 수정하지 마세요.

"대학 입학 준비", "대학 지원" 등의 임의 제목을 만들지 마세요.

여러 대학을 하나의 recommendation으로 묶지 마세요.

추천은 최대 5개까지만 반환하세요.

priority는 각 추천 후보에 제공된 값을 그대로 사용하세요.
priority를 새로 판단하거나 변경하지 마세요.

summary와 reason은 반드시 자연스러운 한국어로 작성하세요.
일본어, 중국어 등 한국어가 아닌 문자를 혼용하지 마세요.

날짜 뒤에는 한국어 표현인 '일에'를 사용하세요.
'D2', 'D4'는 사용자에게 각각 'D-2', 'D-4 체류자격'으로 표현하세요.

대학의 TOPIK 조건만 확인된 경우에는
'TOPIK 조건을 충족합니다'라고 표현하세요.
전체 입학 조건이나 전체 지원 자격을 충족한다고 단정하지 마세요.

응답은 반드시 JSON 형식으로만 반환하세요.

{{
  "summary": "사용자의 현재 상황을 짧게 설명",
  "recommendations": [
    {{
      "type": "LAW 또는 UNIVERSITY",
      "priority": "HIGH 또는 MEDIUM 또는 LOW",
      "title": "후보에 존재하는 실제 title",
      "reason": "사용자 프로필을 기준으로 해당 정보가 관련 있는 이유"
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a recommendation assistant for foreign residents "
                    "and international students in Korea. "
                    "Select only from the candidates provided by the application. "
                    "Never create a new recommendation title."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.1,
        response_format={
            "type": "json_object"
        },
    )

    content = response.choices[0].message.content

    return json.loads(content)