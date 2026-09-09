"""
services/template_filler.py
============================
Gemini를 사용해 지도안 내용을 사용자 양식의 섹션에 지능적으로 매핑
"""
import json
from typing import List, Dict


def smart_fill_with_gemini(
    lesson_markdown: str,
    template_sections: List[Dict],
    lesson_meta: Dict = None,
) -> Dict[str, str]:
    """
    Gemini를 사용해 양식의 각 섹션에 들어갈 내용을 생성.

    Args:
        lesson_markdown: AI가 생성한 지도안 마크다운 전체
        template_sections: 양식에서 추출된 섹션 리스트
            예: [{"name": "활동명"}, {"name": "수업일시"}, ...]
        lesson_meta: 추가 메타데이터 (선택)
            예: {"age": 5, "duration": 40, "search_query": "솔방울 놀이"}

    Returns:
        Dict[str, str]: {섹션이름: 내용} 매핑
            예: {"활동명": "솔방울 오감 탐색", "수업일시": "(미정)", ...}
    """
    from services.keyword_extractor import _get_client

    section_names = [s["name"] for s in template_sections if s.get("name")]
    if not section_names:
        return {}

    section_list_str = "\n".join(f"- {name}" for name in section_names)

    meta_str = ""
    if lesson_meta:
        meta_parts = []
        if "age" in lesson_meta:
            meta_parts.append(f"대상 연령: 만 {lesson_meta['age']}세")
        if "duration" in lesson_meta:
            meta_parts.append(f"수업 시간: {lesson_meta['duration']}분")
        if "search_query" in lesson_meta:
            meta_parts.append(f"수업 주제: {lesson_meta['search_query']}")
        if meta_parts:
            meta_str = "\n\n## 수업 메타 정보\n" + "\n".join(meta_parts)

    prompt = f"""당신은 유치원 교사를 돕는 AI입니다. 아래 [생성된 지도안]의 내용을 [양식의 섹션 목록]에 맞게 재배치/매핑해주세요.

## 양식의 섹션 목록
{section_list_str}

## 생성된 지도안 (마크다운)
{lesson_markdown}
{meta_str}

## 작업 지침
1. 양식의 각 섹션에 가장 적절한 내용을 지도안에서 추출하거나 요약해서 채워주세요.
2. 양식의 섹션 이름이 모호하더라도 의미를 해석해서 매핑하세요.
   - 예: "지도교사" → "(미정)" 또는 빈칸
   - 예: "수업일시", "장소" 등 메타 정보는 지도안에 없으면 "(작성 필요)" 표시
   - 예: "단원", "주제", "활동명" → 지도안의 활동 제목/주제
   - 예: "학습목표", "목표", "교육목표" → 지도안의 교육 목표 부분
   - 예: "준비물", "교구", "재료" → 지도안의 준비물 부분
   - 예: "도입", "전개", "정리", "마무리" → 지도안의 해당 단계 내용
   - 예: "교사 역할", "유의점", "평가" → 지도안의 해당 부분
3. 내용은 양식이 실제 교사가 작성한 것처럼 자연스럽고 구체적이어야 합니다.
4. 마크다운 기호(#, *, -)는 빼고 깔끔한 문장으로 작성하세요.
5. 각 섹션의 내용은 양식의 빈칸에 들어갈 정도의 적절한 길이여야 합니다 (한 줄~여러 줄).

## 출력 형식
오직 JSON만 출력하세요. 다른 설명 없이 다음 형식으로:
{{
  "섹션이름1": "채울 내용1",
  "섹션이름2": "채울 내용2",
  ...
}}

JSON에서 키 이름은 위 [양식의 섹션 목록]에 있는 이름을 그대로 사용하세요.
"""

    try:
        client = _get_client()
        from google.genai import types as genai_types

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        text = response.text.strip()
        # JSON 추출 (혹시 ```json...``` 등이 섞여있을 경우 대비)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:].strip()
            text = text.split("```")[0].strip()

        result = json.loads(text)
        return result
    except Exception as e:
        print(f"⚠️ Gemini 양식 매핑 실패: {e}")
        # 실패 시 빈 dict 반환 (기본 채우기 로직 사용됨)
        return {}


# ============================================================
# 개인정보 필드 감지
# ============================================================

# AI가 자동 작성할 수 없는, 사용자가 직접 입력해야 하는 필드 키워드
PERSONAL_INFO_KEYWORDS = {
    "교사 이름": ["지도교사명", "지도교사", "교사명", "담임교사", "담임", "선생님"],
    "학생/실습생 이름": ["학생명", "실습생", "실습교사", "교생", "이름"],
    "학과/소속": ["학과", "전공", "소속", "부서"],
    "학교/유치원명": ["학교명", "유치원명", "기관명", "학교", "유치원"],
    "수업 일시": ["수업일시", "일시", "날짜", "수업일자", "지도일시"],
    "대상 학급": ["대상학년반", "학년반", "대상학급", "반", "학년"],
    "장소": ["장소", "수업장소", "강의실", "교실"],
    "결재란": ["실습부장", "교감", "교장", "원장", "주임", "원감"],
}


def detect_personal_fields(template_sections: list) -> list:
    """
    양식 섹션 중 '사용자가 직접 입력해야 하는' 개인 정보 필드만 추출.

    Returns:
        [
            {
                "label": "지도교사명",        # 원본 라벨 (양식에 적힌 그대로)
                "category": "교사 이름",       # 우리가 분류한 카테고리
                "field_type": "text",          # text / date / select
                "placeholder": "예: 김민서",   # 입력 안내 문구
                "required": False,             # 필수 여부 (결재란 등은 비워둘 수 있음)
            },
            ...
        ]
    """
    fields = []
    seen_labels = set()

    for section in template_sections:
        label = section.get("name", "").strip()
        if not label or label in seen_labels:
            continue

        # 어떤 카테고리에 속하는지 매칭
        matched_category = None
        for category, keywords in PERSONAL_INFO_KEYWORDS.items():
            for kw in keywords:
                if kw in label:
                    matched_category = category
                    break
            if matched_category:
                break

        if not matched_category:
            continue

        # 필드 타입 결정
        field_type = "text"
        placeholder = ""
        required = matched_category not in ["결재란"]

        if matched_category == "수업 일시":
            field_type = "date"
            placeholder = "예: 2026-06-15 또는 2026.6.15 10:00~10:40"
        elif matched_category == "교사 이름":
            placeholder = "예: 김민서"
        elif matched_category == "학생/실습생 이름":
            placeholder = "예: 송민서"
        elif matched_category == "학과/소속":
            placeholder = "예: 유아교육과"
        elif matched_category == "학교/유치원명":
            placeholder = "예: 햇살유치원"
        elif matched_category == "대상 학급":
            placeholder = "예: 만 4세 햇님반"
        elif matched_category == "장소":
            placeholder = "예: 햇님반 교실"
        elif matched_category == "결재란":
            placeholder = "비워두거나 결재 후 작성"

        fields.append({
            "label": label,
            "category": matched_category,
            "field_type": field_type,
            "placeholder": placeholder,
            "required": required,
        })
        seen_labels.add(label)

    return fields
