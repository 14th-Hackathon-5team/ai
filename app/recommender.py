from app.models import UserProfile
from app.law_service import recommend_laws
from app.univ_service import recommend_universities
from app.llm_service import generate_ai_recommendation


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
                "priority": item.get(
                    "priority",
                    candidate.get("priority"),
                ),
                "title": title,
                "reason": item.get(
                    "reason",
                    candidate.get("reason"),
                ),
                "detail": candidate.get("detail"),
            }
        )

    return {
        "userId": user.userId,
        "summary": ai_recommendation.get("summary"),
        "recommendations": final_recommendations,
    }