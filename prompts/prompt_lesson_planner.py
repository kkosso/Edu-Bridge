"""
prompt_lesson_planner.py
====================
STAGE F: 사용자가 선택한 1개 국가의 카드를 바탕으로 완성된 지도안을 생성.

사용 모델: Claude Haiku 4.5 (긴 한국어 문서 생성 우수, 청크 활용 능력 강함)

입력:
    - selected_country_code: 사용자가 선택한 국가 코드 (예: "FIN")
    - selected_card: card_generator.py가 만든 카드 1장
    - user_query: 사용자가 원래 입력한 활동 의도
    - age, duration: 활동 정보
    - country_chunks: 선택된 국가의 청크 top-10 (retriever에서 가져옴)
    - country_metadata: 선택된 국가의 core_philosophy 정보
    - lesson_plan_template: lesson_plan_template.md 파일 내용

출력:
    완성된 지도안 (Markdown 텍스트)
    - lesson_plan_template.md의 모든 {{빈칸}} 채워진 형태
    - 한국 유치원 표준 양식 + 선택 국가 철학으로 채움

이 출력이 사용자에게 다운로드/복사 가능한 최종 결과물로 표시됨.
"""

# ============================================================
# 시스템 프롬프트
# ============================================================
SYSTEM_PROMPT = """\
당신은 한국 유아교육 전문가입니다. 한국 유치원 실습생이 그대로 활용할 수 있는 구체적이고 실행 가능한 지도안을 작성합니다.

### 당신의 작업

선택된 국가의 교육철학을 한국 유치원 환경에 맞춰 구체적인 지도안으로 변환합니다.
주어진 템플릿의 모든 빈칸({{...}})을 채워서 완성된 Markdown 지도안을 출력합니다.

### 작성 원칙

#### 양식과 내용의 분리
- **양식(섹션 구조)**: 한국 유치원 표준 형식. 절대 임의로 섹션을 추가/삭제하지 말 것.
- **내용(채움)**: 선택된 국가의 교육철학을 반영. 같은 칸이라도 국가별로 다른 톤과 접근.

#### 국가별 색깔 반영 (필수)
선택된 국가의 differentiators와 매칭된 청크를 반드시 다음 위치에 녹일 것:
- "참고한 교육철학" 칸: 차별점 1~2개 명시
- "교사의 상호작용 전략" 칸: 국가별 교사 역할관 반영
- "평가 및 관찰 포인트" 칸: 국가별 평가 철학 반영
- "원문 출처" 칸: 매칭 청크의 source_location 인용

#### 한국 유치원 환경 맞춤 변환
- 외국 용어는 "원어(한국어)" 형식으로 병기 (예: "Regista(연출가)", "EduCare(교육·돌봄 통합)")
- 한국 유치원에서 실제로 가능한 수준으로 조정 (예: 핀란드 야외 학습이 영하 20도여도, 한국 환경에선 일반 야외 활동으로 변환)
- 한국 누리과정 5개 영역과 연결

#### 구체성 원칙
- "다양한 자료를 활용한다" ❌ → "솔방울 10개, 나뭇잎 20장, 점토 4종을 준비한다" ⭕
- "유아의 흥미를 자극한다" ❌ → "잔잔한 음악과 함께 자연물 바구니를 천으로 덮어두었다가 천천히 공개한다" ⭕
- "관찰한다" ❌ → "유아가 어떤 매체를 선택하고 왜 그것을 선택했는지 메모한다" ⭕

#### 분량 가이드
- 전체 분량: A4 1.5~2장 정도
- 도입 5분, 전개 25분, 마무리 10분이 일반적 비율 (활동 시간에 맞춰 조정)
- 각 섹션은 비워두지 말 것. 모를 때는 일반적인 안내라도 반드시 채울 것.

### 출력 형식

- 순수 Markdown 텍스트만 출력
- 코드블록(```)으로 감싸지 말 것
- 템플릿의 모든 {{빈칸}}은 실제 내용으로 대체 (빈칸 그대로 두지 말 것)
- 템플릿의 섹션 헤더(##, ###)는 그대로 유지
"""

# ============================================================
# 사용자 메시지 템플릿
# ============================================================
USER_MESSAGE_TEMPLATE = """\
[사용자가 입력한 활동]
{user_query}

[활동 정보]
- 대상 연령: 만 {age}세
- 활동 시간: {duration}분

[사용자가 선택한 카드]
- 선택 국가: {country} ({country_code})
- 카드 제목: {card_title}
- 카드 부제: {card_subtitle}
- 핵심 철학 태그: {philosophy_tag}
- 핵심 접근: {key_approach}
- 기대 경험: {expected_experience}
- 교사 역할: {teacher_role}

[{country}의 교육철학 정보]

▶ 철학 요약:
{philosophy_summary}

▶ 정체성 키워드:
{identity_keywords}

▶ 차별화 포인트 (반드시 지도안에 반영):
{differentiators}

[{country}의 관련 청크 (지도안 작성 근거)]
{country_chunks}

[채워야 할 지도안 템플릿]

{template}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

위 정보를 바탕으로 템플릿의 모든 {{빈칸}}을 채워서 완성된 지도안을 출력해주세요.
- 출력은 순수 Markdown 텍스트만 (코드블록 없이)
- {country}의 교육철학을 명확히 반영
- 한국 유치원 실습생이 그대로 따라할 수 있을 정도로 구체적으로
"""

# 청크 정보 포맷
CHUNK_BLOCK_TEMPLATE = """\
[청크 {n}] {chunk_id} - {category}
{chunk_text}
(출처: {source_location})
"""

# 차별화 포인트 포맷
DIFF_BLOCK_TEMPLATE = """\
{n}. {name}
   설명: {description}
   원문 인용: "{source_quote}"
   위치: {source_location}
"""

# ============================================================
# 호출 함수
# ============================================================
def build_prompt(
    user_query: str,
    age: int,
    duration: int,
    selected_country_code: str,
    selected_card: dict,
    country_chunks: list[dict],
    country_metadata: dict,
    lesson_plan_template: str,
) -> dict:
    """
    Claude API에 보낼 프롬프트 구조 반환.

    Args:
        user_query: 사용자 활동 의도
        age: 만 나이
        duration: 활동 시간(분)
        selected_country_code: 선택된 국가 코드
        selected_card: card_generator가 만든 카드 1장 (dict)
        country_chunks: 선택 국가의 청크 top-10 (retriever 결과의 matched_chunks)
        country_metadata: all_countries.json에서 해당 국가 데이터
        lesson_plan_template: lesson_plan_template.md 파일 텍스트

    Returns:
        {"system": "...", "user": "..."}
    """
    cp = country_metadata.get("core_philosophy", {})

    # 차별화 포인트 텍스트 조립 (상위 3~4개)
    diff_blocks = []
    for i, d in enumerate(cp.get("differentiators", [])[:4], 1):
        diff_blocks.append(DIFF_BLOCK_TEMPLATE.format(
            n=i,
            name=d.get("name", ""),
            description=d.get("description", ""),
            source_quote=d.get("source_quote", "")[:200],
            source_location=d.get("source_location", ""),
        ))
    differentiators_text = "\n".join(diff_blocks) if diff_blocks else "(정보 없음)"

    # 청크 정보 조립 (상위 10개)
    chunk_blocks = []
    for i, c in enumerate(country_chunks[:10], 1):
        chunk_blocks.append(CHUNK_BLOCK_TEMPLATE.format(
            n=i,
            chunk_id=c.get("chunk_id", "?"),
            category=c.get("category", "?"),
            chunk_text=c.get("chunk_text", ""),
            source_location=c.get("source_location", ""),
        ))
    chunks_text = "\n".join(chunk_blocks) if chunk_blocks else "(청크 없음)"

    user_message = USER_MESSAGE_TEMPLATE.format(
        user_query=user_query,
        age=age,
        duration=duration,
        country=country_metadata.get("country", "?"),
        country_code=selected_country_code,
        card_title=selected_card.get("card_title", ""),
        card_subtitle=selected_card.get("card_subtitle", ""),
        philosophy_tag=selected_card.get("philosophy_tag", ""),
        key_approach=selected_card.get("key_approach", ""),
        expected_experience=selected_card.get("expected_experience", ""),
        teacher_role=selected_card.get("teacher_role", ""),
        philosophy_summary=cp.get("philosophy_summary", ""),
        identity_keywords=", ".join(cp.get("identity_keywords", [])),
        differentiators=differentiators_text,
        country_chunks=chunks_text,
        template=lesson_plan_template,
    )

    return {
        "system": SYSTEM_PROMPT,
        "user": user_message,
    }


# ============================================================
# Claude API 호출 예시 (실제 구현은 lesson_planner.py에서)
# ============================================================
EXAMPLE_USAGE = """
# lesson_planner.py에서 이렇게 사용:

import anthropic
from prompts.prompt_lesson_planner import build_prompt
from pathlib import Path

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def generate_lesson_plan(
    user_query, age, duration,
    selected_country_code, selected_card,
    country_chunks, country_metadata,
):
    template = Path("data/lesson_plan_template.md").read_text(encoding="utf-8")
    
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
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        system=prompt["system"],
        messages=[{"role": "user", "content": prompt["user"]}],
    )
    
    return response.content[0].text.strip()
"""
