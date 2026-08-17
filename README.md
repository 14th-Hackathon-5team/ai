# ai
## 실행 방법

### 1. 프로젝트 클론

git clone <repository-url>
cd ai

### 2. 개발 환경 구성

uv sync

### 3. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

GROQ_API_KEY=your_api_key

### 4. 실행

uv run python -m app.main
