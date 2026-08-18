import logging

from fastapi import (
    FastAPI,
    HTTPException,
    status,
)

from app.models import (
    RecommendationRequest,
    RecommendationResponse,
)
from app.recommender import recommend


logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Buddy Recommendation API",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.post(
    "/recommend",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
)
def create_recommendation(
    request: RecommendationRequest,
):
    try:
        result = recommend(
            user=request.user,
            trigger=request.trigger,
        )

        response = (
            RecommendationResponse
            .model_validate(result)
        )

        return response

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "추천 생성 중 오류가 발생했습니다."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "추천 생성 중 오류가 "
                "발생했습니다."
            ),
        )