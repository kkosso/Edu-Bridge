"""
services/card_generator.py
====================
STAGE D: retriever가 추천한 3개국 → 카드 3장 생성

사용 SDK: google-genai
사용 모델: gemini-2.5-flash

【v3 개선점】
- v2: "시나리오를 구체적으로" 강제 → 통과했지만 카드끼리 비슷해지는 문제 발생
- v3: "활동 형식(format) 자체를 다르게" 강제. 단순 분위기 변주가 아니라
       활동의 종류(미션/게임/회의/실험/이야기)부터 다르게 만들도록 지시.
"""

import os
import json
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types
from google.genai.errors import ServerError
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
MAX_RETRIES = 3
RETRY_DELAY_SEC = 4

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
# 시스템 프롬프트 (v3 - 활동 형식 차별화 강제)
# ============================================================
SYSTEM_PROMPT_3COUNTRY = """\
당신은 유아교육 전문가이자 큐레이터입니다. 한국 유아교육과 학생이 입력한 수업 아이디어를 바탕으로,
주어진 3개 국가 각각에 대해 "수업 제안 카드"를 만들어주는 역할을 합니다.

### 작업 규칙

주어진 3개 국가 각각에 대해 카드를 1장씩, 총 3장을 생성합니다.

### 가장 중요한 원칙 ① — "수업이 머릿속에 그려져야 한다"

추상적인 철학 설명만 늘어놓는 카드는 낙제입니다. 교사가 카드만 읽고도
"아, 이 활동을 어떻게 진행하면 되겠구나"가 떠올라야 합니다.

### 가장 중요한 원칙 ② — "3장의 카드는 활동 형식(format)부터 달라야 한다" ⭐⭐⭐

같은 재료(예: 종이컵)에 대해서도 3개국이 추천된다면, 3장의 카드는 단순히 분위기만 다른 게 아니라
**"무엇을 하는 활동인가"의 종류 자체가 달라야 합니다.**

❌ 절대 금지 (분위기만 변주된 사례):
   - 카드1: "자유롭게 쌓고 무너지면 토의"
   - 카드2: "차분하게 쌓고 무너지면 다시 시도"
   - 카드3: "민주적으로 쌓고 무너지면 회의"
   → 셋 다 본질은 "쌓고 무너지면 이야기"라서 안 됨.

⭕ 반드시 이렇게 (활동 형식이 다른 사례):
   - 카드1: 수학 미션 (패턴 카드 매칭, AB·ABC 패턴 만들기 챌린지)
   - 카드2: 야외 신체 게임 (릴레이로 누가 더 높이 쌓는지 팀 대결)
   - 카드3: 학급 토론 프로젝트 (다 쓴 종이컵 어떻게 재활용할지 회의 → 결정 → 실행)
   → 활동 종류, 공간, 인원 구성, 결과물이 모두 다름.

### 활동 형식의 카탈로그 — 카드마다 다른 형식을 골라 쓰세요

가능한 형식 종류:
- **수학적 발견 미션**: 패턴/개수/도형/측정 같은 수학 개념 발견
- **신체/협동 게임**: 릴레이, 팀 대결, 함께 큰 구조 만들기
- **재료 변환 프로젝트**: 한 재료를 다른 용도로 변환·재사용
- **학급 회의/토론**: 의견 모으기, 투표, 합의, 실행
- **다매체 표현 활동**: 그리기·찰흙·그림자·사진 등 여러 매체로 같은 대상 표현
- **이야기/극놀이**: 재료를 등장인물·소품 삼아 즉흥 극
- **자연·야외 통합**: 실외에서 자연물과 결합
- **돌봄·일상 통합**: 간식·정리정돈 같은 일상에 활동을 녹이기
- **관찰·기록 프로젝트**: 시간을 두고 변화 관찰, 사진/그림으로 기록

3개국 중 1나라는 어떤 형식이 가장 잘 맞는지를 그 나라 철학에서 도출하세요.

### 국가별 철학과 잘 맞는 활동 형식 가이드 (참고)

  · 싱가포르(SGP) → 수학적 발견 미션 / 인지 영역 챌린지 (수리력 강조)
  · 영국(GBR) → 신체/협동 게임 또는 EYFS Prime/Specific 영역 균형 활동
  · 독일(GER) → 학급 회의·토론, 재활용·환경 프로젝트 (민주적 참여)
  · 이탈리아(ITA) → 다매체 표현 활동 / 그림자·빛·찰흙으로 같은 주제 표현
  · 핀란드(FIN) → 돌봄·일상 통합 / 자연·야외 / 페다고지 문서화
  · 스웨덴(SWE) → 자연·야외 통합 / 위험 감수 자유 실험
  · 일본(JPN) → 정돈된 환경에서 마음 정돈, 친구와 차분한 협력
  · 한국(KOR) → 누리과정 5개 영역 통합한 자유놀이
  · 호주(AUS) → 원주민·Country 관점, 야외 자연 결합
  · 뉴질랜드(NZL) → 이야기/극놀이, Whāriki 짜기 메타포의 협동 구조

### 카드 작성 원칙

- **자연스러운 한국어**: 외국 용어는 "원어(한국어)" 형식 (예: "Regista(연출가)")
- **활동 단계가 명확하게**: 도입/전개/마무리 흐름이 자연스럽게 보여야 함
- **카드 간 차별점 명확**: 각 카드의 활동 종류·공간·결과물이 명백히 달라야 함
- **사용자 입력 키워드 반영**: 사용자가 입력한 단어가 카드에 자연스럽게 등장
- **점수 노출 금지**: 임베딩 점수, 순위 같은 시스템 정보 X

### 출력 형식 (JSON)

반드시 아래 JSON 형식으로만 답하세요. 마크다운 코드블록 사용 금지, 순수 JSON만 출력.

{
  "selected_countries": ["국가코드1", "국가코드2", "국가코드3"],
  "cards": [
    {
      "country_code": "FIN",
      "country": "핀란드",
      "card_title": "구체적인 활동명 (15자 내외) — 예: '쓰러지지 않는 종이컵 성벽 만들기'",
      "card_subtitle": "이 활동의 학습 목표 (20자 내외)",
      "philosophy_tag": "이 나라의 차별점 (8자 내외)",
      "activity_format": "이 활동의 형식을 한 단어로. 위 카탈로그 중 하나 (예: '수학적 발견 미션', '학급 회의 프로젝트')",
      "key_approach": "이 나라 철학으로 활동을 풀어내는 핵심 접근. 교육철학 용어를 인용하되 실제 진행 방식이 보이게 2~3문장.",
      "activity_preview": "도입-전개-마무리의 활동 흐름. (도입) ... (전개 1단계) ... (전개 2단계) ... (마무리) ... 형태로 4~5단계가 보이게 작성. 약 4~6문장. 다른 카드와 활동 골격이 명백히 달라야 함.",
      "expected_experience": "유아가 이 활동에서 어떤 구체적 경험·발화·행동을 할지 2~3문장",
      "teacher_role": "이 활동에서 교사가 어떤 발문·개입·기록을 하는지 1~2문장",
      "why_this_country": "사용자가 입력한 활동 의도와 이 나라가 왜 잘 맞는지 1~2문장. 사용자 키워드 반드시 인용."
    }
  ]
}

### 최종 점검 (출력 전 스스로 확인)

JSON을 출력하기 전, 3장 카드의 activity_format을 비교하세요.
- 3장의 activity_format이 서로 다른가? → 같다면 다시 작성.
- 3장의 activity_preview의 첫 문장(도입)이 서로 다른가? → 비슷하다면 다시 작성.
- 활동의 결과물(완성된 작품/기록물/합의된 결정 등)이 서로 다른가? → 같다면 다시 작성.
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

⭐ 결정적 요구사항: 3장 카드는 activity_format 자체가 서로 달라야 합니다.
즉 "수학 미션 / 학급 토론 / 다매체 표현"처럼 활동의 종류 자체가 달라야 하며,
단순히 분위기만 다른 같은 활동이 되어서는 안 됩니다.
"""


# ============================================================
# 프롬프트 빌더
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
# 메인 함수 (재시도 포함)
# ============================================================
def generate_cards(
    user_query: str,
    age: int,
    duration: int,
    top_countries: list,
    countries_metadata: dict,
) -> dict:
    if not top_countries:
        raise ValueError("top_countries가 비어있습니다.")

    prompt = _build_prompt_3country(
        user_query=user_query,
        age=age,
        duration=duration,
        top_countries=top_countries,
        countries_metadata=countries_metadata,
    )

    client = _get_client()

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt["user"]],
                config=types.GenerateContentConfig(
                    system_instruction=prompt["system"],
                    temperature=0.9,           # v3: 활동 형식 다양성 더 확보
                    response_mime_type="application/json",
                    max_output_tokens=8192,
                ),
            )
            return json.loads(_strip_code_fence(response.text))
        except ServerError as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY_SEC * attempt
                print(f"   ⚠️ Gemini 서버 과부하. {wait}초 후 재시도 ({attempt}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                raise
        except json.JSONDecodeError:
            if attempt < MAX_RETRIES:
                print(f"   ⚠️ JSON 파싱 실패. 재시도 ({attempt}/{MAX_RETRIES})")
                time.sleep(1)
            else:
                raise

    raise last_err


# ============================================================
# 헬퍼
# ============================================================
def load_countries_metadata(all_countries_path: Path) -> dict:
    with open(all_countries_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["country_code"]: c for c in data["countries"]}


def print_card(card: dict):
    print(f"  ┌─ [{card.get('country_code', '?')}] {card.get('country', '?')} " + "─" * 40)
    print(f"  │ 활동명     : {card.get('card_title', '')}")
    print(f"  │ 학습 목표  : {card.get('card_subtitle', '')}")
    print(f"  │ 활동 형식  : {card.get('activity_format', '(미지정)')} ⭐")
    print(f"  │ 철학 태그  : {card.get('philosophy_tag', '')}")
    print(f"  │")
    print(f"  │ ▶ 핵심 접근")
    print(f"  │   {card.get('key_approach', '')}")
    print(f"  │")
    print(f"  │ ▶ 활동 시나리오 (도입→전개→마무리)")
    print(f"  │   {card.get('activity_preview', '(없음)')}")
    print(f"  │")
    print(f"  │ ▶ 유아의 기대 경험")
    print(f"  │   {card.get('expected_experience', '')}")
    print(f"  │")
    print(f"  │ ▶ 교사의 역할")
    print(f"  │   {card.get('teacher_role', '')}")
    print(f"  │")
    print(f"  │ ▶ 왜 이 나라인가?")
    print(f"  │   {card.get('why_this_country', '')}")
    print(f"  └" + "─" * 60)


# ============================================================
# 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    from services.retriever import Retriever

    retriever = Retriever()
    metadata = load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")

    # 쿼리를 살짝 넓혀서 다양한 나라가 나오게
    test_queries = [
        ("유아가 종이컵으로 다양한 활동을 하는 수업", 4, 40),
    ]

    print("=" * 70)
    print("card_generator.py 단독 테스트 (v3 - 활동 형식 차별화)")
    print("=" * 70)

    for query, age, duration in test_queries:
        print(f"\n쿼리: {query}\n")
        retrieval = retriever.search(query, top_k_countries=3)
        print(f"  retriever 결과: {[c['country'] for c in retrieval['top_countries']]}\n")

        try:
            result = generate_cards(
                user_query=query,
                age=age,
                duration=duration,
                top_countries=retrieval["top_countries"],
                countries_metadata=metadata,
            )
            print(f"  ✓ 카드 {len(result['cards'])}장 생성")
            # activity_format 한눈에 비교
            print(f"\n  📌 활동 형식 비교 (이 셋이 명백히 달라야 함):")
            for card in result["cards"]:
                print(f"     [{card.get('country_code')}] {card.get('activity_format', '(미지정)')}")
            print()
            for card in result["cards"]:
                print_card(card)
                print()
        except Exception as e:
            print(f"  ✗ 실패: {type(e).__name__}: {e}")

    print("=" * 70)
    print("✅ 테스트 완료")
    print("=" * 70)
