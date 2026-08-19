from datetime import date

from app.law_service import recommend_laws
from app.llm_service import (
    select_optional_recommendations,
)
from app.message_service import build_summary
from app.models import (
    NotificationCategory,
    RecommendationTrigger,
    UserProfile,
)
from app.univ_service import (
    recommend_universities,
)


PRIORITY_ORDER = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
}

MAX_RECOMMENDATIONS = 5

VALID_NOTIFICATION_CATEGORIES = {
    category.value
    for category in NotificationCategory
}


def candidate_key(
    candidate: dict,
):
    return (
        candidate.get("type"),
        candidate.get("title"),
    )


def has_valid_category(
    candidate: dict,
) -> bool:
    detail = candidate.get("detail")

    if not isinstance(detail, dict):
        return False

    category = detail.get("category")

    return (
        category
        in VALID_NOTIFICATION_CATEGORIES
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
        if (
            candidate_key(candidate)
            == target_key
        ):
            return candidate

    return None


def make_final_item(
    candidate: dict,
):
    return {
        "type": candidate.get("type"),
        "priority": candidate.get(
            "priority",
            "LOW",
        ),
        "title": candidate.get("title"),
        "reason": candidate.get("reason"),
        "detail": candidate.get("detail"),
    }


def recommend(
    user: UserProfile,
    trigger: RecommendationTrigger | None = None,
):
    legal_candidates = recommend_laws(user)

    university_candidates = (
        recommend_universities(
            user,
            limit=3,
        )
    )

    generated_candidates = (
        legal_candidates
        + university_candidates
    )

    all_candidates = [
        candidate
        for candidate in generated_candidates
        if has_valid_category(candidate)
    ]

    all_candidates.sort(
        key=lambda item: PRIORITY_ORDER.get(
            item.get("priority"),
            3,
        )
    )

    high_candidates = [
        candidate
        for candidate in all_candidates
        if candidate.get("priority") == "HIGH"
    ]

    high_candidates = high_candidates[
        :MAX_RECOMMENDATIONS
    ]

    optional_candidates = [
        candidate
        for candidate in all_candidates
        if candidate.get("priority") != "HIGH"
    ]

    optional_limit = max(
        0,
        MAX_RECOMMENDATIONS
        - len(high_candidates),
    )

    selected_items = (
        select_optional_recommendations(
            user=user,
            trigger=trigger,
            required_recommendations=(
                high_candidates
            ),
            optional_recommendations=(
                optional_candidates
            ),
            optional_limit=optional_limit,
        )
    )

    final_recommendations = [
        make_final_item(candidate)
        for candidate in high_candidates
    ]

    included_keys = {
        candidate_key(candidate)
        for candidate in high_candidates
    }

    for item in selected_items:
        if (
            len(final_recommendations)
            >= MAX_RECOMMENDATIONS
        ):
            break

        candidate = find_candidate(
            recommendation_type=item.get(
                "type"
            ),
            title=item.get("title"),
            candidates=optional_candidates,
        )

        if candidate is None:
            continue

        if not has_valid_category(candidate):
            continue

        key = candidate_key(candidate)

        if key in included_keys:
            continue

        final_recommendations.append(
            make_final_item(candidate)
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
        "summary": build_summary(
            user=user,
            today=date.today(),
        ),
        "recommendations": (
            final_recommendations[
                :MAX_RECOMMENDATIONS
            ]
        ),
    }