import json
import logging
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
NEWS_RESULT_PATH = BASE_DIR / "news_result.json"

NAVER_NEWS_API_URL = (
    "https://naverapihub.apigw.ntruss.com"
    "/search/v1/news"
)

GEMINI_API_BASE_URL = (
    "https://generativelanguage.googleapis.com"
    "/v1beta/models"
)

GEMINI_MODEL = "gemini-3.5-flash"

NEWS_LIMIT = 4
ARTICLE_TEXT_LIMIT = 20000

DEFAULT_KEYWORDS = [
    "외국인",
    "이주민",
    "유학생",
    "외국인 노동자",
    "다문화",
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {
            "script",
            "style",
            "noscript",
        }:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if (
            tag in {
                "script",
                "style",
                "noscript",
            }
            and self._skip_depth
        ):
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return

        text = data.strip()

        if text:
            self.parts.append(text)

    def get_text(self):
        return normalize_text(
            " ".join(self.parts)
        )


def empty_summary():
    return {
        "threeLineSummary": [],
        "detailedSummary": "",
    }


def normalize_text(value: str):
    return re.sub(
        r"\s+",
        " ",
        unescape(value or ""),
    ).strip()


def clean_naver_text(value: str):
    return normalize_text(
        re.sub(r"</?b>", "", value or "")
    )


def get_keywords():
    raw_keywords = os.getenv(
        "NAVER_NEWS_KEYWORDS"
    )

    if not raw_keywords:
        return DEFAULT_KEYWORDS

    keywords = [
        keyword.strip()
        for keyword in raw_keywords.split(",")
        if keyword.strip()
    ]

    return keywords or DEFAULT_KEYWORDS


def request_naver_json(url: str):
    client_id = os.getenv(
        "NAVER_CLIENT_ID"
    )

    client_secret = os.getenv(
        "NAVER_CLIENT_SECRET"
    )

    if not client_id or not client_secret:
        return None

    request = Request(
        url,
        headers={
            "X-NCP-APIGW-API-KEY-ID": (
                client_id
            ),
            "X-NCP-APIGW-API-KEY": (
                client_secret
            ),
        },
    )

    with urlopen(
        request,
        timeout=10,
    ) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def search_news(
    keyword: str,
    display: int = NEWS_LIMIT,
):
    query = quote(keyword)

    url = (
        f"{NAVER_NEWS_API_URL}"
        f"?query={query}"
        f"&display={display}"
        f"&start=1"
        f"&sort=date"
        f"&format=json"
    )

    try:
        data = request_naver_json(url)

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="ignore",
        )

        logger.warning(
            "NAVER 뉴스 API 호출 실패: %s %s",
            error.code,
            error_body[:500],
        )

        return []

    except (
        URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as error:
        logger.warning(
            "NAVER 뉴스 API 호출 실패: %s",
            error,
        )

        return []

    if not data:
        return []

    return data.get("items", [])


def get_published_at(raw_item: dict):
    pub_date = raw_item.get(
        "pubDate",
        "",
    )

    try:
        return parsedate_to_datetime(pub_date)

    except (TypeError, ValueError):
        return datetime.min.replace(
            tzinfo=timezone.utc
        )


def fetch_article_text(url: str):
    if not url:
        return ""

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    )

    try:
        with urlopen(
            request,
            timeout=10,
        ) as response:
            encoding = (
                response.headers
                .get_content_charset()
                or "utf-8"
            )

            html = response.read().decode(
                encoding,
                errors="ignore",
            )

    except (
        HTTPError,
        URLError,
        TimeoutError,
        UnicodeDecodeError,
    ) as error:
        logger.warning(
            "기사 본문 추출 실패: %s",
            error,
        )

        return ""

    parser = TextExtractor()
    parser.feed(html)

    return parser.get_text()


def build_gemini_prompt(
    title: str,
    description: str,
    article_text: str,
):
    article_source = (
        article_text[:ARTICLE_TEXT_LIMIT]
        if article_text
        else description
    )

    return f"""
다음 뉴스 기사를 한국어로 요약해 주세요.

반드시 제공된 기사 정보만 사용하세요.
기사에 없는 사실을 추측하거나 추가하지 마세요.
광고, 메뉴, 언론사 소개, 저작권 문구 등
기사 본문과 관계없는 내용은 제외하세요.

세 줄 요약 작성 규칙:
- 정확히 3개의 문장으로 작성하세요.
- 각 문장은 독립적으로 이해할 수 있어야 합니다.
- 기사의 핵심 사실, 주요 변화, 영향을 중심으로 작성하세요.
- 서로 같은 내용을 반복하지 마세요.

상세 요약 작성 규칙:
- 5문장 이상 8문장 이하로 작성하세요.
- 사건의 배경, 핵심 내용, 관련 대상, 영향을 설명하세요.
- 기사에서 확인되지 않는 의견이나 전망은 만들지 마세요.
- 하나의 문자열로 작성하세요.

기사 제목:
{title}

NAVER 검색 설명:
{description}

추출한 기사 본문:
{article_source}
""".strip()


def extract_gemini_response_text(
    response_data: dict,
):
    candidates = response_data.get(
        "candidates",
        [],
    )

    if not candidates:
        return ""

    content = candidates[0].get(
        "content",
        {},
    )

    parts = content.get(
        "parts",
        [],
    )

    text_parts = [
        part.get("text", "")
        for part in parts
        if (
            isinstance(
                part.get("text"),
                str,
            )
            and not part.get(
                "thought",
                False,
            )
        )
    ]

    return "".join(text_parts).strip()


def parse_gemini_summary(
    response_text: str,
):
    if not response_text:
        return empty_summary()

    cleaned_text = response_text.strip()

    if cleaned_text.startswith("```"):
        cleaned_text = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        )

        cleaned_text = re.sub(
            r"\s*```$",
            "",
            cleaned_text,
        )

    try:
        summary = json.loads(cleaned_text)

    except json.JSONDecodeError:
        logger.warning(
            "Gemini 응답을 JSON으로 변환하지 못했습니다."
        )

        return empty_summary()

    three_line_summary = summary.get(
        "threeLineSummary",
        [],
    )

    detailed_summary = summary.get(
        "detailedSummary",
        "",
    )

    if not isinstance(
        three_line_summary,
        list,
    ):
        return empty_summary()

    normalized_lines = [
        normalize_text(line)
        for line in three_line_summary
        if (
            isinstance(line, str)
            and normalize_text(line)
        )
    ]

    if len(normalized_lines) != 3:
        logger.warning(
            "Gemini 세 줄 요약이 정확히 "
            "3개가 아닙니다."
        )

        return empty_summary()

    if not isinstance(
        detailed_summary,
        str,
    ):
        return empty_summary()

    detailed_summary = normalize_text(
        detailed_summary
    )

    if not detailed_summary:
        return empty_summary()

    return {
        "threeLineSummary": normalized_lines,
        "detailedSummary": detailed_summary,
    }


def summarize_article_with_gemini(
    title: str,
    description: str,
    article_text: str,
):
    news_ai_api_key = os.getenv(
        "NEWS_AI_API_KEY"
    )

    if not news_ai_api_key:
        logger.warning(
            "NEWS_AI_API_KEY가 설정되지 않았습니다."
        )

        return empty_summary()

    if not article_text and not description:
        return empty_summary()

    model = os.getenv(
        "NEWS_AI_MODEL",
        GEMINI_MODEL,
    )

    encoded_model = quote(
        model,
        safe="",
    )

    url = (
        f"{GEMINI_API_BASE_URL}"
        f"/{encoded_model}:generateContent"
    )

    prompt = build_gemini_prompt(
        title=title,
        description=description,
        article_text=article_text,
    )

    response_schema = {
        "type": "object",
        "properties": {
            "threeLineSummary": {
                "type": "array",
                "description": (
                    "기사의 핵심 내용을 요약한 "
                    "정확히 3개의 한국어 문장"
                ),
                "items": {
                    "type": "string",
                },
                "minItems": 3,
                "maxItems": 3,
            },
            "detailedSummary": {
                "type": "string",
                "description": (
                    "기사의 배경, 핵심 내용, "
                    "관련 대상과 영향을 포함한 "
                    "5~8문장의 한국어 상세 요약"
                ),
            },
        },
        "required": [
            "threeLineSummary",
            "detailedSummary",
        ],
        "additionalProperties": False,
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
            "thinkingConfig": {
                "thinkingLevel": "low",
            },
            "responseFormat": {
                "text": {
                    "mimeType": (
                        "APPLICATION_JSON"
                    ),
                    "schema": (
                        response_schema
                    ),
                }
            },
        },
    }

    request = Request(
        url,
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type": (
                "application/json"
            ),
            "x-goog-api-key": (
                news_ai_api_key
            ),
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=45,
        ) as response:
            response_data = json.loads(
                response
                .read()
                .decode("utf-8")
            )

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="ignore",
        )

        logger.warning(
            "Gemini API 호출 실패: %s %s",
            error.code,
            error_body[:500],
        )

        return empty_summary()

    except (
        URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as error:
        logger.warning(
            "Gemini API 호출 실패: %s",
            error,
        )

        return empty_summary()

    response_text = (
        extract_gemini_response_text(
            response_data
        )
    )

    return parse_gemini_summary(
        response_text
    )


def build_news_item(raw_item: dict):
    title = clean_naver_text(
        raw_item.get(
            "title",
            "",
        )
    )

    description = clean_naver_text(
        raw_item.get(
            "description",
            "",
        )
    )

    link = (
        raw_item.get("originallink")
        or raw_item.get("link")
        or ""
    )

    article_text = fetch_article_text(link)

    summary = summarize_article_with_gemini(
        title=title,
        description=description,
        article_text=article_text,
    )

    return {
        "title": title,
        "threeLineSummary": (
            summary["threeLineSummary"]
        ),
        "detailedSummary": (
            summary["detailedSummary"]
        ),
        "link": link,
    }


def collect_foreigner_news(
    total_limit: int = NEWS_LIMIT,
    display_per_keyword: int = NEWS_LIMIT,
):
    raw_news_items = []
    seen_links = set()

    for keyword in get_keywords():
        news_list = search_news(
            keyword,
            display=display_per_keyword,
        )

        for raw_item in news_list:
            link = (
                raw_item.get("originallink")
                or raw_item.get("link")
            )

            if (
                not link
                or link in seen_links
            ):
                continue

            seen_links.add(link)
            raw_news_items.append(
                raw_item
            )

    raw_news_items.sort(
        key=get_published_at,
        reverse=True,
    )

    latest_news = raw_news_items[
        :total_limit
    ]

    return [
        build_news_item(raw_item)
        for raw_item in latest_news
    ]


def write_news_result(
    path: Path = NEWS_RESULT_PATH,
):
    result = {
        "news": collect_foreigner_news(),
    }

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return result