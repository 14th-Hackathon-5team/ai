import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
    "유학생 비자",
    "유학생 체류",
    "유학생 외국인등록",
    "외국인 유학생 지원",
    "외국인 유학생 장학금",
    "유학생 아르바이트",
    "유학생 시간제 취업",
    "유학생 취업",
    "유학생 건강보험",
    "유학생 의료 지원",
    "유학생 주거 지원",
    "TOPIK 한국어 교육",
    "외국인 유학생 입학 모집",
    "어학연수생 지원",
]

INCLUDE_TERMS = [
    "유학생",
    "외국인 유학생",
    "어학연수",
    "어학연수생",
    "D-2",
    "D2",
    "D-4",
    "D4",
]

USEFUL_TERMS = [
    "비자",
    "체류",
    "연장",
    "외국인등록",
    "등록증",
    "법률",
    "행정",
    "입학",
    "모집",
    "원서",
    "TOPIK",
    "한국어",
    "아르바이트",
    "시간제",
    "취업",
    "장학금",
    "지원",
    "정책",
    "건강보험",
    "의료",
    "생활",
    "주거",
    "기숙사",
    "프로그램",
    "행사",
    "상담",
    "정착",
]

BLOCKED_TERMS = [
    "환율",
    "주식",
    "투자",
    "대출",
    "카드",
    "송금",
    "금융",
    "은행",
    "결제",
    "핀테크",
    "플랫폼",
    "프로모션",
    "할인",
    "출시",
    "상품",
    "광고",
    "협찬",
    "외국인투자",
    "외국인 투자",
    "외국인 매수",
    "외국인 매도",
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
    "연예",
    "스포츠",
    "외국인 선수",
    "외국인 감독",
    "관광객",
]

ALLOWED_PUBLIC_HEALTH_TERMS = [
    "건강보험",
    "국민건강보험",
    "의료 지원",
    "외국인 의료",
]

OVERSEAS_ONLY_TERMS = [
    "미국 유학생",
    "중국 유학생",
    "일본 유학생",
    "영국 유학생",
    "호주 유학생",
    "캐나다 유학생",
    "해외 유학생",
    "한국인 유학생",
]

STATS_ONLY_TERMS = [
    "통계",
    "집계",
    "증가",
    "감소",
    "돌파",
    "명 넘어",
    "비중",
]

DUPLICATE_EVENT_TERMS = [
    "K-TECH Bridge",
    "K-TECH Bridge Program",
    "공동운영 협약",
    "주문식 교육과정",
    "Study Korea 300K",
    "외국인 유학생 30만명",
    "일자리 종합박람회",
    "유학생지원센터",
]

DUPLICATE_STOPWORDS = {
    "외국인",
    "유학생",
    "지원",
    "교육",
    "대학",
    "관련",
    "위한",
    "통해",
    "이번",
    "최근",
    "진행",
    "운영",
    "사업",
}

MIN_ARTICLE_TEXT_LENGTH = 180


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "header", "footer", "nav"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if (
            tag in {"script", "style", "noscript", "header", "footer", "nav"}
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


def has_any_term(text: str, terms: list[str]):
    return any(term in text for term in terms)


def has_ellipsis(text: str):
    return "..." in text or "…" in text


def normalize_title(title: str):
    title = clean_naver_text(title)
    title = title.strip("\"'“”‘’ ")

    return title


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


def search_news(keyword: str, display: int = 20):
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
        with urlopen(request, timeout=8) as response:
            content_type = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(content_type, errors="ignore")
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError):
        return ""

    parser = TextExtractor()
    parser.feed(html)

    return parser.get_text()


def get_searchable_text(raw_item: dict, article_text: str = ""):
    title = clean_naver_text(raw_item.get("title", ""))
    description = clean_naver_text(raw_item.get("description", ""))

    return f"{title} {description} {article_text}"


def get_published_datetime(raw_item: dict):
    pub_date = raw_item.get("pubDate", "")

    if not pub_date:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        value = parsedate_to_datetime(pub_date)

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def is_article_text_valid(article_text: str):
    article_text = normalize_text(article_text)

    if len(article_text) < MIN_ARTICLE_TEXT_LENGTH:
        return False

    invalid_markers = [
        "404",
        "페이지를 찾을 수 없습니다",
        "접근이 제한",
        "서비스 이용에 불편",
        "로그인",
        "구독",
    ]

    return not has_any_term(article_text, invalid_markers)


def is_finance_or_ad_news(text: str):
    if has_any_term(text, ALLOWED_PUBLIC_HEALTH_TERMS):
        return False

    return has_any_term(text, BLOCKED_TERMS)


def is_overseas_only_news(text: str):
    if "한국" in text or "국내" in text or "법무부" in text or "교육부" in text:
        return False

    return has_any_term(text, OVERSEAS_ONLY_TERMS)


def is_stats_only_news(text: str):
    has_student_context = has_any_term(text, INCLUDE_TERMS)
    has_useful_context = has_any_term(text, USEFUL_TERMS)
    has_stats_context = has_any_term(text, STATS_ONLY_TERMS)

    return has_student_context and has_stats_context and not has_useful_context


def is_relevant_news(raw_item: dict, article_text: str):
    text = get_searchable_text(raw_item, article_text)

    if not has_any_term(text, INCLUDE_TERMS):
        return False

    if not has_any_term(text, USEFUL_TERMS):
        return False

    if is_finance_or_ad_news(text):
        return False

    if is_overseas_only_news(text):
        return False

    if is_stats_only_news(text):
        return False

    return True


def calculate_relevance_score(raw_item: dict, article_text: str):
    text = get_searchable_text(raw_item, article_text)
    score = 0

    for term in INCLUDE_TERMS:
        if term in text:
            score += 5

    for term in USEFUL_TERMS:
        if term in text:
            score += 3

    return score


def normalize_duplicate_text(text: str):
    text = clean_naver_text(text).lower()
    text = re.sub(r"[^0-9a-zA-Z가-힣\s]", " ", text)

    return {
        token
        for token in text.split()
        if len(token) >= 2
        and token not in DUPLICATE_STOPWORDS
    }


def get_duplicate_tokens(item: dict):
    return normalize_duplicate_text(
        f"{item['title']} {item['description']} {item['articleText'][:1000]}"
    )


def has_same_event_term(left_item: dict, right_item: dict):
    left_text = (
        f"{left_item['title']} {left_item['description']} {left_item['articleText']}"
        .lower()
    )
    right_text = (
        f"{right_item['title']} {right_item['description']} {right_item['articleText']}"
        .lower()
    )

    for term in DUPLICATE_EVENT_TERMS:
        normalized_term = term.lower()

        if (
            normalized_term in left_text
            and normalized_term in right_text
        ):
            return True

    return False


def is_duplicate_news(left_item: dict, right_item: dict):
    if has_same_event_term(left_item, right_item):
        return True

    left_tokens = get_duplicate_tokens(left_item)
    right_tokens = get_duplicate_tokens(right_item)

    if not left_tokens or not right_tokens:
        return False

    overlap_count = len(left_tokens & right_tokens)
    smaller_size = min(len(left_tokens), len(right_tokens))

    return (
        overlap_count >= 5
        and overlap_count / smaller_size >= 0.45
    )


def remove_duplicate_news(items: list[dict]):
    unique_items = []

    for item in items:
        if any(
            is_duplicate_news(item, unique_item)
            for unique_item in unique_items
        ):
            continue

        unique_items.append(item)

    return unique_items


def split_sentences(text: str):
    text = normalize_text(text)

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?。])\s+|(?<=다\.)\s*|(?<=습니다\.)\s*",
        text,
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def get_news_ai_api_key():
    return os.getenv("NEWS_AI_API_KEY", "").strip()


def get_news_ai_model():
    return os.getenv("NEWS_AI_MODEL", "gpt-5.6-luna").strip()


def build_news_summary_prompt(title: str, description: str, article_text: str):
    article_text = trim_text(article_text, 6000)

    return f"""
아래 뉴스 자료를 외국인 유학생에게 도움이 되는 정보 중심으로 정리해줘.

작성 규칙:
- 반드시 한국어로 작성한다.
- 출력은 JSON 객체 하나만 반환한다.
- title은 기사 내용을 자연스럽게 대표하는 제목으로 작성한다.
- 원문 제목이 말줄임표로 잘렸으면 기사 내용과 네이버 요약을 바탕으로 완성된 제목으로 정리한다.
- title은 45자 이내로 작성한다.
- threeLineSummary는 정확히 3개의 문자열 배열로 작성한다.
- threeLineSummary 각 문장은 45자 이내로 짧게 작성한다.
- threeLineSummary와 detailedSummary의 모든 문장은 존댓말로 작성한다.
- 문장 끝은 "~습니다.", "~합니다.", "~됩니다.", "~입니다." 형태로 통일한다.
- "~다.", "~됐다.", "~있다." 같은 평서체 종결은 사용하지 않는다.
- detailedSummary는 3~5문장으로 작성한다.
- 외국인 유학생이 실제로 알아야 할 비자, 체류, 외국인등록, 법률, 행정, 입학, TOPIK, 한국어교육, 아르바이트, 취업, 장학금, 건강보험, 의료, 주거, 생활 정보만 요약한다.
- 기사에 없는 내용은 절대 추측하지 않는다.
- 기사에서 확인되지 않는 내용은 "기사에서 구체적으로 확인되지 않습니다."라고 표시한다.
- 사건사고, 금융, 광고성 내용은 강조하지 않는다.
- 기관명, 날짜, 신청 대상, 제도명, 참여 방법이 있으면 detailedSummary에 포함한다.

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


def validate_summary_result(summary: dict):
    title = normalize_title(str(summary.get("title", "")))
    lines = summary.get("threeLineSummary", [])
    detailed_summary = normalize_text(str(summary.get("detailedSummary", "")))

    if not title:
        return None

    if not isinstance(lines, list) or len(lines) != 3:
        return None

    clean_lines = [
        trim_text(str(line), 70)
        for line in lines
        if normalize_text(str(line))
    ]

    if len(clean_lines) != 3:
        return None

    if not detailed_summary:
        return None

    return {
        "title": trim_text(title, 45),
        "threeLineSummary": clean_lines,
        "detailedSummary": trim_text(detailed_summary, 900),
    }


def summarize_article_with_ai(title: str, description: str, article_text: str):
    api_key = get_news_ai_api_key()

    if not api_key:
        return None

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
                            "기사에 없는 내용은 추측하지 않고, 존댓말로만 요약한다."
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
                        "title": {
                            "type": "string"
                        },
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
                        "title",
                        "threeLineSummary",
                        "detailedSummary",
                    ],
                },
            }
        },
        "max_output_tokens": 800,
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
        return None
    except (URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
        print("NEWS AI ERROR:", error)
        return None

    try:
        response_text = extract_openai_response_text(response_data)
        summary = parse_json_object(response_text)

        return validate_summary_result(summary)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        print("NEWS AI PARSE ERROR:", error)
        return None


def prepare_news_candidate(raw_item: dict):
    title = clean_naver_text(raw_item.get("title", ""))
    description = clean_naver_text(raw_item.get("description", ""))
    link = raw_item.get("originallink") or raw_item.get("link") or ""

    if not link:
        return None

    article_text = fetch_article_text(link)

    if not is_article_text_valid(article_text):
        return None

    if not is_relevant_news(raw_item, article_text):
        return None

    return {
        "title": title,
        "description": description,
        "link": link,
        "articleText": article_text,
        "publishedAt": get_published_datetime(raw_item),
        "score": calculate_relevance_score(raw_item, article_text),
    }


def build_news_item(candidate: dict):
    summary = summarize_article_with_ai(
        title=candidate["title"],
        description=candidate["description"],
        article_text=candidate["articleText"],
    )

    if not summary:
        return None

    return {
        "title": summary["title"],
        "threeLineSummary": summary["threeLineSummary"],
        "detailedSummary": summary["detailedSummary"],
        "link": candidate["link"],
    }


def collect_foreigner_news(total_limit: int = 4, display_per_keyword: int = 20):
    candidates = []
    seen_links = set()

    for keyword in get_keywords():
        for raw_item in search_news(keyword, display=display_per_keyword):
            link = raw_item.get("originallink") or raw_item.get("link")

            if not link or link in seen_links:
                continue

            seen_links.add(link)

            candidate = prepare_news_candidate(raw_item)

            if candidate:
                candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            item["publishedAt"],
            item["score"],
        ),
        reverse=True,
    )

    unique_candidates = remove_duplicate_news(candidates)

    news_items = []

    for candidate in unique_candidates:
        news_item = build_news_item(candidate)

        if not news_item:
            continue

        news_items.append(news_item)

        if len(news_items) >= total_limit:
            break

    return news_items


def write_news_result(path: Path = NEWS_RESULT_PATH):
    result = {
        "news": collect_foreigner_news(),
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    return result