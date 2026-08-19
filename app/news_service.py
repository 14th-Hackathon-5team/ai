import json
import os
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
NEWS_RESULT_PATH = BASE_DIR / "news_result.json"

NAVER_API_HUB_NEWS_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
NAVER_DEVELOPERS_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"

OPENAI_RESPONSES_API_URL = "https://api.openai.com/v1/responses"

DEFAULT_KEYWORDS = [
    "외국인 유학생 지원",
    "유학생 비자",
    "유학생 체류",
    "유학생 외국인등록",
    "유학생 아르바이트",
    "유학생 시간제 취업",
    "유학생 건강보험",
    "유학생 장학금",
    "유학생 취업",
    "어학연수생 지원",
]

USEFUL_TERMS = [
    "지원",
    "비자",
    "체류",
    "연장",
    "외국인등록",
    "등록증",
    "아르바이트",
    "시간제",
    "취업",
    "건강보험",
    "보험",
    "장학금",
    "입학",
    "TOPIK",
    "한국어능력시험",
    "교육",
    "상담",
    "정착",
]

STUDENT_TERMS = [
    "유학생",
    "외국인 유학생",
    "어학연수",
    "어학연수생",
    "D-2",
    "D2",
    "D-4",
    "D4",
]

BLOCKED_TERMS = [
    "성폭행",
    "성범죄",
    "강간",
    "추행",
    "폭행",
    "살해",
    "살인",
    "마약",
    "음주",
    "만취",
    "구속",
    "구속송치",
    "검거",
    "피의자",
    "피해자",
    "경찰",
    "범죄",
    "불법촬영",
    "체포",
    "징역",
    "재판",
    "외국인투자",
    "외국인 투자",
    "외국인 매수",
    "외국인 매도",
    "외국인 선수",
    "외국인 감독",
    "관광객",
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return

        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        return normalize_text(" ".join(self.parts))


def normalize_text(value: str):
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def clean_naver_text(value: str):
    return normalize_text(re.sub(r"</?b>", "", value or ""))


def trim_text(text: str, max_length: int):
    text = normalize_text(text)

    if len(text) <= max_length:
        return text

    return text[:max_length].rstrip() + "..."


def get_keywords():
    raw_keywords = os.getenv("NAVER_NEWS_KEYWORDS")

    if not raw_keywords:
        return DEFAULT_KEYWORDS

    keywords = [
        keyword.strip()
        for keyword in raw_keywords.split(",")
        if keyword.strip()
    ]

    return keywords or DEFAULT_KEYWORDS


def get_naver_provider():
    return os.getenv("NAVER_NEWS_PROVIDER", "api_hub").strip().lower()


def get_naver_auth_headers():
    provider = get_naver_provider()

    if provider == "developers":
        client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
        client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()

        return {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }

    client_id = (
        os.getenv("NAVER_API_HUB_CLIENT_ID")
        or os.getenv("NAVER_CLIENT_ID")
        or ""
    ).strip()

    client_secret = (
        os.getenv("NAVER_API_HUB_CLIENT_SECRET")
        or os.getenv("NAVER_CLIENT_SECRET")
        or ""
    ).strip()

    return {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
    }


def get_naver_news_url():
    if get_naver_provider() == "developers":
        return NAVER_DEVELOPERS_NEWS_URL

    return NAVER_API_HUB_NEWS_URL


def request_json(url: str):
    headers = get_naver_auth_headers()

    if not all(headers.values()):
        raise RuntimeError("NAVER API 인증 키가 없습니다.")

    request = Request(url, headers=headers)

    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def search_news(keyword: str, display: int = 10):
    provider = get_naver_provider()

    params = {
        "query": keyword,
        "display": display,
        "start": 1,
        "sort": "date",
    }

    if provider != "developers":
        params["format"] = "json"

    url = f"{get_naver_news_url()}?{urlencode(params)}"

    try:
        data = request_json(url)
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        print("NAVER HTTP ERROR:", error.code, error.reason)
        print(error_body)
        return []
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        print("NAVER ERROR:", error)
        return []

    return data.get("items", [])


def fetch_article_text(url: str):
    if not url:
        return ""

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    )

    try:
        with urlopen(request, timeout=5) as response:
            content_type = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(content_type, errors="ignore")
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError):
        return ""

    parser = TextExtractor()
    parser.feed(html)

    return parser.get_text()


def get_searchable_text(raw_item: dict):
    title = clean_naver_text(raw_item.get("title", ""))
    description = clean_naver_text(raw_item.get("description", ""))

    return f"{title} {description}"


def has_blocked_term(raw_item: dict):
    text = get_searchable_text(raw_item)

    return any(term in text for term in BLOCKED_TERMS)


def calculate_relevance_score(raw_item: dict):
    text = get_searchable_text(raw_item)

    if has_blocked_term(raw_item):
        return -100

    score = 0

    for term in STUDENT_TERMS:
        if term in text:
            score += 5

    for term in USEFUL_TERMS:
        if term in text:
            score += 3

    return score


def split_sentences(text: str):
    text = normalize_text(text)

    if not text:
        return []

    sentences = re.split(r"(?<=[.!?。])\s+", text)

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def fallback_summary(title: str, description: str, article_text: str):
    source_text = description or article_text or title
    sentences = split_sentences(source_text)

    lines = []

    for sentence in sentences:
        line = trim_text(sentence, 70)
        if line and line not in lines:
            lines.append(line)

        if len(lines) == 3:
            break

    if len(lines) < 3 and title:
        title_line = trim_text(title, 70)
        if title_line not in lines:
            lines.append(title_line)

    if len(lines) < 3 and description:
        description_line = trim_text(description, 70)
        if description_line not in lines:
            lines.append(description_line)

    while len(lines) < 3:
        lines.append("원문 기사에서 자세한 내용을 확인할 수 있습니다.")

    detailed_source = article_text or description or title

    return {
        "threeLineSummary": lines[:3],
        "detailedSummary": trim_text(detailed_source, 700),
    }


def get_news_ai_api_key():
    return os.getenv("NEWS_AI_API_KEY", "").strip()


def get_news_ai_model():
    return os.getenv("NEWS_AI_MODEL", "gpt-5.6-luna").strip()


def build_news_summary_prompt(title: str, description: str, article_text: str):
    article_text = trim_text(article_text, 6000)

    return f"""
아래 뉴스 자료를 외국인 유학생에게 도움이 되는 정보 중심으로 요약해줘.

작성 규칙:
- 반드시 한국어로 작성한다.
- 출력은 JSON 객체 하나만 반환한다.
- threeLineSummary는 정확히 3개의 문자열 배열로 작성한다.
- threeLineSummary 각 문장은 45자 이내로 짧게 작성한다.
- detailedSummary는 3~5문장으로 작성한다.
- 외국인 유학생이 실제로 알아야 할 정책, 비자, 체류, 등록, 취업, 건강보험, 장학금, 학교생활 정보를 우선한다.
- 기사에 사건사고나 자극적인 내용이 있더라도 강조하지 않는다.
- 기사에 없는 내용은 절대 추측하지 않는다.
- 기관명, 날짜, 신청 대상, 제도명이 있으면 detailedSummary에 포함한다.
- 단순 홍보성 문구는 줄이고 사용자가 알아야 할 변화나 행동 정보를 중심으로 정리한다.

뉴스 제목:
{title}

네이버 요약:
{description}

기사 본문:
{article_text}
""".strip()


def extract_openai_response_text(response_data: dict):
    if response_data.get("output_text"):
        return response_data["output_text"]

    texts = []

    for output_item in response_data.get("output", []):
        for content_item in output_item.get("content", []):
            if not isinstance(content_item, dict):
                continue

            text = content_item.get("text")
            if text:
                texts.append(text)

    return "\n".join(texts).strip()


def parse_json_object(text: str):
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("JSON 객체를 찾을 수 없습니다.")

    return json.loads(match.group(0))


def normalize_summary_result(
    summary: dict,
    title: str,
    description: str,
    article_text: str,
):
    fallback = fallback_summary(
        title=title,
        description=description,
        article_text=article_text,
    )

    raw_lines = summary.get("threeLineSummary", [])
    lines = []

    if isinstance(raw_lines, list):
        for line in raw_lines:
            line = trim_text(str(line), 70)
            if line:
                lines.append(line)

    for line in fallback["threeLineSummary"]:
        if len(lines) >= 3:
            break

        if line not in lines:
            lines.append(line)

    detailed_summary = normalize_text(
        str(summary.get("detailedSummary", ""))
    )

    if not detailed_summary:
        detailed_summary = fallback["detailedSummary"]

    return {
        "threeLineSummary": lines[:3],
        "detailedSummary": trim_text(detailed_summary, 900),
    }


def summarize_article_with_ai(title: str, description: str, article_text: str):
    api_key = get_news_ai_api_key()

    if not api_key:
        return fallback_summary(
            title=title,
            description=description,
            article_text=article_text,
        )

    payload = {
        "model": get_news_ai_model(),
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "너는 외국인 유학생을 위한 뉴스 요약 도우미다. "
                            "뉴스를 정책, 생활정보, 행정절차 관점에서 간결하게 정리한다."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": build_news_summary_prompt(
                            title=title,
                            description=description,
                            article_text=article_text,
                        ),
                    }
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "news_summary",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "threeLineSummary": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {
                                "type": "string"
                            },
                        },
                        "detailedSummary": {
                            "type": "string"
                        },
                    },
                    "required": [
                        "threeLineSummary",
                        "detailedSummary",
                    ],
                },
            }
        },
        "max_output_tokens": 700,
    }

    request = Request(
        OPENAI_RESPONSES_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        print("NEWS AI HTTP ERROR:", error.code, error.reason)
        print(error_body)

        return fallback_summary(
            title=title,
            description=description,
            article_text=article_text,
        )
    except (URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
        print("NEWS AI ERROR:", error)

        return fallback_summary(
            title=title,
            description=description,
            article_text=article_text,
        )

    try:
        response_text = extract_openai_response_text(response_data)
        summary = parse_json_object(response_text)

        return normalize_summary_result(
            summary=summary,
            title=title,
            description=description,
            article_text=article_text,
        )
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        print("NEWS AI PARSE ERROR:", error)

        return fallback_summary(
            title=title,
            description=description,
            article_text=article_text,
        )


def build_news_item(raw_item: dict):
    title = clean_naver_text(raw_item.get("title", ""))
    description = clean_naver_text(raw_item.get("description", ""))
    link = raw_item.get("originallink") or raw_item.get("link") or ""

    article_text = fetch_article_text(link)

    summary = summarize_article_with_ai(
        title=title,
        description=description,
        article_text=article_text,
    )

    return {
        "title": title,
        "threeLineSummary": summary["threeLineSummary"],
        "detailedSummary": summary["detailedSummary"],
        "link": link,
    }


def collect_foreigner_news(total_limit: int = 4, display_per_keyword: int = 10):
    raw_items = []
    seen_links = set()

    for keyword in get_keywords():
        for raw_item in search_news(keyword, display=display_per_keyword):
            link = raw_item.get("originallink") or raw_item.get("link")

            if not link or link in seen_links:
                continue

            seen_links.add(link)
            raw_items.append(raw_item)

    filtered_items = [
        raw_item
        for raw_item in raw_items
        if calculate_relevance_score(raw_item) > 0
    ]

    if not filtered_items:
        filtered_items = [
            raw_item
            for raw_item in raw_items
            if not has_blocked_term(raw_item)
        ]

    filtered_items.sort(
        key=calculate_relevance_score,
        reverse=True,
    )

    return [
        build_news_item(raw_item)
        for raw_item in filtered_items[:total_limit]
    ]


def write_news_result(path: Path = NEWS_RESULT_PATH):
    result = {
        "news": collect_foreigner_news(),
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    return result