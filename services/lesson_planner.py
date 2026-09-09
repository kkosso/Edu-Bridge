"""
services/lesson_planner.py
====================
STAGE F: 사용자가 선택한 1개 카드 → 완성된 지도안(Markdown) 생성

사용 SDK: google-genai
사용 모델: gemini-2.5-flash

사용 예:
    from services.lesson_planner import generate_lesson_plan

    md = generate_lesson_plan(
        user_query="유아가 자연물을 탐색하는 미술 활동",
        age=4,
        duration=40,
        selected_country_code="ITA",
        selected_card=cards[0],
        country_chunks=retrieval_top["matched_chunks"],
        country_metadata=metadata["ITA"],
    )
"""

import os
import sys
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

SERVICES_DIR = Path(__file__).parent
BACKEND_ROOT = SERVICES_DIR.parent
sys.path.insert(0, str(BACKEND_ROOT))

from prompts.prompt_lesson_planner import build_prompt


# ============================================================
# 설정
# ============================================================
load_dotenv(BACKEND_ROOT / ".env")
GEMINI_MODEL = "gemini-2.5-flash"
TEMPLATE_PATH = BACKEND_ROOT / "data" / "lesson_plan_template.md"

_client = None
_template_cache = None


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


def _load_template() -> str:
    global _template_cache
    if _template_cache is None:
        if not TEMPLATE_PATH.exists():
            raise FileNotFoundError(
                f"지도안 템플릿이 없습니다: {TEMPLATE_PATH}\n"
                f"data/lesson_plan_template.md 파일을 배치하세요."
            )
        _template_cache = TEMPLATE_PATH.read_text(encoding="utf-8")
    return _template_cache


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```markdown"):
        text = text[11:]
    elif text.startswith("```md"):
        text = text[5:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ============================================================
# 메인 함수
# ============================================================
def generate_lesson_plan(
    user_query: str,
    age: int,
    duration: int,
    selected_country_code: str,
    selected_card: dict,
    country_chunks: list,
    country_metadata: dict,
) -> str:
    """선택된 카드 1장 → 완성된 Markdown 지도안 텍스트."""
    template = _load_template()

    prompt = build_prompt(
        user_query=user_query,
        age=age,
        duration=duration,
        selected_country_code=selected_country_code,
        selected_card=selected_card,
        country_chunks=country_chunks,
        country_metadata=country_metadata,
        lesson_plan_template=template,
    )

    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt["user"]],
        config=types.GenerateContentConfig(
            system_instruction=prompt["system"],
            temperature=0.6,
            max_output_tokens=8192,
            # Markdown 출력이라 response_mime_type 지정 X
        ),
    )

    return _strip_code_fence(response.text)


# ============================================================
# 단독 실행 테스트 (전체 파이프라인 통합)
# ============================================================
if __name__ == "__main__":
    from services.retriever import Retriever
    from services.card_generator import generate_cards, load_countries_metadata

    print("=" * 70)
    print("lesson_planner.py 단독 테스트 (전체 파이프라인)")
    print("=" * 70)

    user_query = "유아가 자연물을 오감으로 탐색하고 다양한 매체로 표현하는 활동"
    age = 4
    duration = 40

    print("\n[1/3] retriever 검색 중...")
    retriever = Retriever()
    retrieval = retriever.search(user_query, top_k_countries=3)
    print(f"     top-3: {[c['country'] for c in retrieval['top_countries']]}")

    print("\n[2/3] 카드 3장 생성 중...")
    metadata = load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")
    cards_result = generate_cards(
        user_query=user_query,
        age=age,
        duration=duration,
        top_countries=retrieval["top_countries"],
        countries_metadata=metadata,
    )
    for card in cards_result["cards"]:
        print(f"     [{card['country_code']}] {card['card_title']}")

    selected_card = cards_result["cards"][0]
    selected_code = selected_card["country_code"]
    print(f"\n[3/3] '{selected_card['country']}' 카드 선택 → 지도안 생성 중...")

    selected_country_data = next(
        c for c in retrieval["top_countries"] if c["country_code"] == selected_code
    )
    md = generate_lesson_plan(
        user_query=user_query,
        age=age,
        duration=duration,
        selected_country_code=selected_code,
        selected_card=selected_card,
        country_chunks=selected_country_data["matched_chunks"],
        country_metadata=metadata[selected_code],
    )

    print("\n" + "=" * 70)
    print("생성된 지도안 (앞 1500자)")
    print("=" * 70)
    print(md[:1500])
    print("..." if len(md) > 1500 else "")

    out = BACKEND_ROOT / "test_lesson_plan_output.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n✅ 전체 지도안이 {out} 에 저장되었습니다.")
