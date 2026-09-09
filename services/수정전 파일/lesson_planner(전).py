"""
services/lesson_planner.py
====================
STAGE F: 사용자가 선택한 1개 카드 → 완성된 지도안(Markdown) 생성

사용 모델: Gemini 2.0 Flash (Claude Haiku에서 변경)

사용 예:
    from services.lesson_planner import generate_lesson_plan

    md = generate_lesson_plan(
        user_query="유아가 자연물을 탐색하는 미술 활동",
        age=4,
        duration=40,
        selected_country_code="ITA",
        selected_card=cards[0],                     # card_generator 결과 중 1개
        country_chunks=retrieval_top["matched_chunks"],
        country_metadata=metadata["ITA"],
    )
    print(md)  # → 완성된 Markdown 지도안
"""

import os
import sys
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

SERVICES_DIR = Path(__file__).parent
BACKEND_ROOT = SERVICES_DIR.parent
sys.path.insert(0, str(BACKEND_ROOT))

from prompts.prompt_lesson_planner import build_prompt


# ============================================================
# 설정
# ============================================================
load_dotenv(BACKEND_ROOT / ".env")
GEMINI_MODEL = "gemini-2.0-flash-exp"
TEMPLATE_PATH = BACKEND_ROOT / "data" / "lesson_plan_template.md"

_model = None
_template_cache = None


def _get_model():
    global _model
    if _model is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 환경변수가 없습니다. backend/.env에 추가하세요."
            )
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(GEMINI_MODEL)
    return _model


def _load_template() -> str:
    """지도안 템플릿을 읽어 캐싱."""
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
    """LLM이 ``` 으로 감쌌을 때 제거 (Markdown 결과 보호)"""
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
    """
    선택된 카드 1장을 입력받아 완성된 지도안(Markdown 텍스트)을 반환.

    Args:
        user_query: 사용자 활동 의도 (search_query)
        age: 만 나이
        duration: 활동 시간(분)
        selected_country_code: 선택된 국가 코드 (예: "ITA")
        selected_card: card_generator 결과의 cards 중 사용자가 선택한 1장
        country_chunks: retriever 결과 중 해당 국가의 matched_chunks
        country_metadata: countries_metadata[selected_country_code]

    Returns:
        완성된 Markdown 지도안 텍스트
    """
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

    contents = [prompt["system"] + "\n\n" + prompt["user"]]

    model = _get_model()
    response = model.generate_content(
        contents,
        generation_config={
            "temperature": 0.6,
            "max_output_tokens": 4096,
            # Markdown 출력이므로 response_mime_type 지정하지 않음 (text/plain default)
        },
    )

    return _strip_code_fence(response.text)


# ============================================================
# 단독 실행 테스트 (전체 파이프라인 통합)
# ============================================================
if __name__ == "__main__":
    from retriever import Retriever
    from card_generator import generate_cards, load_countries_metadata

    print("=" * 70)
    print("lesson_planner.py 단독 테스트 (전체 파이프라인)")
    print("=" * 70)

    # 1. 사용자 입력
    user_query = "유아가 자연물을 오감으로 탐색하고 다양한 매체로 표현하는 활동"
    age = 4
    duration = 40

    # 2. retriever
    print("\n[1/3] retriever 검색 중...")
    retriever = Retriever()
    retrieval = retriever.search(user_query, top_k_countries=3)
    print(f"     top-3: {[c['country'] for c in retrieval['top_countries']]}")

    # 3. 카드 생성
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

    # 4. 첫 번째 카드를 사용자가 선택했다고 가정
    selected_card = cards_result["cards"][0]
    selected_code = selected_card["country_code"]
    print(f"\n[3/3] '{selected_card['country']}' 카드 선택 → 지도안 생성 중...")

    # 5. 해당 국가의 청크와 메타데이터 추출
    selected_country_data = next(
        c for c in retrieval["top_countries"] if c["country_code"] == selected_code
    )
    country_chunks = selected_country_data["matched_chunks"]
    country_meta = metadata[selected_code]

    # 6. 지도안 생성
    md = generate_lesson_plan(
        user_query=user_query,
        age=age,
        duration=duration,
        selected_country_code=selected_code,
        selected_card=selected_card,
        country_chunks=country_chunks,
        country_metadata=country_meta,
    )

    print("\n" + "=" * 70)
    print("생성된 지도안 (앞 1500자)")
    print("=" * 70)
    print(md[:1500])
    print("..." if len(md) > 1500 else "")

    # 파일로도 저장
    out = BACKEND_ROOT / "test_lesson_plan_output.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n✅ 전체 지도안이 {out} 에 저장되었습니다.")
