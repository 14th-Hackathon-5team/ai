import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import UserProfile
from app.news_service import write_news_result
from app.recommender import recommend


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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/recommendations")
def create_recommendations(user: UserProfile):
    return recommend(user)


@app.get("/news")
def get_news():
    return write_news_result()


def run_from_file():
    with open("user.json", "r", encoding="utf-8") as f:
        user_data = json.load(f)

    user = UserProfile(**user_data)

    result = recommend(user)

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("result.json 생성 완료")

    write_news_result()

    print("news_result.json 생성 완료")


if __name__ == "__main__":
    run_from_file()