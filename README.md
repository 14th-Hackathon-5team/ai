# KBuddy-AI

외국인 유학생을 위한 맞춤형 법률·대학·뉴스 추천 AI 서비스입니다.

## 프로젝트 배경
외국인 유학생은 외국인등록, 체류기간 연장, 아르바이트 허가, 대학 입학 일정과 같은 정보를
개인 상황에 맞게 확인하기 어렵고, 필요한 기한을 놓치는 경우가 있습니다.

KBuddy에서 AI파트는 사용자의 프로필과 체류·학업 상황을 분석해 필요한 법률·대학 정보를 우선순위에 따라 추천하고, 관련 뉴스까지 제공하는 AI 서비스를 제공합니다.

## 서비스 주소

- Frontend: https://frontend-chi-pied-78.vercel.app/login

## 주요 기능

- 외국인 유학생 사용자 프로필 기반 맞춤 추천
- 외국인등록, 체류기간 연장, 아르바이트 허가 등 법률·비자 정보 추천
- TOPIK 등급과 모집 일정 기반 대학 입학 정보 추천
- Groq AI를 활용한 추천 후보 선택
- 네이버 뉴스 API를 통한 유학생 관련 뉴스 수집
- GPT 기반 뉴스 3줄 요약 및 상세 요약 생성

## 프로젝트 구조

```txt
app/
  main.py              FastAPI 메인 실행 파일
  models.py            요청/응답 데이터 모델 정의
  recommender.py       최종 추천 목록 생성
  law_service.py       법률·비자·체류 추천 로직
  univ_service.py      대학 입학 추천 로직
  message_service.py   사용자 요약 및 추천 사유 문장 생성
  llm_service.py       Groq AI 기반 추천 후보 선택
  news_service.py      네이버 뉴스 수집 및 GPT 뉴스 요약

data/
  law_info.json        법률·비자·체류 정보 원본 데이터
  univ_info.json       대학 입학 정보 원본 데이터

user.json              로컬 실행용 사용자 예시 데이터
request_fixture.json   요청 예시 데이터
result.json            추천 결과 예시
news_result.json       뉴스 결과 예시
pyproject.toml         프로젝트 의존성 및 Python 설정
uv.lock                패키지 버전 잠금 파일
개발 환경
- Python 3.14 이상
- FastAPI
- Uvicorn
- Pydantic
- python-dotenv
- Groq
설치 방법
프로젝트를 클론한 뒤 의존성을 설치합니다.
uv sync
환경변수 설정
프로젝트 루트에 .env 파일을 생성하고 아래 값을 설정합니다.
GROQ_API_KEY=Groq_API_Key
NAVER_CLIENT_ID=Naver_Client_ID
NAVER_CLIENT_SECRET=Naver_Client_Secret
NEWS_AI_API_KEY=News_AI_API_Key
NEWS_AI_MODEL=gpt-5.6-luna
NAVER_NEWS_PROVIDER=api_hub
NAVER_NEWS_KEYWORDS=유학생,외국인 유학생,유학생 비자,유학생 체류,유학생 외국인등록,유학생 아르바이트,유학생 취업,유학생 건강보험,유학생 장학금,어학연수생
환경변수 설명
변수명	설명
GROQ_API_KEY	추천 후보 선택에 사용하는 Groq API Key
NAVER_CLIENT_ID	네이버 뉴스 API 호출용 Client ID
NAVER_CLIENT_SECRET	네이버 뉴스 API 호출용 Client Secret
NEWS_AI_API_KEY	뉴스 요약에 사용하는 GPT API Key
NEWS_AI_MODEL	뉴스 요약에 사용할 GPT 모델명
NAVER_NEWS_PROVIDER	네이버 뉴스 API 제공 방식
NAVER_NEWS_KEYWORDS	뉴스 검색에 사용할 키워드 목록


## 서버 실행

로컬 실행:

```bash
uvicorn app.main:app --reload
```

배포 환경 실행:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

서버 실행 후 API 문서는 아래 주소에서 확인할 수 있습니다.

```txt
http://127.0.0.1:8000/docs
```

## API

### 상태 확인

```http
GET /health
```

응답 예시:

```json
{
  "status": "ok"
}
```

### 맞춤 추천 생성

```http
POST /recommendations
```

사용자 프로필을 기반으로 법률·비자·대학 입학 추천을 생성합니다.

요청 예시:

```json
{
  "userId": 1001,
  "nationality": "Vietnam",
  "birthYear": 2004,
  "userStatus": "LANGUAGE_STUDENT",
  "schoolName": "Seoul Korean Language Institute",
  "entryDate": "2026-06-01",
  "visaType": "D4",
  "hasAlienRegistration": false,
  "stayExpirationDate": "2026-10-15",
  "housingType": "DORMITORY",
  "isParentSupported": false,
  "partTimeStatus": "SEARCHING",
  "partTimeStartDate": null,
  "hasPartTimePermit": false,
  "currentTopikLevel": "LEVEL_3",
  "targetTopikLevel": "LEVEL_4",
  "language": "KOREAN"
}
```

응답 예시:

```json
{
  "userId": 1001,
  "summary": "현재 D-4 체류자격으로 한국에서 유학 중입니다.",
  "recommendations": [
    {
      "type": "LAW",
      "priority": "HIGH",
      "title": "외국인 등록",
      "reason": "외국인등록이 아직 완료되지 않았습니다.",
      "detail": {
        "category": "ENTRY",
        "title": "외국인 등록"
      }
    }
  ]
}
```

### 뉴스 조회

```http
GET /news
```

네이버 뉴스 API에서 외국인 유학생 관련 뉴스를 수집하고 GPT를 활용해 요약합니다.

응답 예시:

```json
{
  "news": [
    {
      "title": "외국인 유학생 지원 정책 확대",
      "threeLineSummary": [
        "외국인 유학생 지원이 확대됩니다.",
        "비자와 체류 지원이 강화됩니다.",
        "취업과 정착 지원도 함께 논의됩니다."
      ],
      "detailedSummary": "외국인 유학생을 위한 비자, 체류, 취업, 정착 지원 정책이 확대됩니다. 관련 기관은 유학생이 한국 생활에 적응할 수 있도록 행정 지원과 상담을 강화할 예정입니다.",
      "link": "https://example.com/news"
    }
  ]
}
```

## 추천 로직

### 법률·비자 추천

사용자의 비자 종류, 입국일, 외국인등록 여부, 체류기간 만료일, 아르바이트 상태를 기준으로 추천을 생성합니다.

주요 추천 항목은 다음과 같습니다.

- 외국인 등록
- 체류기간 만료/연장
- 유학생 아르바이트 허가
- 유학생 비자 종류 D-2
- 유학생 비자 종류 D-4

### 대학 입학 추천

사용자의 현재 TOPIK 등급과 대학별 모집 일정을 기준으로 추천 가능한 대학을 선택합니다.

추천 기준은 다음과 같습니다.

- 사용자 상태 확인
- 대학별 TOPIK 요구 조건 충족 여부 확인
- 원서접수 기간 확인
- 우선순위와 매칭 점수 계산

### AI 추천 선택

법률 추천과 대학 추천 후보를 먼저 생성한 뒤, 우선순위가 높은 추천은 자동으로 포함합니다.

남은 추천 후보는 Groq AI가 사용자 상황을 참고해 선택합니다.

## 뉴스 수집 및 요약 로직

뉴스 기능은 네이버 뉴스 API와 GPT 요약 API를 함께 사용합니다.

처리 순서는 다음과 같습니다.

```txt
1. NAVER_NEWS_KEYWORDS 기준으로 네이버 뉴스 검색
2. 중복 기사 제거
3. 서비스 목적과 맞지 않는 기사 제외
4. 유학생, 비자, 체류, 취업, 장학금 등 키워드 기준으로 관련도 계산
5. 관련도 높은 기사 선택
6. GPT로 3줄 요약과 상세 요약 생성
7. /news 응답으로 반환
```

## 로컬 파일 실행

아래 명령어로 로컬 테스트용 JSON 파일을 기반으로 결과 파일을 생성할 수 있습니다.

```bash
uv run python -m app.main
```

실행 결과로 아래 파일이 생성 또는 갱신됩니다.

```txt
result.json
news_result.json
```

## 주의사항

- `.env` 파일은 Git에 커밋하지 않습니다.
- API Key를 코드나 JSON 파일에 직접 작성하지 않습니다.
- FastAPI 공식 실행 기준은 `app.main`입니다.
- 백엔드는 `/recommendations`, `/news`를 기준으로 연동합니다.
- 네이버 API 인증 실패 시 뉴스 결과가 비어 있을 수 있습니다.
- 뉴스 요약 API 실패 시 기본 요약 로직으로 대체될 수 있습니다.