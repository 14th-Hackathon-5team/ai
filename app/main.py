import json

from app.models import UserProfile
from app.recommender import recommend


def main():
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


if __name__ == "__main__":
    main()