import json
import os

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Query,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    RecommendationRequest,
    UserProfile,
)
from app.news_service import write_news_result
from app.recommender import recommend


load_dotenv()

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")


app = FastAPI(
    title="Foreign Student Recommendation API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://frontend-chi-pied-78.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_internal_api_key(
    x_internal_api_key: str | None,
):
    if not INTERNAL_API_KEY:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="INTERNAL_API_KEY is not configured",
        )

    if x_internal_api_key != INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/recommend")
def create_recommendation(
    request: RecommendationRequest,
    x_internal_api_key: str | None = Header(
        default=None,
        alias="X-Internal-API-Key",
    ),
):
    verify_internal_api_key(x_internal_api_key)

    return recommend(
        user=request.user,
        trigger=request.trigger,
    )


@app.post("/recommendations")
def create_recommendations(user: UserProfile):
    return recommend(user)


@app.get("/news")
def get_news(
    refresh: bool = Query(default=False),
    language: str = Query(default="ko"),
):
    return write_news_result(
        force_refresh=refresh,
        language=language,
    )


def run_from_file():
    with open("user.json", "r", encoding="utf-8") as file:
        user_data = json.load(file)

    user = UserProfile(**user_data)

    result = recommend(user)

    with open("result.json", "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("result.json 생성 완료")

    write_news_result(
        force_refresh=True,
        language=getattr(user, "language", "ko"),
    )

    print("news_result.json 생성 완료")


if __name__ == "__main__":
    run_from_file()
