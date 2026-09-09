"""
prompt_card_generator.py
====================
STAGE D-E: retriever가 추천한 5개국 후보에서 3개국을 선택하고,
각 나라별로 차별화된 "수업 제안 카드"를 생성.

사용 모델: Claude Haiku 4.5 (한국어 강함, 빠름, JSON 출력 안정적)

입력:
    - user_query: 사용자가 원래 입력한 활동 의도 (또는 search_query)
    - top_5_countries: retriever.search() 결과의 top_countries
        각 country는 다음 정보 포함:
        - country, country_code, final_score
        - matched_chunks (top 3)
        - core_philosophy (philosophy_summary, identity_keywords, differentiators)

출력:
    {
        "selected_countries": ["FIN", "ITA", "KOR"],
        "selection_reason": "이 3개국은 서로 다른 접근 방식으로 활동을 풍부하게 합니다",
        "cards": [
            {
                "country_code": "FIN",
                "country": "핀란드",
                "card_title": "일상이 곧 배움이 되는 자연 탐색",
                "card_subtitle": "EduCare 통합 - 식사·휴식·놀이가 하나로",
                "philosophy_tag": "교육·교수·돌봄 통합",
                "key_approach": "활동 중 이루어지는 모든 일상 행동을 교육적 순간으로 활용...",
                "expected_experience": "유아는 자연물을 탐색하면서 동시에 ...",
                "teacher_role": "다전문가 협력을 통해 ...",
                "why_this_country": "당신이 입력한 활동은 ... 핀란드의 EduCare 철학과 잘 맞습니다"
            },
            ...
        ]
    }

이 출력이 사용자에게 카드 형태로 표시됨. 사용자가 1개 카드를 선택하면 STAGE F로 진행.
"""

# ============================================================
# 시스템 프롬프트
# ============================================================
SYSTEM_PROMPT = """\
당신은 유아교육 전문가이자 큐레이터입니다. 한국 유아교육과 학생이 입력한 수업 아이디어를 바탕으로,
세계 여러 나라의 유아교육 철학 중에서 가장 적합한 3가지를 골라 "수업 제안 카드"를 만들어주는 역할을 합니다.

### 당신의 작업

5개 후보 국가 중에서 **차별화된 3개국**을 선택하고, 각 나라별로 카드를 1장씩 만듭니다.

### 3개국 선택 기준 (매우 중요)

1. **차별성**: 5개국 중 비슷한 접근 방식을 가진 나라는 한 나라만 선택. 서로 다른 색깔의 3개국 추천.
2. **활동 적합성**: 단순히 임베딩 점수가 높은 게 아니라, 실제로 이 활동을 풍부하게 만들 수 있는 나라.
3. **교사의 시야 확장**: 사용자가 미처 생각 못 한 새로운 관점을 제공하는 나라 우선.

예시: 후보가 [핀란드, 스웨덴, 한국, 호주, 영국]이라면
- 핀란드와 스웨덴은 둘 다 노르딕 EduCare → 둘 중 하나만
- 한국과 영국은 둘 다 놀이 중심 → 둘 중 하나만
- 결과: 핀란드, 한국, 호주 (3개의 다른 색깔)

### 카드 작성 원칙

- **자연스러운 한국어**: 외국 용어는 "원어(한국어)" 형식으로 병기
- **구체적**: 추상적인 "유아 중심" 같은 말 대신 실제 활동 모습이 그려지는 표현
- **차별점 강조**: 각 카드의 "philosophy_tag"가 서로 명확히 달라야 함
- **사용자 입력 반영**: card_title과 why_this_country에 사용자가 입력한 키워드가 자연스럽게 녹아야 함
- **점수 노출 금지**: 임베딩 점수, 순위 같은 시스템 정보는 카드에 표시하지 않음

### 출력 형식 (JSON)

반드시 아래 JSON 형식으로만 답하세요. 마크다운 코드블록도 사용 금지, 순수 JSON만 출력.

{
  "selected_countries": ["국가코드1", "국가코드2", "국가코드3"],
  "selection_reason": "왜 이 3개국을 선택했는지 1~2문장",
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
    {...},
    {...}
  ]
}
"""

# ============================================================
# 사용자 메시지 템플릿
# ============================================================
USER_MESSAGE_TEMPLATE = """\
[사용자 입력 활동]
{user_query}

[활동 정보]
- 대상 연령: 만 {age}세
- 활동 시간: {duration}분

[5개 후보 국가 정보]
{country_candidates}

위 5개 후보 중 차별화된 3개국을 선택하고, 각 나라별 수업 제안 카드를 JSON으로 생성해주세요.
"""

# 5개 후보 국가 정보를 LLM이 읽기 쉬운 형식으로 변환
COUNTRY_BLOCK_TEMPLATE = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【후보 {rank}】 {country} ({country_code})

▶ 핵심 교육철학 요약:
{philosophy_summary}

▶ 정체성 키워드: {identity_keywords}

▶ 주요 차별화 포인트:
{differentiators}

▶ 이 활동과 매칭된 청크 (상위 3개):
{matched_chunks}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ============================================================
# 호출 함수
# ============================================================
def build_prompt(
    user_query: str,
    age: int,
    duration: int,
    top_5_countries: list[dict],
    countries_metadata: dict,  # all_countries.json의 countries 정보
) -> dict:
    """
    Claude API에 보낼 프롬프트 구조 반환.

    Args:
        user_query: 사용자가 입력한 활동 의도 (search_query)
        age: 만 나이
        duration: 활동 시간(분)
        top_5_countries: retriever.search() 결과의 top_countries
        countries_metadata: all_countries.json의 countries 배열 ({code: country_data})

    Returns:
        {"system": "...", "user": "..."}
    """
    # 5개 후보 정보를 텍스트로 조립
    country_blocks = []
    for rank, country in enumerate(top_5_countries, 1):
        code = country["country_code"]
        meta = countries_metadata.get(code, {})
        cp = meta.get("core_philosophy", {})

        # differentiators 압축 표시
        diff_lines = []
        for d in cp.get("differentiators", [])[:3]:  # 상위 3개만
            diff_lines.append(f"  · {d['name']}: {d['description'][:80]}...")
        differentiators_text = "\n".join(diff_lines) if diff_lines else "  (정보 없음)"

        # 매칭 청크 정보
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

    user_message = USER_MESSAGE_TEMPLATE.format(
        user_query=user_query,
        age=age,
        duration=duration,
        country_candidates="\n".join(country_blocks),
    )

    return {
        "system": SYSTEM_PROMPT,
        "user": user_message,
    }


# ============================================================
# Claude API 호출 예시 (실제 구현은 card_generator.py에서)
# ============================================================
EXAMPLE_USAGE = """
# card_generator.py에서 이렇게 사용:

import anthropic
import json
from prompts.prompt_card_generator import build_prompt

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def generate_cards(user_query, age, duration, top_5_countries, countries_metadata):
    prompt = build_prompt(user_query, age, duration, top_5_countries, countries_metadata)
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=3000,
        system=prompt["system"],
        messages=[{"role": "user", "content": prompt["user"]}],
    )
    
    result_text = response.content[0].text.strip()
    # JSON 파싱 (LLM이 코드블록으로 감싸도 처리)
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    
    return json.loads(result_text.strip())
"""
