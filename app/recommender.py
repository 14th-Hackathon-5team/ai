from app.models import UserProfile
from app.law_service import recommend_laws
from app.univ_service import recommend_universities
from app.llm_service import generate_ai_recommendation


PRIORITY_ORDER = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
}


def find_candidate(
    recommendation_type: str,
    title: str,
    legal_recommendations: list,
    university_recommendations: list,
):
    if recommendation_type == "LAW":
        candidates = legal_recommendations

    elif recommendation_type == "UNIVERSITY":
        candidates = university_recommendations

    else:
        return None

    for candidate in candidates:
        if candidate.get("title") == title:
            return candidate

    return None


def recommend(user: UserProfile):
    legal_recommendations = recommend_laws(user)

    university_recommendations = recommend_universities(
        user,
        limit=3,
    )

    ai_recommendation = generate_ai_recommendation(
        user=user,
        legal_recommendations=legal_recommendations,
        university_recommendations=university_recommendations,
    )

    final_recommendations = []

    for item in ai_recommendation.get(
        "recommendations",
        [],
    ):
        recommendation_type = item.get("type")
        title = item.get("title")

        candidate = find_candidate(
            recommendation_type=recommendation_type,
            title=title,
            legal_recommendations=legal_recommendations,
            university_recommendations=university_recommendations,
        )

        if candidate is None:
            continue

        final_recommendations.append(
            {
                "type": recommendation_type,

                # AI가 만든 priority를 사용하지 않습니다.
                # law_service 또는 univ_service가 계산한 값을 사용합니다.
                "priority": candidate.get(
                    "priority",
                    "LOW",
                ),

                "title": title,

                # 날짜와 상태가 포함된 규칙 기반 reason을 우선 사용합니다.
                "reason": candidate.get(
                    "reason",
                    item.get("reason"),
                ),

                "detail": candidate.get("detail"),
            }
        )

    final_recommendations.sort(
        key=lambda item: PRIORITY_ORDER.get(
            item.get("priority"),
            3,
        )
    )

    return {
        "userId": user.userId,
        "summary": ai_recommendation.get("summary"),
        "recommendations": final_recommendations,
    }