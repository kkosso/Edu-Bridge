"""
services/applied_template_service.py
====================================
양식 적용 결과의 fills를 채팅으로 수정하는 로직
"""
import json
from typing import List, Dict


def refine_fills_with_chat(
    current_fills: List[Dict],
    refine_request: str,
    conversation_history: List[Dict] = None,
    template_analysis_summary: str = "",
) -> Dict:
    """
    채팅으로 양식 셀 내용 수정 요청 처리

    Args:
        current_fills: 현재 채워진 셀들 [{"table_idx":0, "row":0, "col":1, "content":"...", "label":"단원"}, ...]
        refine_request: 사용자의 수정 요청
        conversation_history: 이전 대화 (선택)

    Returns:
        {
            "updated_fills": [...],     # 전체 fills (변경된 셀만 content가 바뀜)
            "changed_indices": [0,3,5], # 변경된 셀의 인덱스
            "assistant_message": "..."
        }
    """
    from services.keyword_extractor import _get_client
    from google.genai import types as genai_types

    # current_fills에 인덱스 추가
    cells_for_prompt = []
    for i, c in enumerate(current_fills):
        cells_for_prompt.append({
            "id": i,
            "label": c.get("label", ""),
            "content": c.get("content", "")[:300],  # 너무 길면 자르기
        })

    history_text = ""
    if conversation_history:
        history_text = "\n\n## 이전 대화\n"
        for msg in conversation_history[-6:]:
            role = "교사" if msg.get("role") == "user" else "AI"
            history_text += f"[{role}]: {msg.get('content', '')[:200]}\n"

    prompt = f"""당신은 유치원 교사의 지도안 양식 작성을 돕는 AI입니다.
교사가 양식에 채워진 내용 중 일부를 수정하고 싶어 합니다.

## 현재 양식에 채워진 셀들
{json.dumps(cells_for_prompt, ensure_ascii=False, indent=2)}

{history_text}

## 교사의 수정 요청
{refine_request}

## 작업 지침
1. 교사의 요청에 해당하는 셀들만 찾아서 수정하세요.
2. 라벨(label)을 보고 어떤 셀을 수정해야 할지 판단하세요.
3. 요청과 무관한 셀은 변경하지 마세요.
4. 유아 발달과 교육적 적절성을 고려해서 작성하세요.
5. 마크다운 기호 없이 깔끔한 문장으로.

## 출력 형식
오직 JSON만 출력:
{{
  "changes": [
    {{"id": 3, "new_content": "..."}},
    {{"id": 5, "new_content": "..."}}
  ],
  "summary": "수정된 내용에 대한 1-2줄 설명 (교사에게 보낼 응답)"
}}
"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=4096,
                response_mime_type="application/json",
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:].strip()
            text = text.split("```")[0].strip()

        result = json.loads(text)
        changes = result.get("changes", [])
        summary = result.get("summary", "수정을 완료했어요.")

        # current_fills 복사 + 변경 적용
        updated_fills = [dict(c) for c in current_fills]
        changed_indices = []
        for change in changes:
            idx = change.get("id")
            new_content = change.get("new_content", "")
            if idx is not None and 0 <= idx < len(updated_fills) and new_content:
                updated_fills[idx]["content"] = new_content
                changed_indices.append(idx)

        return {
            "updated_fills": updated_fills,
            "changed_indices": changed_indices,
            "assistant_message": summary,
        }
    except Exception as e:
        print(f"⚠️ Fills 수정 실패: {e}")
        return {
            "updated_fills": current_fills,
            "changed_indices": [],
            "assistant_message": f"수정 실패: {e}",
        }
