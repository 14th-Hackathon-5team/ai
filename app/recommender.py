from app.models import UserProfile
from app.law_service import recommend_laws
from app.univ_service import recommend_universities
from app.llm_service import generate_ai_recommendation


PRIORITY_ORDER = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
}

MAX_RECOMMENDATIONS = 5


def candidate_key(candidate: dict):
    return (
        candidate.get("type"),
        candidate.get("title"),
    )


def find_candidate(
    recommendation_type: str,
    title: str,
    candidates: list,
):
    target_key = (
        recommendation_type,
        title,
    )

    for candidate in candidates:
        if candidate_key(candidate) == target_key:
            return candidate

    return None


def make_final_item(
    candidate: dict,
    ai_reason: str | None = None,
):
    return {
        "type": candidate.get("type"),
        "priority": candidate.get(
            "priority",
            "LOW",
        ),
        "title": candidate.get("title"),
        "reason": (
            ai_reason
            or candidate.get("reason")
        ),
        "detail": candidate.get("detail"),
    }


def recommend(user: UserProfile):
    legal_candidates = recommend_laws(user)

    university_candidates = recommend_universities(
        user,
        limit=3,
    )

    all_candidates = (
        legal_candidates
        + university_candidates
    )

    high_candidates = [
        candidate
        for candidate in all_candidates
        if candidate.get("priority") == "HIGH"
    ]

    optional_candidates = [
        candidate
        for candidate in all_candidates
        if candidate.get("priority") != "HIGH"
    ]

    optional_limit = max(
        0,
        MAX_RECOMMENDATIONS - len(high_candidates),
    )

    ai_recommendation = generate_ai_recommendation(
        user=user,
        required_recommendations=high_candidates,
        optional_recommendations=optional_candidates,
        optional_limit=optional_limit,
    )

    final_recommendations = [
        make_final_item(candidate)
        for candidate in high_candidates
    ]

    included_keys = {
        candidate_key(candidate)
        for candidate in high_candidates
    }

    for item in ai_recommendation.get(
        "recommendations",
        [],
    ):
        if (
            len(final_recommendations)
            >= MAX_RECOMMENDATIONS
        ):
            break

        candidate = find_candidate(
            recommendation_type=item.get("type"),
            title=item.get("title"),
            candidates=optional_candidates,
        )

        if candidate is None:
            continue

        key = candidate_key(candidate)

        if key in included_keys:
            continue

        final_recommendations.append(
            make_final_item(
                candidate=candidate,
                ai_reason=item.get("reason"),
            )
        )

        included_keys.add(key)

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