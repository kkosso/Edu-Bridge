#!/usr/bin/env python3
"""
patch_smart_template_fill.py
==============================
Gemini로 지도안 내용을 양식 섹션에 지능적으로 매핑해서 채우기

기존: 마크다운 헤더 이름이 양식 섹션과 정확히 일치해야 채워짐 (대부분 실패)
개선: Gemini가 양식 섹션 의미를 이해해서 지도안 내용을 적절히 분배

수행 작업:
1. services/template_filler.py 신규 생성 (Gemini 기반 매핑)
2. services/docx_writer.py 개선 (셀 채우기 패턴 다양화)
3. main.py: export-docx API에 Gemini 매핑 통합
"""
from pathlib import Path

BACKEND = Path(".")
SERVICES = BACKEND / "services"
MAIN_PATH = BACKEND / "main.py"


# ============================================================
# 1) services/template_filler.py 신규 생성
# ============================================================
TEMPLATE_FILLER_CODE = '''"""
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

    section_list_str = "\\n".join(f"- {name}" for name in section_names)

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
            meta_str = "\\n\\n## 수업 메타 정보\\n" + "\\n".join(meta_parts)

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
'''

(SERVICES / "template_filler.py").write_text(TEMPLATE_FILLER_CODE, encoding="utf-8")
print("✅ services/template_filler.py 생성")


# ============================================================
# 2) services/docx_writer.py 개선 - 셀 채우기 패턴 다양화
# ============================================================
docx_writer = (SERVICES / "docx_writer.py").read_text(encoding="utf-8")

old_fill = '''def _fill_template(template_path: str, output_path: str, sections_data: Dict[str, str]):
    """
    사용자 양식 docx를 열어서 각 섹션에 값을 채워 넣기.
    
    동작 방식:
    - 표 안의 각 셀: 셀 텍스트가 sections_data의 키와 매칭되면 다음 셀에 값 삽입
    - 단락 기반: 헤더 단락 다음에 새 단락으로 값 추가
    """
    doc = Document(template_path)

    # 1) 표 기반 채우기
    for table in doc.tables:
        for row in table.rows:
            cells = row.cells
            for i, cell in enumerate(cells):
                cell_text = cell.text.strip().rstrip(":：").strip()
                # 매칭되는 섹션 데이터 찾기
                value = _find_matching_value(cell_text, sections_data)
                if value and i + 1 < len(cells):
                    # 다음 셀이 비어있으면 값 삽입
                    next_cell = cells[i + 1]
                    if not next_cell.text.strip() or _is_filler(next_cell.text):
                        # 기존 텍스트 제거
                        for para in next_cell.paragraphs:
                            for run in para.runs:
                                run.text = ""
                        # 새 텍스트 삽입
                        next_cell.paragraphs[0].add_run(value)

    # 2) 단락 기반 채우기 (헤더 발견 시 다음 단락에 값 추가)
    paragraphs = doc.paragraphs
    for i, para in enumerate(paragraphs):
        text = para.text.strip().rstrip(":：").strip()
        value = _find_matching_value(text, sections_data)
        if value and i + 1 < len(paragraphs):
            next_para = paragraphs[i + 1]
            if not next_para.text.strip() or _is_filler(next_para.text):
                next_para.add_run(value)

    doc.save(output_path)'''

new_fill = '''def _fill_template(template_path: str, output_path: str, sections_data: Dict[str, str]):
    """
    사용자 양식 docx를 열어서 각 섹션에 값을 채워 넣기.

    셀 채우기 전략 (우선순위):
    1. 같은 행의 다음 셀 (가장 일반적)
    2. 바로 아래 행의 같은 위치 셀
    3. 같은 셀 내부의 빈 공간
    """
    doc = Document(template_path)
    filled_cells = set()  # 이미 채운 셀 추적

    # 1) 표 기반 채우기
    for table in doc.tables:
        rows = list(table.rows)
        for row_idx, row in enumerate(rows):
            cells = row.cells
            for col_idx, cell in enumerate(cells):
                cell_id = (id(table), row_idx, col_idx)
                if cell_id in filled_cells:
                    continue
                
                cell_text = cell.text.strip().rstrip(":：").strip()
                if not cell_text:
                    continue
                
                value = _find_matching_value(cell_text, sections_data)
                if not value:
                    continue
                
                # 전략 1: 같은 행의 다음 셀
                if col_idx + 1 < len(cells):
                    next_cell = cells[col_idx + 1]
                    next_id = (id(table), row_idx, col_idx + 1)
                    if next_id not in filled_cells and (
                        not next_cell.text.strip() or _is_filler(next_cell.text)
                    ):
                        _replace_cell_text(next_cell, value)
                        filled_cells.add(next_id)
                        continue
                
                # 전략 2: 바로 아래 행의 같은 위치 셀
                if row_idx + 1 < len(rows):
                    below_cell = rows[row_idx + 1].cells[col_idx] if col_idx < len(rows[row_idx + 1].cells) else None
                    below_id = (id(table), row_idx + 1, col_idx)
                    if below_cell and below_id not in filled_cells and (
                        not below_cell.text.strip() or _is_filler(below_cell.text)
                    ):
                        _replace_cell_text(below_cell, value)
                        filled_cells.add(below_id)
                        continue

    # 2) 단락 기반 채우기
    paragraphs = doc.paragraphs
    for i, para in enumerate(paragraphs):
        text = para.text.strip().rstrip(":：").strip()
        if not text:
            continue
        value = _find_matching_value(text, sections_data)
        if value and i + 1 < len(paragraphs):
            next_para = paragraphs[i + 1]
            if not next_para.text.strip() or _is_filler(next_para.text):
                next_para.add_run(value)

    doc.save(output_path)


def _replace_cell_text(cell, value: str):
    """셀의 기존 텍스트를 모두 제거하고 새 값 삽입"""
    # 첫 단락만 남기고 나머지 단락 제거
    for para in cell.paragraphs[1:]:
        p_element = para._element
        p_element.getparent().remove(p_element)
    # 첫 단락의 모든 run 제거
    first_para = cell.paragraphs[0]
    for run in first_para.runs:
        run.text = ""
    # 새 텍스트 삽입 (줄바꿈 처리)
    lines = value.split("\\n")
    if lines:
        first_para.add_run(lines[0])
        for extra_line in lines[1:]:
            new_para = cell.add_paragraph()
            new_para.add_run(extra_line)'''

if old_fill in docx_writer:
    docx_writer = docx_writer.replace(old_fill, new_fill)
    (SERVICES / "docx_writer.py").write_text(docx_writer, encoding="utf-8")
    print("✅ docx_writer.py: 셀 채우기 패턴 개선")
else:
    print("ℹ️  docx_writer.py: 이미 개선됨 또는 패턴 변경")


# ============================================================
# 3) main.py: export-docx API에 Gemini 매핑 통합
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

old_export = '''@app.post("/api/lesson/export-docx")
async def api_export_lesson_docx(body: dict):
    """
    지도안을 .docx 파일로 다운로드
    
    body: {
        "markdown": "...",
        "title": "...",
        "template_id": null (또는 양식 ID),
        "sections_data": {"활동명": "...", "목표": "..."}  // template_id 있을 때
    }
    """
    from services.docx_writer import markdown_to_docx
    
    markdown = body.get("markdown", "")
    title = body.get("title", "지도안")
    template_id = body.get("template_id")
    sections_data = body.get("sections_data")
    
    output_path = TEMPLATES_DIR / f"output_{uuid.uuid4().hex}.docx"
    
    template_path = None
    if template_id:
        # DB에서 template_path 조회 (인증 필요하지만 간단하게 처리)
        from database import SessionLocal
        db = SessionLocal()
        try:
            tpl = db.query(UserTemplate).filter(UserTemplate.id == template_id).first()
            if tpl:
                template_path = tpl.file_path
        finally:
            db.close()
    
    try:
        markdown_to_docx(
            markdown=markdown,
            output_path=str(output_path),
            title=title,
            template_path=template_path,
            sections_data=sections_data,
        )
        filename_for_download = f"{title}.docx".replace("/", "_").replace(" ", "_")
        return FileResponse(
            path=str(output_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename_for_download,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"docx 생성 실패: {str(e)}")'''

new_export = '''@app.post("/api/lesson/export-docx")
async def api_export_lesson_docx(body: dict):
    """
    지도안을 .docx 파일로 다운로드 (양식이 있으면 Gemini로 지능적 매핑)
    
    body: {
        "markdown": "...",
        "title": "...",
        "template_id": null (또는 양식 ID),
        "age": 4 (선택, Gemini 매핑 보조용),
        "duration": 40 (선택),
        "search_query": "..." (선택)
    }
    """
    from services.docx_writer import markdown_to_docx
    
    markdown = body.get("markdown", "")
    title = body.get("title", "지도안")
    template_id = body.get("template_id")
    
    output_path = TEMPLATES_DIR / f"output_{uuid.uuid4().hex}.docx"
    template_path = None
    sections_data = None
    
    if template_id:
        from database import SessionLocal
        db = SessionLocal()
        try:
            tpl = db.query(UserTemplate).filter(UserTemplate.id == template_id).first()
            if tpl:
                template_path = tpl.file_path
                # 양식의 섹션 목록 가져오기
                tpl_sections = json.loads(tpl.sections_json) if tpl.sections_json else []
                
                # Gemini로 지능적 매핑
                if tpl_sections:
                    try:
                        from services.template_filler import smart_fill_with_gemini
                        lesson_meta = {
                            "age": body.get("age"),
                            "duration": body.get("duration"),
                            "search_query": body.get("search_query"),
                        }
                        # None 값 제거
                        lesson_meta = {k: v for k, v in lesson_meta.items() if v is not None}
                        sections_data = smart_fill_with_gemini(
                            lesson_markdown=markdown,
                            template_sections=tpl_sections,
                            lesson_meta=lesson_meta,
                        )
                        print(f"✅ Gemini 매핑 완료: {len(sections_data)}개 섹션")
                    except Exception as e:
                        print(f"⚠️ Gemini 매핑 실패, 기본 채우기로 폴백: {e}")
                        sections_data = body.get("sections_data")
        finally:
            db.close()
    
    try:
        markdown_to_docx(
            markdown=markdown,
            output_path=str(output_path),
            title=title,
            template_path=template_path,
            sections_data=sections_data,
        )
        filename_for_download = f"{title}.docx".replace("/", "_").replace(" ", "_")
        return FileResponse(
            path=str(output_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename_for_download,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"docx 생성 실패: {str(e)}")'''

if old_export in main_code:
    main_code = main_code.replace(old_export, new_export)
    MAIN_PATH.write_text(main_code, encoding="utf-8")
    print("✅ main.py: export-docx API에 Gemini 매핑 통합")
else:
    print("⚠️  main.py: export-docx 패턴 못 찾음 (이미 패치됐을 수 있음)")


print("\n" + "=" * 50)
print("🎉 지능적 양식 채우기 패치 완료!")
print("=" * 50)
print("\n동작 방식:")
print("  1. 양식 적용해서 .docx 다운로드 요청")
print("  2. 백엔드: Gemini가 양식 섹션 의미를 이해해서 지도안 내용 매핑")
print("     - '단원' → 지도안 활동 제목")
print("     - '학습목표' → 지도안 목표 부분")
print("     - '도입/전개/정리' → 지도안 단계별 내용")
print("     - '준비물' → 지도안 준비물")
print("     - '지도교사명' 등 메타 정보 → '(작성 필요)' 표시")
print("  3. 양식의 표 셀에 매핑된 내용 자동 삽입")
print("\n주의: Gemini 호출 1회 추가 (약 3-5초 소요)")
