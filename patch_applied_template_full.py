#!/usr/bin/env python3
"""
patch_applied_template_full.py
================================
양식 적용 결과 (A) 수정 채팅 + (B) 스크랩 저장 통합 패치

신규 기능:
1. 양식 적용 결과를 셀별로 미리보기/수정 가능한 모달
2. 한 지도안에 여러 양식 적용 이력 보관
3. 저장된 결과 재다운로드 / 수정 / 삭제
"""
from pathlib import Path

BACKEND = Path(".")
SERVICES = BACKEND / "services"
MAIN_PATH = BACKEND / "main.py"
DB_PATH = BACKEND / "database.py"
HTML_PATH = BACKEND / "static" / "edu-bridge-full.html"


# ============================================================
# 1) database.py: AppliedTemplate 테이블 추가
# ============================================================
db_code = DB_PATH.read_text(encoding="utf-8")

if "class AppliedTemplate" not in db_code:
    insertion = "# ============================================================\n# 데이터베이스 초기화"
    new_table = '''
class AppliedTemplate(Base):
    """저장된 지도안에 양식을 적용한 이력 (스크랩)"""
    __tablename__ = "applied_templates"

    id = Column(Integer, primary_key=True, index=True)
    saved_lesson_id = Column(Integer, ForeignKey("saved_lessons.id"), nullable=False)
    user_template_id = Column(Integer, ForeignKey("user_templates.id"), nullable=True)
    template_name = Column(String(200), nullable=False)
    # fills_json: [{"table_idx":0, "row":0, "col":1, "content":"...", "label":"단원"}, ...]
    fills_json = Column(Text, nullable=False)
    personal_info_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


'''
    db_code = db_code.replace(insertion, new_table + insertion)
    DB_PATH.write_text(db_code, encoding="utf-8")
    print("✅ database.py: AppliedTemplate 테이블 추가")
else:
    print("ℹ️  AppliedTemplate 이미 존재")


# ============================================================
# 2) services/applied_template_service.py 신규 생성
# ============================================================
SERVICE_CODE = '''"""
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
        history_text = "\\n\\n## 이전 대화\\n"
        for msg in conversation_history[-6:]:
            role = "교사" if msg.get("role") == "user" else "AI"
            history_text += f"[{role}]: {msg.get('content', '')[:200]}\\n"

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
'''

(SERVICES / "applied_template_service.py").write_text(SERVICE_CODE, encoding="utf-8")
print("✅ services/applied_template_service.py 생성")


# ============================================================
# 3) main.py: 신규 API들 추가
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

# UserTemplate 옆에 AppliedTemplate import 추가
if "AppliedTemplate" not in main_code:
    main_code = main_code.replace(
        "User, SavedLesson, UserTemplate,",
        "User, SavedLesson, UserTemplate, AppliedTemplate,"
    )
    print("✅ main.py: AppliedTemplate import 추가")

# 새 API 블록
applied_apis = '''

# ============================================================
# 양식 적용 결과 미리보기 / 수정 / 스크랩 API
# ============================================================

@app.post("/api/lesson/preview-fills")
async def api_preview_fills(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    지도안을 양식에 채울 내용 미리 계산 (다운로드 전에 미리보기)

    body: {markdown, title, template_id, age, duration, search_query, personal_info}
    """
    template_id = body.get("template_id")
    markdown = body.get("markdown", "")

    if not template_id:
        raise HTTPException(status_code=400, detail="template_id 필요")

    tpl = db.query(UserTemplate).filter(
        UserTemplate.id == template_id,
        UserTemplate.user_id == current_user.id
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="양식 없음")

    if not tpl.analysis_json:
        raise HTTPException(status_code=400, detail="이 양식은 심층 분석이 안 되어있습니다. 재업로드하세요.")

    analysis = json.loads(tpl.analysis_json)
    lesson_meta = {
        "age": body.get("age"),
        "duration": body.get("duration"),
        "search_query": body.get("search_query"),
    }
    lesson_meta = {k: v for k, v in lesson_meta.items() if v is not None}
    personal_info = body.get("personal_info") or {}

    from services.template_analyzer import fill_cells_with_lesson
    position_fills = fill_cells_with_lesson(
        template_analysis=analysis,
        lesson_markdown=markdown,
        lesson_meta=lesson_meta,
        personal_info=personal_info,
    )

    # 라벨 정보와 함께 리스트로 변환
    cells = analysis.get("cells", [])
    fills_with_labels = []
    for (ti, ri, ci), content in position_fills.items():
        # 해당 위치의 셀 정보 찾기
        cell_info = None
        for c in cells:
            if c.get("table_idx") == ti and c.get("row") == ri and c.get("col") == ci:
                cell_info = c
                break
        label = cell_info.get("for_label", "") if cell_info else ""
        category = cell_info.get("category", "") if cell_info else ""
        fills_with_labels.append({
            "table_idx": ti, "row": ri, "col": ci,
            "content": content,
            "label": label,
            "category": category,
        })

    # 표/위치 순으로 정렬
    fills_with_labels.sort(key=lambda x: (x["table_idx"], x["row"], x["col"]))

    return {
        "fills": fills_with_labels,
        "template_name": tpl.template_name,
        "template_id": tpl.id,
        "personal_info": personal_info,
    }


@app.post("/api/lesson/refine-fills")
async def api_refine_fills(body: dict, current_user: User = Depends(get_current_user)):
    """양식 채워진 결과를 채팅으로 수정"""
    from services.applied_template_service import refine_fills_with_chat

    current_fills = body.get("current_fills", [])
    refine_request = body.get("refine_request", "")
    conversation_history = body.get("conversation_history", [])

    if not current_fills or not refine_request:
        raise HTTPException(status_code=400, detail="current_fills와 refine_request 필요")

    result = refine_fills_with_chat(
        current_fills=current_fills,
        refine_request=refine_request,
        conversation_history=conversation_history,
    )
    return result


@app.post("/api/lesson/export-from-fills")
async def api_export_from_fills(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    이미 계산된 fills로 .docx 생성 (수정 후 다운로드용)

    body: {title, template_id, fills}
    """
    template_id = body.get("template_id")
    title = body.get("title", "지도안")
    fills = body.get("fills", [])

    tpl = db.query(UserTemplate).filter(
        UserTemplate.id == template_id,
        UserTemplate.user_id == current_user.id
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="양식 없음")

    # fills 리스트 → 위치 dict로 변환
    position_fills = {
        (f["table_idx"], f["row"], f["col"]): f["content"]
        for f in fills if f.get("content")
    }

    output_path = TEMPLATES_DIR / f"output_{uuid.uuid4().hex}.docx"

    from services.docx_writer import fill_template_by_positions
    try:
        fill_template_by_positions(tpl.file_path, str(output_path), position_fills)
        filename_for_download = f"{title}.docx".replace("/", "_").replace(" ", "_")
        return FileResponse(
            path=str(output_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename_for_download,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"생성 실패: {str(e)}")


@app.post("/api/applied-templates/save")
async def api_save_applied_template(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """양식 적용 결과를 SavedLesson에 연결해서 저장"""
    saved_lesson_id = body.get("saved_lesson_id")
    template_id = body.get("template_id")
    fills = body.get("fills", [])
    personal_info = body.get("personal_info", {})

    if not saved_lesson_id or not template_id:
        raise HTTPException(status_code=400, detail="saved_lesson_id, template_id 필요")

    # SavedLesson 소유권 확인
    lesson = db.query(SavedLesson).filter(
        SavedLesson.id == saved_lesson_id,
        SavedLesson.user_id == current_user.id
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="저장된 지도안 없음")

    tpl = db.query(UserTemplate).filter(
        UserTemplate.id == template_id,
        UserTemplate.user_id == current_user.id
    ).first()
    template_name = tpl.template_name if tpl else "(삭제된 양식)"

    applied = AppliedTemplate(
        saved_lesson_id=saved_lesson_id,
        user_template_id=template_id,
        template_name=template_name,
        fills_json=json.dumps(fills, ensure_ascii=False),
        personal_info_json=json.dumps(personal_info, ensure_ascii=False) if personal_info else None,
    )
    db.add(applied)
    db.commit()
    db.refresh(applied)
    return {"id": applied.id, "message": "양식 적용 결과가 저장되었습니다."}


@app.get("/api/lessons/{lesson_id}/applied-templates")
def api_get_applied_templates(lesson_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """저장된 지도안의 양식 적용 이력 조회"""
    lesson = db.query(SavedLesson).filter(
        SavedLesson.id == lesson_id,
        SavedLesson.user_id == current_user.id
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="지도안 없음")

    applied = db.query(AppliedTemplate).filter(
        AppliedTemplate.saved_lesson_id == lesson_id
    ).order_by(AppliedTemplate.created_at.desc()).all()

    result = []
    for a in applied:
        fills = json.loads(a.fills_json) if a.fills_json else []
        result.append({
            "id": a.id,
            "template_id": a.user_template_id,
            "template_name": a.template_name,
            "fills_count": len(fills),
            "created_at": a.created_at.isoformat(),
        })
    return result


@app.get("/api/applied-templates/{applied_id}")
def api_get_applied_detail(applied_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """양식 적용 이력 상세 (수정/재다운로드용)"""
    applied = db.query(AppliedTemplate).join(SavedLesson).filter(
        AppliedTemplate.id == applied_id,
        SavedLesson.user_id == current_user.id
    ).first()
    if not applied:
        raise HTTPException(status_code=404, detail="없음")

    return {
        "id": applied.id,
        "template_id": applied.user_template_id,
        "template_name": applied.template_name,
        "fills": json.loads(applied.fills_json) if applied.fills_json else [],
        "personal_info": json.loads(applied.personal_info_json) if applied.personal_info_json else {},
        "created_at": applied.created_at.isoformat(),
    }


@app.put("/api/applied-templates/{applied_id}")
def api_update_applied(applied_id: int, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """수정된 fills로 양식 적용 이력 업데이트"""
    applied = db.query(AppliedTemplate).join(SavedLesson).filter(
        AppliedTemplate.id == applied_id,
        SavedLesson.user_id == current_user.id
    ).first()
    if not applied:
        raise HTTPException(status_code=404, detail="없음")
    fills = body.get("fills")
    if fills is not None:
        applied.fills_json = json.dumps(fills, ensure_ascii=False)
        db.commit()
    return {"message": "업데이트 완료"}


@app.delete("/api/applied-templates/{applied_id}")
def api_delete_applied(applied_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """양식 적용 이력 삭제"""
    applied = db.query(AppliedTemplate).join(SavedLesson).filter(
        AppliedTemplate.id == applied_id,
        SavedLesson.user_id == current_user.id
    ).first()
    if not applied:
        raise HTTPException(status_code=404, detail="없음")
    db.delete(applied)
    db.commit()
    return {"message": "삭제됨"}

'''

if "/api/lesson/preview-fills" not in main_code:
    main_code = main_code.replace(
        '\n@app.get("/api/health")',
        applied_apis + '\n@app.get("/api/health")'
    )
    MAIN_PATH.write_text(main_code, encoding="utf-8")
    print("✅ main.py: 양식 적용 관련 API 7개 추가")
else:
    print("ℹ️  양식 적용 API 이미 존재")


# ============================================================
# 4) HTML 패치 - 미리보기/수정 모달 + 적용 이력 UI
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_applied_full")
backup.write_text(html, encoding="utf-8")
print(f"✅ HTML 백업: {backup}")

# 4-1) 양식 적용 미리보기/수정 모달
preview_modal = '''
<!-- 양식 적용 결과 미리보기/수정 모달 -->
<div id="fillsPreviewModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10000; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeFillsPreview();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:92%; max-width:1100px; max-height:92vh; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3); display:flex; flex-direction:column;">
    <!-- 헤더 -->
    <div style="padding:20px 24px; border-bottom:1px solid var(--g2); display:flex; align-items:center; justify-content:space-between;">
      <div>
        <div style="font-size:17px; font-weight:700; color:var(--g9);">📝 양식 적용 결과</div>
        <div id="fillsPreviewSubtitle" style="font-size:12px; color:var(--g5); margin-top:3px;"></div>
      </div>
      <button onclick="closeFillsPreview()" style="width:34px; height:34px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px; color:var(--g7);">×</button>
    </div>

    <!-- 본문 (좌측: 셀 카드, 우측: 채팅) -->
    <div style="flex:1; overflow:hidden; display:flex; gap:1px; background:var(--g2);">
      <!-- 셀 목록 -->
      <div style="flex:1.4; background:var(--g0); overflow-y:auto; padding:20px;">
        <div id="fillsCellsList"></div>
      </div>

      <!-- 채팅 -->
      <div style="flex:1; background:var(--white); display:flex; flex-direction:column;">
        <div style="padding:14px 18px; border-bottom:1px solid var(--g2); font-size:13px; font-weight:700; color:var(--g8);">💬 수정 요청 채팅</div>
        <div id="fillsChatHistory" style="flex:1; overflow-y:auto; padding:14px 18px;"></div>
        <div style="padding:14px 18px; border-top:1px solid var(--g2);">
          <div style="display:flex; gap:8px;">
            <input type="text" id="fillsChatInput" placeholder="예: 학습 목표를 더 구체적으로" onkeypress="if(event.key==='Enter') sendFillsRefineRequest()" style="flex:1; height:38px; padding:0 12px; border:1.5px solid var(--g2); border-radius:var(--r); font-family:var(--font); font-size:13px; outline:none;">
            <button onclick="sendFillsRefineRequest()" style="padding:0 16px; border:none; border-radius:var(--r); background:var(--teal); color:var(--white); font-family:var(--font); font-size:12px; font-weight:700; cursor:pointer;">전송</button>
          </div>
          <div style="font-size:11px; color:var(--g5); margin-top:6px; line-height:1.5;">
            💡 예시: "전개의 활동 1을 더 구체적으로", "평가 기준에 협동 항목 추가", "학습 목표를 한 줄로 짧게"
          </div>
        </div>
      </div>
    </div>

    <!-- 하단 액션 -->
    <div style="padding:14px 24px; border-top:1px solid var(--g2); display:flex; gap:10px; justify-content:flex-end; flex-wrap:wrap;">
      <button id="fillsSaveBtn" onclick="saveFillsToHistory()" style="padding:10px 16px; border:1.5px solid var(--teal); border-radius:var(--r); background:var(--white); color:var(--teal); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer; display:none;">💾 적용 이력에 저장</button>
      <button onclick="downloadFromFillsModal()" style="padding:10px 18px; border:none; border-radius:var(--r); background:var(--teal); color:var(--white); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">📄 .docx 다운로드</button>
    </div>
  </div>
</div>
'''

if 'id="fillsPreviewModal"' not in html:
    html = html.replace('</script>\n</body>', '</script>\n' + preview_modal + '\n</body>')
    print("✅ HTML: 양식 적용 미리보기 모달 추가")

# 4-2) 저장된 지도안 모달에 "적용 양식" 섹션 추가
old_marker = '<div id="lessonDetailContent" class="lesson-md" style="padding:24px;"></div>'
new_marker = '''<div id="lessonDetailContent" class="lesson-md" style="padding:24px;"></div>

        <!-- 적용한 양식 이력 -->
        <div id="appliedTemplatesSection" style="border-top:1px solid var(--g2); padding:18px 24px; background:#FAFBFC;">
          <div style="font-size:13px; font-weight:700; color:var(--g8); margin-bottom:10px;">📎 이전에 적용한 양식</div>
          <div id="appliedTemplatesList" style="font-size:12px; color:var(--g6);">불러오는 중...</div>
        </div>'''

if old_marker in html and 'id="appliedTemplatesSection"' not in html:
    html = html.replace(old_marker, new_marker)
    print("✅ HTML: 저장된 지도안 모달에 '적용 양식' 섹션 추가")

# 4-3) JS 추가
new_js = '''

// ============================================================
// 양식 적용 결과 미리보기/수정/저장
// ============================================================

let _currentFills = [];           // 현재 미리보기 모달의 fills
let _currentFillsContext = null;  // {template_id, title, personal_info, saved_lesson_id}
let _fillsChatHistory = [];
let _currentAppliedId = null;     // 저장된 적용 이력 ID (수정 모드일 때)

// 양식 적용 결과 미리보기 열기
async function openFillsPreview(context) {
  // context = {markdown, title, template_id, age?, duration?, search_query?, personal_info, saved_lesson_id?}
  const token = localStorage.getItem('auth_token');
  if (!token) { showModal(); return; }

  _currentFillsContext = context;
  _fillsChatHistory = [];
  _currentAppliedId = null;
  
  document.getElementById('fillsCellsList').innerHTML = '<div style="text-align:center; padding:3rem; color:var(--g5);">양식에 채울 내용을 생성하는 중... (약 5-10초)</div>';
  document.getElementById('fillsChatHistory').innerHTML = '';
  document.getElementById('fillsPreviewSubtitle').textContent = '';
  document.getElementById('fillsSaveBtn').style.display = 'none';
  document.getElementById('fillsPreviewModal').style.display = 'block';

  try {
    const r = await fetch(API_BASE + '/api/lesson/preview-fills', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify({
        markdown: context.markdown,
        title: context.title,
        template_id: context.template_id,
        age: context.age,
        duration: context.duration,
        search_query: context.search_query,
        personal_info: context.personal_info || {},
      }),
    });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || '미리보기 실패');
    }
    const data = await r.json();
    _currentFills = data.fills || [];
    document.getElementById('fillsPreviewSubtitle').textContent = `${data.template_name} · ${_currentFills.length}개 셀`;
    renderFillsList(_currentFills, []);
    
    // 저장된 지도안이면 "이력 저장" 버튼 표시
    if (context.saved_lesson_id) {
      document.getElementById('fillsSaveBtn').style.display = 'inline-block';
    }
  } catch (e) {
    document.getElementById('fillsCellsList').innerHTML = '<div style="text-align:center; padding:3rem; color:var(--coral);">❌ ' + e.message + '</div>';
  }
}

// 저장된 적용 이력 열기 (수정/재다운로드용)
async function openAppliedTemplate(appliedId) {
  const token = localStorage.getItem('auth_token');
  if (!token) return;

  _fillsChatHistory = [];
  _currentAppliedId = appliedId;
  
  document.getElementById('fillsCellsList').innerHTML = '<div style="text-align:center; padding:3rem; color:var(--g5);">불러오는 중...</div>';
  document.getElementById('fillsChatHistory').innerHTML = '';
  document.getElementById('fillsSaveBtn').style.display = 'none';
  document.getElementById('fillsPreviewModal').style.display = 'block';

  try {
    const r = await fetch(API_BASE + '/api/applied-templates/' + appliedId, {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (!r.ok) throw new Error('불러오기 실패');
    const data = await r.json();
    _currentFills = data.fills || [];
    _currentFillsContext = {
      template_id: data.template_id,
      title: '지도안',
      personal_info: data.personal_info || {},
    };
    document.getElementById('fillsPreviewSubtitle').textContent = `${data.template_name} · ${_currentFills.length}개 셀 · 저장된 결과 수정 중`;
    renderFillsList(_currentFills, []);
  } catch (e) {
    document.getElementById('fillsCellsList').innerHTML = '<div style="text-align:center; padding:3rem; color:var(--coral);">❌ ' + e.message + '</div>';
  }
}

function closeFillsPreview() {
  document.getElementById('fillsPreviewModal').style.display = 'none';
  _currentFills = [];
  _currentFillsContext = null;
  _fillsChatHistory = [];
  _currentAppliedId = null;
}

function renderFillsList(fills, changedIndices) {
  const container = document.getElementById('fillsCellsList');
  if (!fills.length) {
    container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--g5);">채워진 셀이 없습니다.</div>';
    return;
  }
  
  // 카테고리별 그룹화
  const categoryNames = {
    "personal_info": "👤 개인 정보",
    "lesson_meta": "📌 수업 정보",
    "lesson_content": "📝 수업 내용",
    "evaluation": "✅ 평가",
    "resource": "📦 자료/준비물",
    "": "기타",
  };
  
  const grouped = {};
  fills.forEach((f, idx) => {
    const cat = f.category || "";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push({...f, _idx: idx});
  });
  
  const order = ["personal_info", "lesson_meta", "lesson_content", "evaluation", "resource", ""];
  let html = '';
  
  for (const cat of order) {
    if (!grouped[cat]) continue;
    const items = grouped[cat];
    html += '<div style="margin-bottom:18px;">';
    html += '<div style="font-size:12px; font-weight:700; color:var(--g6); margin-bottom:8px;">' + (categoryNames[cat] || cat) + '</div>';
    for (const item of items) {
      const isChanged = changedIndices.includes(item._idx);
      const badge = isChanged ? '<span style="display:inline-block; margin-left:6px; padding:2px 6px; background:var(--teal); color:white; border-radius:4px; font-size:10px;">수정됨</span>' : '';
      html += `
        <div style="background:var(--white); border:1px solid ${isChanged ? 'var(--teal)' : 'var(--g2)'}; border-radius:8px; padding:10px 12px; margin-bottom:6px; ${isChanged ? 'box-shadow:0 0 0 2px rgba(29,158,117,0.15);' : ''}">
          <div style="font-size:11px; font-weight:600; color:var(--g6); margin-bottom:4px;">${escapeHtml(item.label || '(라벨 없음)')}${badge}</div>
          <div style="font-size:13px; color:var(--g9); line-height:1.5; white-space:pre-wrap;">${escapeHtml(item.content || '(비어있음)')}</div>
        </div>
      `;
    }
    html += '</div>';
  }
  
  container.innerHTML = html;
}

async function sendFillsRefineRequest() {
  const input = document.getElementById('fillsChatInput');
  const request = input.value.trim();
  if (!request) return;
  if (!_currentFills.length) { showToast('수정할 내용이 없습니다.', 'error'); return; }
  
  appendFillsChat('user', request);
  _fillsChatHistory.push({role: 'user', content: request});
  input.value = '';
  
  const loadingId = appendFillsChat('assistant', '⏳ 수정 중...');
  
  try {
    const token = localStorage.getItem('auth_token');
    const r = await fetch(API_BASE + '/api/lesson/refine-fills', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify({
        current_fills: _currentFills,
        refine_request: request,
        conversation_history: _fillsChatHistory,
      }),
    });
    if (!r.ok) throw new Error('수정 실패');
    const data = await r.json();
    _currentFills = data.updated_fills;
    renderFillsList(_currentFills, data.changed_indices || []);
    
    document.getElementById(loadingId).textContent = data.assistant_message || '수정 완료';
    _fillsChatHistory.push({role: 'assistant', content: data.assistant_message || '수정 완료'});
    
    // 저장된 적용 이력 수정 모드면 백엔드에도 업데이트
    if (_currentAppliedId) {
      await fetch(API_BASE + '/api/applied-templates/' + _currentAppliedId, {
        method: 'PUT',
        headers: {'Content-Type':'application/json', 'Authorization': 'Bearer ' + token},
        body: JSON.stringify({fills: _currentFills}),
      });
    }
  } catch (e) {
    document.getElementById(loadingId).textContent = '❌ ' + e.message;
  }
}

function appendFillsChat(role, text) {
  const container = document.getElementById('fillsChatHistory');
  const id = 'fmsg_' + Date.now() + '_' + Math.random().toString(36).slice(2,7);
  const isUser = role === 'user';
  container.insertAdjacentHTML('beforeend', `
    <div style="display:flex; gap:6px; margin-bottom:8px; ${isUser ? 'justify-content:flex-end;' : ''}">
      <div id="${id}" style="max-width:80%; padding:7px 11px; border-radius:10px; font-size:12px; line-height:1.4; ${isUser ? 'background:var(--teal); color:var(--white);' : 'background:var(--g0); color:var(--g9); border:1px solid var(--g2);'}">${escapeHtml(text)}</div>
    </div>
  `);
  container.scrollTop = container.scrollHeight;
  return id;
}

async function downloadFromFillsModal() {
  if (!_currentFills.length) { showToast('다운로드할 내용이 없습니다.', 'error'); return; }
  if (!_currentFillsContext) return;
  
  showToast('.docx 생성 중...', 'info');
  
  try {
    const token = localStorage.getItem('auth_token');
    const r = await fetch(API_BASE + '/api/lesson/export-from-fills', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify({
        title: _currentFillsContext.title || '지도안',
        template_id: _currentFillsContext.template_id,
        fills: _currentFills,
      }),
    });
    if (!r.ok) throw new Error('생성 실패');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (_currentFillsContext.title || '지도안') + '.docx';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('.docx 다운로드 완료!', 'success');
  } catch (e) {
    showToast('실패: ' + e.message, 'error');
  }
}

async function saveFillsToHistory() {
  if (!_currentFillsContext || !_currentFillsContext.saved_lesson_id) {
    showToast('저장된 지도안에서만 가능합니다.', 'error');
    return;
  }
  
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/applied-templates/save', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify({
        saved_lesson_id: _currentFillsContext.saved_lesson_id,
        template_id: _currentFillsContext.template_id,
        fills: _currentFills,
        personal_info: _currentFillsContext.personal_info || {},
      }),
    });
    if (!r.ok) throw new Error('저장 실패');
    showToast('적용 이력에 저장되었습니다!', 'success');
    document.getElementById('fillsSaveBtn').style.display = 'none';
    // 적용 이력 목록 새로고침
    if (_currentSavedLesson) loadAppliedTemplates(_currentSavedLesson.id);
  } catch (e) {
    showToast('저장 실패: ' + e.message, 'error');
  }
}

// 저장된 지도안의 적용 양식 이력 로드
async function loadAppliedTemplates(lessonId) {
  const container = document.getElementById('appliedTemplatesList');
  if (!container) return;
  
  const token = localStorage.getItem('auth_token');
  if (!token) { container.textContent = '로그인 필요'; return; }
  
  try {
    const r = await fetch(API_BASE + '/api/lessons/' + lessonId + '/applied-templates', {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (!r.ok) throw new Error('조회 실패');
    const list = await r.json();
    
    if (!list.length) {
      container.innerHTML = '<div style="color:var(--g5); font-size:12px;">아직 적용한 양식이 없습니다. 양식을 선택하고 다운로드 시 "이력에 저장"하세요.</div>';
      return;
    }
    
    container.innerHTML = list.map(a => {
      const date = new Date(a.created_at).toLocaleDateString('ko-KR') + ' ' + new Date(a.created_at).toLocaleTimeString('ko-KR', {hour:'2-digit',minute:'2-digit'});
      return `
        <div style="background:var(--white); border:1px solid var(--g2); border-radius:8px; padding:10px 12px; margin-bottom:6px; display:flex; align-items:center; gap:10px;">
          <div style="font-size:24px;">📎</div>
          <div style="flex:1;">
            <div style="font-size:13px; font-weight:700; color:var(--g9);">${escapeHtml(a.template_name)}</div>
            <div style="font-size:11px; color:var(--g5); margin-top:2px;">${date} · ${a.fills_count}개 셀</div>
          </div>
          <button onclick="openAppliedTemplate(${a.id})" style="padding:5px 10px; border:1px solid var(--g2); border-radius:var(--r); background:var(--white); font-family:var(--font); font-size:11px; cursor:pointer;">👁 보기·수정</button>
          <button onclick="redownloadApplied(${a.id})" style="padding:5px 10px; border:none; border-radius:var(--r); background:var(--teal); color:var(--white); font-family:var(--font); font-size:11px; cursor:pointer;">📥 재다운로드</button>
          <button onclick="deleteApplied(${a.id})" style="padding:5px 8px; border:1px solid var(--g2); border-radius:var(--r); background:var(--g1); color:var(--coral); font-family:var(--font); font-size:11px; cursor:pointer;">🗑</button>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = '<div style="color:var(--coral); font-size:12px;">불러오기 실패</div>';
  }
}

async function redownloadApplied(appliedId) {
  const token = localStorage.getItem('auth_token');
  showToast('다운로드 중...', 'info');
  try {
    const r1 = await fetch(API_BASE + '/api/applied-templates/' + appliedId, {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    const data = await r1.json();
    
    const r = await fetch(API_BASE + '/api/lesson/export-from-fills', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify({
        title: data.template_name || '지도안',
        template_id: data.template_id,
        fills: data.fills,
      }),
    });
    if (!r.ok) throw new Error('생성 실패');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = (data.template_name || '지도안') + '.docx';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('다운로드 완료!', 'success');
  } catch (e) {
    showToast('실패: ' + e.message, 'error');
  }
}

async function deleteApplied(appliedId) {
  if (!confirm('이 양식 적용 이력을 삭제하시겠습니까?')) return;
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/applied-templates/' + appliedId, {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (!r.ok) throw new Error('삭제 실패');
    showToast('삭제됨', 'info');
    if (_currentSavedLesson) loadAppliedTemplates(_currentSavedLesson.id);
  } catch (e) {
    showToast('실패: ' + e.message, 'error');
  }
}

// 저장된 지도안 상세 보기 시 적용 양식 목록도 같이 로드
const _origViewLessonForApplied = viewLessonDetail;
viewLessonDetail = async function(id) {
  await _origViewLessonForApplied(id);
  loadAppliedTemplates(id);
};

// 기존 .docx 다운로드 흐름 변경: 양식 선택 + 개인정보 → 미리보기 모달
// (기존 actualDownloadDocx를 미리보기 모달로 변경)
const _origActualDownloadDocx = typeof actualDownloadDocx !== 'undefined' ? actualDownloadDocx : null;
if (_origActualDownloadDocx) {
  actualDownloadDocx = async function(context, personalInfo) {
    // 양식 없으면 기존대로 바로 다운로드
    if (!context.templateId) {
      return await _origActualDownloadDocx(context, personalInfo);
    }
    // 양식 있으면 미리보기 모달 열기
    await openFillsPreview({
      ...context,
      template_id: context.templateId,
      personal_info: personalInfo,
      saved_lesson_id: context.saved_lesson_id,
    });
  };
}

// 저장된 지도안에서 다운로드 시 saved_lesson_id 전달
const _origDownloadSavedAsDocx2 = downloadSavedAsDocx;
downloadSavedAsDocx = async function() {
  if (!_currentSavedLesson) { showToast('지도안이 없습니다.', 'error'); return; }
  const tplSelect = document.getElementById('savedLessonTplSelect');
  const templateId = tplSelect && tplSelect.value ? parseInt(tplSelect.value) : null;
  
  await checkAndShowPersonalInfo({
    markdown: _currentSavedLesson.lesson_markdown,
    title: _currentSavedLesson.title || '지도안',
    templateId: templateId,
    age: _currentSavedLesson.age,
    duration: _currentSavedLesson.duration,
    search_query: _currentSavedLesson.search_query,
    saved_lesson_id: _currentSavedLesson.id,
  });
};
'''

if 'function openFillsPreview' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + new_js + '\n' + html[last_close:]
        print("✅ HTML: 양식 적용 결과 JS 추가")

HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 50)
print("🎉 통합 패치 완료!")
print("=" * 50)
print("\n다음 단계:")
print("  rm edubridge.db  (DB 스키마 변경됨)")
print("\n새 흐름:")
print("  [Play-Scanner / 내 지도안 보기]")
print("  ① 양식 선택 후 .docx 다운로드 클릭")
print("  ② 개인정보 입력 모달")
print("  ③ 👉 **양식 적용 미리보기 모달** (셀별 내용 + 채팅 수정)")
print("  ④ '수정 요청' 채팅으로 셀 내용 조정")
print("  ⑤ [📄 다운로드] / [💾 적용 이력에 저장] 선택")
print("")
print("  [저장된 지도안 모달]")
print("  - '📎 이전에 적용한 양식' 섹션에서 이력 확인")
print("  - 각 항목: [👁 보기·수정] [📥 재다운로드] [🗑 삭제]")
