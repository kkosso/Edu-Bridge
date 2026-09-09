#!/usr/bin/env python3
"""
patch_personal_info_modal.py
==============================
.docx 다운로드 전, 양식의 개인정보 입력란을 감지해서 모달로 받기

동작:
1. 양식에서 '교사 이름', '학과', '학교명', '날짜', '장소' 등 개인 정보 필드 감지
2. 다운로드 클릭 시 → 개인정보 입력 모달 표시
3. 사용자가 입력한 정보 + Gemini가 매핑한 지도안 내용 → docx 생성

수행 작업:
1. services/template_filler.py: detect_personal_fields() 함수 추가
2. main.py: /api/templates/{id}/personal-fields API 추가
                 /api/lesson/export-docx에 personal_info 파라미터 추가
3. HTML: 개인정보 입력 모달 + JS 로직
"""
from pathlib import Path

SERVICES = Path("services")
MAIN_PATH = Path("main.py")
HTML_PATH = Path("static/edu-bridge-full.html")

if not all(p.exists() for p in [SERVICES / "template_filler.py", MAIN_PATH, HTML_PATH]):
    print("❌ 필요한 파일이 없습니다.")
    exit(1)


# ============================================================
# 1) template_filler.py에 detect_personal_fields() 추가
# ============================================================
filler_code = (SERVICES / "template_filler.py").read_text(encoding="utf-8")

detect_func = '''

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
'''

if "detect_personal_fields" not in filler_code:
    filler_code += detect_func
    (SERVICES / "template_filler.py").write_text(filler_code, encoding="utf-8")
    print("✅ template_filler.py: detect_personal_fields() 추가")
else:
    print("ℹ️  detect_personal_fields 이미 존재")


# ============================================================
# 2) main.py에 personal-fields API 추가 + export-docx 개선
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

if "/api/templates/{template_id}/personal-fields" not in main_code:
    new_api = '''

@app.get("/api/templates/{template_id}/personal-fields")
def api_get_personal_fields(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """양식의 개인 정보 필드 목록 반환 (교사 이름, 학과 등)"""
    tpl = db.query(UserTemplate).filter(
        UserTemplate.id == template_id,
        UserTemplate.user_id == current_user.id
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="양식을 찾을 수 없습니다.")

    sections = json.loads(tpl.sections_json) if tpl.sections_json else []

    from services.template_filler import detect_personal_fields
    fields = detect_personal_fields(sections)
    return {"fields": fields, "total": len(fields)}

'''
    main_code = main_code.replace(
        '\n@app.get("/api/health")',
        new_api + '\n@app.get("/api/health")'
    )
    print("✅ main.py: /api/templates/{id}/personal-fields API 추가")

# export-docx API에 personal_info 파라미터 처리 추가
# 핵심: sections_data (Gemini 매핑) + personal_info (사용자 입력) 병합
old_smart = '''                if tpl_sections:
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
                        sections_data = body.get("sections_data")'''

new_smart = '''                if tpl_sections:
                    try:
                        from services.template_filler import smart_fill_with_gemini
                        lesson_meta = {
                            "age": body.get("age"),
                            "duration": body.get("duration"),
                            "search_query": body.get("search_query"),
                        }
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
                    
                    # 사용자가 입력한 개인 정보로 덮어쓰기 (Gemini가 추측한 값보다 우선)
                    personal_info = body.get("personal_info") or {}
                    if personal_info and isinstance(sections_data, dict):
                        for label, value in personal_info.items():
                            if value and value.strip():
                                sections_data[label] = value.strip()
                        print(f"✅ 개인정보 {len(personal_info)}개 적용")'''

if old_smart in main_code:
    main_code = main_code.replace(old_smart, new_smart)
    print("✅ main.py: export-docx에 personal_info 처리 추가")
else:
    print("ℹ️  export-docx 패턴 못 찾음 (이미 패치됐을 수 있음)")

MAIN_PATH.write_text(main_code, encoding="utf-8")


# ============================================================
# 3) HTML 패치
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_personal_info")
backup.write_text(html, encoding="utf-8")
print(f"✅ HTML 백업: {backup}")

# 3-1) 개인정보 입력 모달 추가
personal_info_modal = '''
<!-- 개인정보 입력 모달 -->
<div id="personalInfoModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:9999; backdrop-filter:blur(4px);" onclick="if(event.target===this) closePersonalInfoModal();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; max-width:520px; max-height:85vh; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3); display:flex; flex-direction:column;">
    <div style="padding:20px 24px; border-bottom:1px solid var(--g2);">
      <div style="font-size:17px; font-weight:700; color:var(--g9);">📝 양식 정보 입력</div>
      <div style="font-size:12px; color:var(--g5); margin-top:4px;">AI가 작성할 수 없는 개인 정보를 입력해주세요. 비워두면 빈 칸으로 출력됩니다.</div>
    </div>
    <div id="personalInfoFields" style="flex:1; overflow-y:auto; padding:20px 24px;"></div>
    <div style="padding:16px 24px; border-top:1px solid var(--g2); display:flex; gap:10px; justify-content:flex-end;">
      <button onclick="closePersonalInfoModal()" style="padding:9px 16px; border:1px solid var(--g2); border-radius:var(--r); background:var(--white); font-family:var(--font); font-size:13px; cursor:pointer;">취소</button>
      <button onclick="submitPersonalInfoAndDownload()" style="padding:9px 18px; border:none; border-radius:var(--r); background:var(--teal); color:var(--white); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">📄 .docx 생성하기</button>
    </div>
  </div>
</div>
'''

if 'id="personalInfoModal"' not in html:
    # 다른 모달 옆에 추가
    if '<!-- 양식 미리보기 모달 -->' in html:
        html = html.replace('<!-- 양식 미리보기 모달 -->', personal_info_modal + '\n<!-- 양식 미리보기 모달 -->')
    else:
        html = html.replace('</script>\n</body>', '</script>\n' + personal_info_modal + '\n</body>')
    print("✅ HTML: 개인정보 입력 모달 추가")

# 3-2) JS 추가 (downloadAsDocx, downloadSavedAsDocx 인터셉트)
new_js = '''

// ============================================================
// 개인정보 입력 모달 로직
// ============================================================

let _pendingDocxContext = null;  // {markdown, title, templateId, source, age, duration, search_query}

async function checkAndShowPersonalInfo(context) {
  // context = {markdown, title, templateId, age?, duration?, search_query?}
  const token = localStorage.getItem('auth_token');
  
  // 양식이 없으면 바로 다운로드
  if (!context.templateId) {
    return await actualDownloadDocx(context, {});
  }
  
  // 양식이 있으면 개인정보 필드 조회
  try {
    const r = await fetch(API_BASE + '/api/templates/' + context.templateId + '/personal-fields', {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (!r.ok) {
      // 조회 실패해도 다운로드는 진행
      return await actualDownloadDocx(context, {});
    }
    const data = await r.json();
    if (!data.fields || data.fields.length === 0) {
      // 개인 정보 필드가 없으면 바로 다운로드
      return await actualDownloadDocx(context, {});
    }
    // 개인 정보 필드가 있으면 모달 표시
    _pendingDocxContext = context;
    renderPersonalInfoFields(data.fields);
    document.getElementById('personalInfoModal').style.display = 'block';
  } catch (e) {
    console.error('개인정보 필드 조회 실패:', e);
    return await actualDownloadDocx(context, {});
  }
}

function renderPersonalInfoFields(fields) {
  const container = document.getElementById('personalInfoFields');
  
  // 카테고리별로 그룹화
  const grouped = {};
  for (const f of fields) {
    if (!grouped[f.category]) grouped[f.category] = [];
    grouped[f.category].push(f);
  }
  
  let html = '';
  const categoryIcons = {
    "교사 이름": "👨\u200d🏫",
    "학생/실습생 이름": "🎓",
    "학과/소속": "🏛",
    "학교/유치원명": "🏫",
    "수업 일시": "📅",
    "대상 학급": "👶",
    "장소": "📍",
    "결재란": "📋",
  };
  
  for (const [category, list] of Object.entries(grouped)) {
    const icon = categoryIcons[category] || "📝";
    html += '<div style="margin-bottom:18px;">';
    html += '<div style="font-size:12px; font-weight:700; color:var(--g7); margin-bottom:8px;">' + icon + ' ' + category + '</div>';
    for (const f of list) {
      const inputType = f.field_type === 'date' ? 'text' : f.field_type;
      html += `
        <div style="margin-bottom:10px;">
          <label style="display:block; font-size:11px; color:var(--g6); margin-bottom:4px;">${escapeHtml(f.label)}</label>
          <input type="${inputType}" 
                 data-label="${escapeHtml(f.label)}"
                 class="personal-info-input"
                 placeholder="${escapeHtml(f.placeholder || '')}" 
                 style="width:100%; height:38px; padding:0 12px; border:1.5px solid var(--g2); border-radius:var(--r); font-family:var(--font); font-size:13px; background:var(--white); color:var(--g9); outline:none;">
        </div>
      `;
    }
    html += '</div>';
  }
  
  container.innerHTML = html;
}

function closePersonalInfoModal() {
  document.getElementById('personalInfoModal').style.display = 'none';
  _pendingDocxContext = null;
}

async function submitPersonalInfoAndDownload() {
  if (!_pendingDocxContext) return;
  
  // 입력값 수집
  const personalInfo = {};
  document.querySelectorAll('.personal-info-input').forEach(inp => {
    const label = inp.dataset.label;
    const val = inp.value.trim();
    if (label && val) personalInfo[label] = val;
  });
  
  const ctx = _pendingDocxContext;
  closePersonalInfoModal();
  
  await actualDownloadDocx(ctx, personalInfo);
}

async function actualDownloadDocx(context, personalInfo) {
  showToast(context.templateId ? '양식 적용해서 docx 생성 중... (약 5초)' : '.docx 생성 중...', 'info');
  
  try {
    const body = {
      markdown: context.markdown,
      title: context.title,
      template_id: context.templateId,
      personal_info: personalInfo,
    };
    if (context.age) body.age = context.age;
    if (context.duration) body.duration = context.duration;
    if (context.search_query) body.search_query = context.search_query;
    
    const r = await fetch(API_BASE + '/api/lesson/export-docx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error('생성 실패');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (context.title || '지도안') + '.docx';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('.docx 다운로드 완료!', 'success');
  } catch (e) {
    showToast('다운로드 실패: ' + e.message, 'error');
  }
}

// ============================================================
// 기존 다운로드 함수를 인터셉트해서 personal info 체크
// ============================================================
const _origDownloadAsDocx = downloadAsDocx;
downloadAsDocx = async function() {
  const content = document.getElementById('outputContent');
  const md = content.dataset.markdown;
  if (!md) { showToast('지도안이 없습니다.', 'error'); return; }
  const tplSelect = document.getElementById('exportTplSelect');
  const templateId = tplSelect && tplSelect.value ? parseInt(tplSelect.value) : null;
  const card = _state.cards && _state.cards[_state.selectedCardIdx];
  const title = card ? card.card_title : '지도안';
  
  await checkAndShowPersonalInfo({
    markdown: md,
    title: title,
    templateId: templateId,
    age: _state.age,
    duration: _state.duration,
    search_query: _state.searchQuery,
  });
};

const _origDownloadSavedAsDocx = downloadSavedAsDocx;
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
  });
};
'''

if 'function checkAndShowPersonalInfo' not in html:
    # 마지막 </script> 직전에 삽입
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + new_js + '\n' + html[last_close:]
        print("✅ HTML: 개인정보 모달 JS 추가")

HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 50)
print("🎉 개인정보 입력 모달 패치 완료!")
print("=" * 50)
print("\n동작:")
print("  1. 양식 적용 .docx 다운로드 클릭")
print("  2. 양식에 '교사 이름', '학과', '날짜' 등 개인정보 필드가 있으면")
print("     → 입력 모달이 먼저 뜸")
print("  3. 사용자가 정보 입력 → '.docx 생성하기' 클릭")
print("  4. 그 정보 + AI 매핑된 지도안 내용 → docx 생성")
print("\n자동 감지하는 필드:")
print("  - 교사 이름 (지도교사명, 담임교사 등)")
print("  - 학생/실습생 이름")
print("  - 학과/소속")
print("  - 학교/유치원명")
print("  - 수업 일시")
print("  - 대상 학급")
print("  - 장소")
print("  - 결재란 (실습부장, 교감, 교장 등 - 선택)")
