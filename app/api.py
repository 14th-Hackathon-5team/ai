import logging
import os
import secrets
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    Header,
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


def verify_internal_api_key(
    x_internal_api_key: Annotated[
        str | None,
        Header(alias="X-Internal-API-Key"),
    ] = None,
):
    expected_api_key = os.getenv(
        "INTERNAL_API_KEY"
    )

    if not expected_api_key:
        logger.error(
            "INTERNAL_API_KEY가 설정되지 않았습니다."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="서버 인증 설정이 올바르지 않습니다.",
        )

    if (
        not x_internal_api_key
        or not secrets.compare_digest(
            x_internal_api_key,
            expected_api_key,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 내부 API 키입니다.",
        )


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.post(
    "/recommend",
    response_model=RecommendationResponse,
)
def create_recommendation(
    request: RecommendationRequest,
    _: None = Depends(
        verify_internal_api_key
    ),
):
    try:
        return recommend(
            user=request.user,
            trigger=request.trigger,
        )

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
            detail="추천 생성 중 오류가 발생했습니다.",
        )