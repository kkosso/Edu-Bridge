"""
services/test_pipeline.py
====================
end-to-end 파이프라인 통합 테스트.

순서:
    텍스트(+이미지) → keyword_extractor → retriever → card_generator → lesson_planner

실행:
    cd backend
    python -m services.test_pipeline
"""

import sys
from pathlib import Path

SERVICES_DIR = Path(__file__).parent
BACKEND_ROOT = SERVICES_DIR.parent
sys.path.insert(0, str(BACKEND_ROOT))

from services.keyword_extractor import extract_keywords
from services.retriever import Retriever
from services.card_generator import generate_cards, load_countries_metadata
from services.lesson_planner import generate_lesson_plan


def run_pipeline(
    text: str,
    age: int,
    duration: int,
    image_path: str = None,
    auto_select_index: int = 0,
):
    print("=" * 70)
    print(f"입력: {text}")
    print(f"     연령={age}세, 시간={duration}분, 이미지={'있음' if image_path else '없음'}")
    print("=" * 70)

    # STAGE A
    print("\n[STAGE A] 키워드 추출 (Gemini)...")
    kw = extract_keywords(text=text, age=age, duration=duration, image_path=image_path)
    print(f"  ✓ 활동 유형: {kw.get('activity_type')}")
    print(f"  ✓ 키워드: {', '.join(kw.get('keywords', []))}")
    print(f"  ✓ search_query: {kw['search_query']}")

    # STAGE B-D
    print("\n[STAGE B-D] retriever 검색...")
    retriever = Retriever()
    retrieval = retriever.search(kw["search_query"], top_k_countries=3)
    for rank, c in enumerate(retrieval["top_countries"], 1):
        print(f"  [{rank}] {c['country']} (final={c['final_score']:.3f})")

    # STAGE E
    print("\n[STAGE E] 카드 3장 생성 (Gemini)...")
    metadata = load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")
    cards_result = generate_cards(
        user_query=kw["search_query"],
        age=age,
        duration=duration,
        top_countries=retrieval["top_countries"],
        countries_metadata=metadata,
    )
    for i, card in enumerate(cards_result["cards"]):
        marker = "👉" if i == auto_select_index else "  "
        print(f"  {marker} [{card['country_code']}] {card['card_title']}")
        print(f"           ({card['philosophy_tag']}) {card['card_subtitle']}")

    # STAGE F
    selected_card = cards_result["cards"][auto_select_index]
    selected_code = selected_card["country_code"]
    print(f"\n[STAGE F] '{selected_card['country']}' 카드로 지도안 생성 (Gemini)...")

    selected_country_data = next(
        c for c in retrieval["top_countries"] if c["country_code"] == selected_code
    )
    md = generate_lesson_plan(
        user_query=kw["search_query"],
        age=age,
        duration=duration,
        selected_country_code=selected_code,
        selected_card=selected_card,
        country_chunks=selected_country_data["matched_chunks"],
        country_metadata=metadata[selected_code],
    )

    out_path = BACKEND_ROOT / f"test_output_{selected_code}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"  ✓ 지도안 길이: {len(md)}자")
    print(f"  ✓ 저장: {out_path}")

    return {
        "keywords": kw,
        "retrieval": retrieval,
        "cards": cards_result,
        "selected_card": selected_card,
        "lesson_plan": md,
    }


if __name__ == "__main__":
    test_cases = [
        ("솔방울이랑 나뭇잎 모아왔는데 아이들이 만지고 그림 그리는 활동 하고 싶어요", 4, 40),
    ]

    for text, age, duration in test_cases:
        run_pipeline(text=text, age=age, duration=duration)
        print("\n" + "=" * 70 + "\n")

    print("✅ end-to-end 파이프라인 테스트 완료")
