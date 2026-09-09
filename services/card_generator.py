"""
services/card_generator.py
====================
STAGE D: retriever가 추천한 3개국 → 카드 3장 생성

사용 SDK: google-genai
사용 모델: gemini-2.5-flash

【v4 개선점】
- v3까지: 카드에 정보 과다 (5개 섹션 prose) → 가독성 떨어짐
- v4: 카드용 짧은 필드 추가
    · key_keywords: 핵심 접근법을 단어/짧은 구 4~5개 (칩 표시용)
    · activity_summary: 활동을 2~3문장으로 압축 (카드용)
    · activity_preview: 도입/전개/마무리 풀 시나리오 (지도안 페이지용으로 유지)
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
# 시스템 프롬프트 (v4 - 카드 가독성 개선)
# ============================================================
SYSTEM_PROMPT_3COUNTRY = """\
당신은 유아교육 전문가이자 큐레이터입니다. 한국 유아교육과 학생이 입력한 수업 아이디어를 바탕으로,
주어진 3개 국가 각각에 대해 "수업 제안 카드"를 만들어주는 역할을 합니다.

### 작업 규칙

주어진 3개 국가 각각에 대해 카드를 1장씩, 총 3장을 생성합니다.

### 가장 중요한 원칙 ① — "카드는 한눈에 파악되어야 한다"

카드는 사용자가 짧은 시간 안에 3개국을 비교하는 화면입니다. 긴 설명은 금물.
- key_keywords: **칩 형태로 표시할 짧은 단어/구 4~5개** (각 6글자 이내, "유아 주도성" "비구조화 자료" 같은 명사구)
- activity_summary: **이 활동의 핵심을 2~3문장으로 압축** (카드에 표시됨)
- activity_preview: **도입/전개/마무리 풀 시나리오** (카드에는 안 보이지만 지도안 작성에 쓰임)

### 가장 중요한 원칙 ② — "3장의 카드는 활동 형식부터 달라야 한다" ⭐⭐⭐

같은 재료(예: 종이컵)에 대해서도 3장의 카드는 단순히 분위기만 다른 게 아니라
**"무엇을 하는 활동인가"의 종류 자체가 달라야 합니다.**

❌ 절대 금지 (분위기만 변주):
   - 카드1: "자유롭게 쌓고 무너지면 토의"
   - 카드2: "차분하게 쌓고 무너지면 다시 시도"
   - 카드3: "민주적으로 쌓고 무너지면 회의"

⭕ 반드시 이렇게 (활동 형식이 다름):
   - 카드1: 수학 미션 (패턴 카드 매칭, 챌린지)
   - 카드2: 야외 신체 게임 (팀 릴레이)
   - 카드3: 학급 토론 프로젝트 (재활용 회의)

### 활동 형식의 카탈로그

가능한 형식:
- **수학적 발견 미션**: 패턴/개수/도형/측정 같은 수학 개념 발견
- **신체/협동 게임**: 릴레이, 팀 대결, 함께 큰 구조 만들기
- **재료 변환 프로젝트**: 한 재료를 다른 용도로 변환·재사용
- **학급 회의/토론**: 의견 모으기, 투표, 합의, 실행
- **다매체 표현 활동**: 그리기·찰흙·그림자·사진 등 여러 매체로 같은 대상 표현
- **이야기/극놀이**: 재료를 등장인물·소품 삼아 즉흥 극
- **자연·야외 통합**: 실외에서 자연물과 결합
- **돌봄·일상 통합**: 간식·정리정돈 같은 일상에 활동을 녹이기
- **관찰·기록 프로젝트**: 시간을 두고 변화 관찰, 사진/그림으로 기록

### 국가별 철학과 잘 맞는 활동 형식 가이드

  · 싱가포르(SGP) → 수학적 발견 미션 (수리력 강조)
  · 영국(GBR) → 신체/협동 게임 (EYFS Prime/Specific 균형)
  · 독일(GER) → 학급 회의·토론, 재활용·환경 프로젝트 (민주적 참여)
  · 이탈리아(ITA) → 다매체 표현 활동 (100가지 언어)
  · 핀란드(FIN) → 돌봄·일상 통합 / 자연·야외
  · 스웨덴(SWE) → 자연·야외 통합 / 위험 감수 자유 실험
  · 일본(JPN) → 정돈된 환경에서 차분한 협력 / 관찰·기록
  · 한국(KOR) → 누리과정 5개 영역 통합한 자유놀이
  · 호주(AUS) → 원주민·Country 관점, 야외 자연
  · 뉴질랜드(NZL) → 이야기/극놀이, Whāriki 메타포의 협동 구조

### 카드 작성 원칙

- **자연스러운 한국어**: 외국 용어는 "원어(한국어)" 형식 (예: "Regista(연출가)")
- **카드 간 차별점 명확**: 활동 종류·공간·결과물이 명백히 달라야 함
- **사용자 입력 키워드 반영**: 입력 단어가 자연스럽게 등장
- **점수 노출 금지**

### 출력 형식 (JSON)

반드시 아래 JSON 형식으로만 답하세요. 마크다운 코드블록 사용 금지, 순수 JSON만 출력.

{
  "selected_countries": ["국가코드1", "국가코드2", "국가코드3"],
  "cards": [
    {
      "country_code": "FIN",
      "country": "핀란드",
      "card_title": "구체적 활동명 (15자 내외) — 예: '쓰러지지 않는 종이컵 성벽 만들기'",
      "card_subtitle": "활동의 학습 목표를 한 줄로 (20자 내외)",
      "philosophy_tag": "이 나라의 차별점 (8자 내외)",
      "activity_format": "활동 형식을 한 단어로 (위 카탈로그 중 하나)",

      "key_keywords": ["칩1", "칩2", "칩3", "칩4", "칩5"],
      // ⭐ 핵심 접근법을 짧은 단어/구 4~5개로. 각 6글자 이내.
      // 예: ["유아 주도성", "비구조화 자료", "통합적 배움", "5개 영역", "교사 비계"]
      // 너무 추상적인 단어("탐색", "경험") 금지. 이 나라 철학에서만 쓰는 고유한 용어 우선.

      "activity_summary": "이 활동을 2~3문장으로 압축한 요약. 카드에 표시되므로 짧고 명료하게. 어떤 활동이고 어떤 결과물이 나오는지가 보여야 함.",
      // 예: "솔방울·나뭇잎을 자유롭게 배치하고 만져보며 오감으로 탐색합니다. 유아가 스스로 놀이를 확장하면 교사는 비구조화 자료를 추가로 지원합니다."

      "activity_preview": "도입-전개-마무리의 풀 시나리오. (도입) ... (전개 1단계) ... (전개 2단계) ... (마무리) ... 형태로 4~5단계가 보이게 작성. 약 4~6문장. 카드엔 안 보이고 지도안 작성에 쓰임.",

      "expected_experience": "유아의 구체적 경험·발화·행동 2~3문장. 지도안 작성용.",
      "teacher_role": "교사의 발문·개입·기록 1~2문장. 지도안 작성용.",
      "why_this_country": "사용자 의도와 이 나라가 잘 맞는 이유 1~2문장. 카드에는 안 보임."
    }
  ]
}

### 최종 점검 (출력 전 스스로 확인)

1. 3장의 activity_format이 서로 다른가?
2. 3장의 key_keywords에 겹치는 단어가 거의 없는가? (각 나라 고유 용어 위주)
3. 각 키워드가 6글자 이내인가? (칩 표시 가독성)
4. activity_summary가 길어도 3문장 이내인가?
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

⭐ 핵심 요구사항:
1. activity_format은 3장이 서로 다르게.
2. key_keywords는 각 6글자 이내, 4~5개, 그 나라만의 고유 용어 위주.
3. activity_summary는 2~3문장으로 짧게.
4. 단순히 분위기만 다른 같은 활동이 되어서는 안 됩니다.
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
# 메인 함수
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
                    temperature=0.85,
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
    print(f"  │ 활동 형식  : {card.get('activity_format', '')}")
    print(f"  │ 철학 태그  : {card.get('philosophy_tag', '')}")
    print(f"  │ 키워드 칩  : {' · '.join(card.get('key_keywords', []))}")
    print(f"  │")
    print(f"  │ ▶ 활동 요약 (카드 표시용)")
    print(f"  │   {card.get('activity_summary', '')}")
    print(f"  │")
    print(f"  │ ▶ 활동 시나리오 (지도안용)")
    print(f"  │   {card.get('activity_preview', '')[:200]}...")
    print(f"  └" + "─" * 60)


# ============================================================
# 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    from services.retriever import Retriever

    retriever = Retriever()
    metadata = load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")

    test_queries = [
        ("유아가 솔방울을 만지고 자연을 탐색하는 활동", 4, 40),
    ]

    print("=" * 70)
    print("card_generator.py 단독 테스트 (v4 - 카드 가독성 개선)")
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
            print(f"\n  📌 활동 형식 비교:")
            for card in result["cards"]:
                print(f"     [{card.get('country_code')}] {card.get('activity_format', '(미지정)')}")
            print(f"\n  📌 키워드 칩 비교:")
            for card in result["cards"]:
                print(f"     [{card.get('country_code')}] {' · '.join(card.get('key_keywords', []))}")
            print()
            for card in result["cards"]:
                print_card(card)
                print()
        except Exception as e:
            print(f"  ✗ 실패: {type(e).__name__}: {e}")

    print("=" * 70)
    print("✅ 테스트 완료")
    print("=" * 70)
