"""
services/card_generator.py
====================
STAGE D: retriever가 추천한 3개국 → 카드 3장 생성

사용 SDK: google-genai
사용 모델: gemini-2.5-flash

사용 예:
    from services.card_generator import generate_cards, load_countries_metadata

    metadata = load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")
    result = generate_cards(
        user_query="유아가 자연물을 오감으로 탐색하는 미술 활동",
        age=4,
        duration=40,
        top_countries=retriever_result["top_countries"],
        countries_metadata=metadata,
    )
    for card in result["cards"]:
        print(card["card_title"])
"""

import os
import json
import sys
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

SERVICES_DIR = Path(__file__).parent
BACKEND_ROOT = SERVICES_DIR.parent
sys.path.insert(0, str(BACKEND_ROOT))

from prompts.prompt_card_generator import COUNTRY_BLOCK_TEMPLATE


# ============================================================
# 설정
# ============================================================
load_dotenv(BACKEND_ROOT / ".env")
GEMINI_MODEL = "gemini-2.5-flash"

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 환경변수가 없습니다. backend/.env에 추가하세요."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ============================================================
# 3개국 정책 시스템 프롬프트 (오버라이드)
# ============================================================
SYSTEM_PROMPT_3COUNTRY = """\
당신은 유아교육 전문가이자 큐레이터입니다. 한국 유아교육과 학생이 입력한 수업 아이디어를 바탕으로,
주어진 3개 국가 각각에 대해 "수업 제안 카드"를 만들어주는 역할을 합니다.

### 당신의 작업

주어진 3개 국가 각각에 대해 카드를 1장씩 만듭니다. 총 3장의 카드를 출력합니다.

### 카드 작성 원칙

- **국가별 차별성 부각**: 같은 활동이라도 나라별 철학에 따라 다르게 풀어내야 합니다.
  · 핀란드 → 일상과 통합된 EduCare 톤
  · 이탈리아 → 100가지 언어와 문서화 톤
  · 스웨덴 → 위험 감수와 야외 자연 톤
  · 한국 → 누리과정 통합 운영 톤
  · 등 각 나라 고유 색깔 반영
- **자연스러운 한국어**: 외국 용어는 "원어(한국어)" 형식으로 병기 (예: "Regista(연출가)")
- **구체적**: 추상적인 "유아 중심" 대신 실제 활동 모습이 그려지는 표현
- **카드 간 차별점 명확**: 각 카드의 philosophy_tag가 서로 명확히 달라야 함
- **사용자 입력 반영**: card_title과 why_this_country에 사용자 활동 키워드가 자연스럽게 녹아야 함
- **점수 노출 금지**: 임베딩 점수, 순위 같은 시스템 정보는 카드에 표시하지 않음

### 출력 형식 (JSON)

반드시 아래 JSON 형식으로만 답하세요. 마크다운 코드블록 사용 금지, 순수 JSON만 출력.

{
  "selected_countries": ["국가코드1", "국가코드2", "국가코드3"],
  "cards": [
    {
      "country_code": "FIN",
      "country": "핀란드",
      "card_title": "이 카드의 활동을 한 줄로 표현 (12자 내외)",
      "card_subtitle": "이 나라 철학의 핵심 (15자 내외)",
      "philosophy_tag": "이 나라의 가장 강한 차별점 (8자 내외)",
      "key_approach": "이 나라 철학으로 활동을 풀어내는 핵심 접근 방식 2~3문장",
      "expected_experience": "유아가 이 활동에서 어떤 경험을 할지 2~3문장",
      "teacher_role": "교사가 이 활동에서 어떤 역할을 해야 하는지 1~2문장",
      "why_this_country": "사용자의 활동 의도와 이 나라가 왜 잘 맞는지 1~2문장"
    },
    ... (3장)
  ]
}
"""

USER_MESSAGE_TEMPLATE_3 = """\
[사용자 입력 활동]
{user_query}

[활동 정보]
- 대상 연령: 만 {age}세
- 활동 시간: {duration}분

[추천된 3개 국가 정보]
{country_candidates}

위 3개 국가 각각에 대해 수업 제안 카드를 1장씩, 총 3장을 JSON으로 생성해주세요.
"""


# ============================================================
# 프롬프트 빌더 (3개국 버전)
# ============================================================
def _build_prompt_3country(
    user_query: str,
    age: int,
    duration: int,
    top_countries: list,
    countries_metadata: dict,
) -> dict:
    country_blocks = []
    for rank, country in enumerate(top_countries, 1):
        code = country["country_code"]
        meta = countries_metadata.get(code, {})
        cp = meta.get("core_philosophy", {})

        diff_lines = []
        for d in cp.get("differentiators", [])[:3]:
            diff_lines.append(f"  · {d['name']}: {d['description'][:80]}...")
        differentiators_text = "\n".join(diff_lines) if diff_lines else "  (정보 없음)"

        chunk_lines = []
        for c in country.get("matched_chunks", [])[:3]:
            marker = "★" if c.get("is_core_philosophy") else " "
            chunk_lines.append(
                f"  [{marker}] {c['chunk_id']} ({c['category']})\n"
                f"      {c['chunk_text'][:120]}..."
            )
        chunks_text = "\n".join(chunk_lines) if chunk_lines else "  (매칭 청크 없음)"

        country_blocks.append(COUNTRY_BLOCK_TEMPLATE.format(
            rank=rank,
            country=country["country"],
            country_code=code,
            philosophy_summary=cp.get("philosophy_summary", "(요약 없음)"),
            identity_keywords=", ".join(cp.get("identity_keywords", [])[:6]),
            differentiators=differentiators_text,
            matched_chunks=chunks_text,
        ))

    user_message = USER_MESSAGE_TEMPLATE_3.format(
        user_query=user_query,
        age=age,
        duration=duration,
        country_candidates="\n".join(country_blocks),
    )

    return {"system": SYSTEM_PROMPT_3COUNTRY, "user": user_message}


# ============================================================
# 메인 함수
# ============================================================
def generate_cards(
    user_query: str,
    age: int,
    duration: int,
    top_countries: list,
    countries_metadata: dict,
) -> dict:
    """retriever 결과 top_countries (3개국) → 카드 3장 (JSON)."""
    if not top_countries:
        raise ValueError("top_countries가 비어있습니다. retriever 결과를 확인하세요.")

    prompt = _build_prompt_3country(
        user_query=user_query,
        age=age,
        duration=duration,
        top_countries=top_countries,
        countries_metadata=countries_metadata,
    )

    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt["user"]],
        config=types.GenerateContentConfig(
            system_instruction=prompt["system"],
            temperature=0.7,
            response_mime_type="application/json",
            max_output_tokens=4096,
        ),
    )

    return json.loads(_strip_code_fence(response.text))


# ============================================================
# 헬퍼
# ============================================================
def load_countries_metadata(all_countries_path: Path) -> dict:
    """all_countries.json → {국가코드: 국가데이터} dict"""
    with open(all_countries_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["country_code"]: c for c in data["countries"]}


# ============================================================
# 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    from services.retriever import Retriever

    retriever = Retriever()
    metadata = load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")

    test_queries = [
        ("유아가 자연물을 오감으로 탐색하는 미술 활동", 4, 40),
        ("교육과 돌봄을 통합한 일상 속 학습", 5, 50),
    ]

    print("=" * 70)
    print("card_generator.py 단독 테스트 (google-genai SDK)")
    print("=" * 70)

    for query, age, duration in test_queries:
        print(f"\n쿼리: {query}")
        retrieval = retriever.search(query, top_k_countries=3)
        print(f"  retriever 결과: {[c['country'] for c in retrieval['top_countries']]}")

        try:
            result = generate_cards(
                user_query=query,
                age=age,
                duration=duration,
                top_countries=retrieval["top_countries"],
                countries_metadata=metadata,
            )
            print(f"  ✓ 카드 {len(result['cards'])}장 생성\n")
            for card in result["cards"]:
                print(f"  ┌─ [{card['country_code']}] {card['country']} " + "─" * 40)
                print(f"  │ 제목      : {card['card_title']}")
                print(f"  │ 부제      : {card['card_subtitle']}")
                print(f"  │ 철학 태그 : {card['philosophy_tag']}")
                print(f"  │")
                print(f"  │ ▶ 핵심 접근 방식")
                print(f"  │   {card['key_approach']}")
                print(f"  │")
                print(f"  │ ▶ 유아의 기대 경험")
                print(f"  │   {card['expected_experience']}")
                print(f"  │")
                print(f"  │ ▶ 교사의 역할")
                print(f"  │   {card['teacher_role']}")
                print(f"  │")
                print(f"  │ ▶ 왜 이 나라인가?")
                print(f"  │   {card['why_this_country']}")
                print(f"  └" + "─" * 60 + "\n")
        except Exception as e:
            print(f"  ✗ 실패: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("✅ 테스트 완료")
    print("=" * 70)
