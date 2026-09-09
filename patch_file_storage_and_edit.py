#!/usr/bin/env python3
"""
patch_file_storage_and_edit.py
================================
1. 명칭 변경: '적용 이력에 저장' → '이 파일 저장'
2. 사이드바에 '📁 파일 보관함' 메뉴 추가
3. 파일 보관함 페이지 신규 (사용자의 모든 양식 적용 파일 모음)
4. 셀 카드 직접 편집 기능 (✏️ 클릭하면 인라인 수정)
"""
from pathlib import Path

MAIN_PATH = Path("main.py")
HTML_PATH = Path("static/edu-bridge-full.html")


# ============================================================
# 1) main.py: 사용자 전체 파일 목록 API 추가
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

if "/api/applied-templates/all" not in main_code:
    new_api = '''

@app.get("/api/applied-templates/all")
def api_get_all_applied(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """현재 사용자의 모든 양식 적용 파일 (보관함용)"""
    results = (
        db.query(AppliedTemplate, SavedLesson)
        .join(SavedLesson, AppliedTemplate.saved_lesson_id == SavedLesson.id)
        .filter(SavedLesson.user_id == current_user.id)
        .order_by(AppliedTemplate.created_at.desc())
        .all()
    )
    output = []
    for applied, lesson in results:
        fills = json.loads(applied.fills_json) if applied.fills_json else []
        output.append({
            "id": applied.id,
            "template_id": applied.user_template_id,
            "template_name": applied.template_name,
            "lesson_title": lesson.title,
            "lesson_search_query": lesson.search_query,
            "country_code": lesson.country_code,
            "age": lesson.age,
            "duration": lesson.duration,
            "saved_lesson_id": applied.saved_lesson_id,
            "fills_count": len(fills),
            "created_at": applied.created_at.isoformat(),
        })
    return output

'''
    main_code = main_code.replace(
        '\n@app.get("/api/health")',
        new_api + '\n@app.get("/api/health")'
    )
    MAIN_PATH.write_text(main_code, encoding="utf-8")
    print("✅ main.py: /api/applied-templates/all API 추가")


# ============================================================
# 2) HTML 패치
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_file_storage")
backup.write_text(html, encoding="utf-8")
print(f"✅ HTML 백업: {backup}")


# 2-1) 사이드바에 '파일 보관함' 메뉴 추가 ('내 양식' 다음)
old_nav_part = '''    <button class="nav-item" onclick="showPage('templates', this)">
      <span class="nav-icon">📄</span><span>내 양식</span>
    </button>'''
new_nav_part = '''    <button class="nav-item" onclick="showPage('templates', this)">
      <span class="nav-icon">📄</span><span>내 양식</span>
    </button>
    <button class="nav-item" onclick="showPage('filestorage', this)">
      <span class="nav-icon">📁</span><span>파일 보관함</span>
    </button>'''

if old_nav_part in html and "showPage('filestorage'" not in html:
    html = html.replace(old_nav_part, new_nav_part)
    print("✅ 사이드바 '파일 보관함' 메뉴 추가")


# 2-2) 파일 보관함 페이지 추가
old_marker = '<!-- ════ COMMUNITY PAGE ════ -->'
new_marker = '''<!-- ════ FILE STORAGE PAGE ════ -->
  <div class="page" id="page-filestorage">
    <div style="padding:2rem;">
      <div class="page-title">📁 파일 보관함</div>
      <div class="page-sub">양식에 적용해서 저장한 지도안 파일들입니다</div>

      <div id="fileStorageNeedLogin" style="display:none; text-align:center; padding:3rem 1rem;">
        <div style="font-size:48px; margin-bottom:16px;">🔐</div>
        <div style="font-size:16px; font-weight:700; color:var(--g7); margin-bottom:8px;">로그인이 필요합니다</div>
        <button class="btn-primary" onclick="showModal()">로그인 / 회원가입</button>
      </div>

      <div id="fileStorageEmpty" style="display:none; text-align:center; padding:3rem 1rem;">
        <div style="font-size:48px; margin-bottom:16px;">📂</div>
        <div style="font-size:16px; font-weight:700; color:var(--g7); margin-bottom:8px;">저장된 파일이 없습니다</div>
        <div style="font-size:13px; color:var(--g5);">지도안 생성 → 양식 적용 → 💾 이 파일 저장</div>
      </div>

      <div id="fileStorageContent">
        <div style="margin-bottom:1rem;">
          <input type="text" id="fileSearchInput" placeholder="🔍 양식 이름 또는 지도안 제목으로 검색..." oninput="filterFileStorage()" style="width:100%; max-width:400px; height:38px; padding:0 14px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; background:var(--white); outline:none;">
        </div>
        <ul class="log-list" id="fileStorageList"></ul>
      </div>
    </div>
  </div>

  <!-- ════ COMMUNITY PAGE ════ -->'''

if old_marker in html and 'id="page-filestorage"' not in html:
    html = html.replace(old_marker, new_marker)
    print("✅ 파일 보관함 페이지 추가")


# 2-3) "적용 이력에 저장" → "이 파일 저장" 명칭 변경
html = html.replace(
    "💾 적용 이력에 저장",
    "💾 이 파일 저장"
)
print("✅ '적용 이력에 저장' → '이 파일 저장' 변경")


# 2-4) "이전에 적용한 양식" → "이 지도안의 저장된 파일들"
html = html.replace(
    "📎 이전에 적용한 양식",
    "💾 이 지도안의 저장된 파일들"
)
print("✅ '이전에 적용한 양식' → '이 지도안의 저장된 파일들' 변경")


# 2-5) JS 추가 - 파일 보관함 로드 + 셀 직접 편집
new_js = '''

// ============================================================
// 파일 보관함 (Files Storage)
// ============================================================

let _allAppliedFiles = [];

async function loadFileStorage() {
  const token = localStorage.getItem('auth_token');
  const needLogin = document.getElementById('fileStorageNeedLogin');
  const empty = document.getElementById('fileStorageEmpty');
  const content = document.getElementById('fileStorageContent');

  if (!needLogin) return;

  if (!token) {
    needLogin.style.display = 'block';
    empty.style.display = 'none';
    content.style.display = 'none';
    return;
  }
  needLogin.style.display = 'none';

  try {
    const r = await fetch(API_BASE + '/api/applied-templates/all', {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (r.status === 401) {
      needLogin.style.display = 'block';
      content.style.display = 'none';
      return;
    }
    _allAppliedFiles = await r.json();
    if (!_allAppliedFiles.length) {
      empty.style.display = 'block';
      content.style.display = 'none';
      return;
    }
    empty.style.display = 'none';
    content.style.display = 'block';
    renderFileStorageList(_allAppliedFiles);
  } catch (e) {
    console.error('파일 보관함 로드 실패:', e);
  }
}

function filterFileStorage() {
  const q = document.getElementById('fileSearchInput').value.trim().toLowerCase();
  if (!q) {
    renderFileStorageList(_allAppliedFiles);
    return;
  }
  const filtered = _allAppliedFiles.filter(f =>
    (f.template_name || '').toLowerCase().includes(q) ||
    (f.lesson_title || '').toLowerCase().includes(q) ||
    (f.lesson_search_query || '').toLowerCase().includes(q)
  );
  renderFileStorageList(filtered);
}

function renderFileStorageList(files) {
  const list = document.getElementById('fileStorageList');
  if (!list) return;
  if (!files.length) {
    list.innerHTML = '<li style="padding:2rem; text-align:center; color:var(--g5);">검색 결과가 없습니다.</li>';
    return;
  }
  list.innerHTML = files.map(f => {
    const flag = FLAGS[f.country_code] || '🌐';
    const date = new Date(f.created_at).toLocaleDateString('ko-KR');
    return `
      <li class="log-item">
        <div class="log-thumb" style="background:linear-gradient(135deg, var(--teal-3), var(--teal));color:var(--white);">📄</div>
        <div class="log-content">
          <div class="log-title">${escapeHtml(f.lesson_title || '지도안')}</div>
          <div class="log-meta">양식: <b>${escapeHtml(f.template_name)}</b> · ${flag} · 만 ${f.age}세 · ${f.duration}분</div>
          <div style="font-size:11px; color:var(--g5); margin-top:6px;">
            🔍 검색어: ${escapeHtml(f.lesson_search_query || '')}
          </div>
          <div style="display:flex; gap:6px; margin-top:10px;">
            <button class="log-action-btn" style="background:var(--teal-3);color:var(--teal-dark, #085041);border:none;" onclick="openAppliedTemplate(${f.id})">👁 보기·수정</button>
            <button class="log-action-btn" style="background:var(--teal);color:var(--white);border:none;font-weight:700;" onclick="redownloadApplied(${f.id})">📥 재다운로드</button>
            <button class="log-action-btn" style="background:var(--g1);color:var(--coral);border:1px solid var(--g2);" onclick="deleteAppliedFromStorage(${f.id})">🗑</button>
          </div>
        </div>
        <div class="log-right">
          <div class="log-date">${date}</div>
          <div style="font-size:11px; color:var(--g5);">${f.fills_count}개 셀</div>
        </div>
      </li>
    `;
  }).join('');
}

async function deleteAppliedFromStorage(appliedId) {
  if (!confirm('이 파일을 삭제하시겠습니까?')) return;
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/applied-templates/' + appliedId, {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (!r.ok) throw new Error('삭제 실패');
    showToast('삭제됨', 'info');
    loadFileStorage();
  } catch (e) {
    showToast('실패: ' + e.message, 'error');
  }
}

// showPage 후크: filestorage 진입 시 로드
const _origShowPageFile = showPage;
showPage = function(id, navEl, section) {
  _origShowPageFile(id, navEl, section);
  if (id === 'filestorage') loadFileStorage();
};


// ============================================================
// 셀 직접 편집 (Inline Edit)
// ============================================================

// renderFillsList를 인라인 편집 가능하게 재정의
const _origRenderFillsList = renderFillsList;
renderFillsList = function(fills, changedIndices) {
  const container = document.getElementById('fillsCellsList');
  if (!fills.length) {
    container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--g5);">채워진 셀이 없습니다.</div>';
    return;
  }
  
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
        <div id="cellCard_${item._idx}" data-idx="${item._idx}" style="background:var(--white); border:1px solid ${isChanged ? 'var(--teal)' : 'var(--g2)'}; border-radius:8px; padding:10px 12px; margin-bottom:6px; ${isChanged ? 'box-shadow:0 0 0 2px rgba(29,158,117,0.15);' : ''} position:relative;">
          <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:8px;">
            <div style="flex:1;">
              <div style="font-size:11px; font-weight:600; color:var(--g6); margin-bottom:4px;">${escapeHtml(item.label || '(라벨 없음)')}${badge}</div>
              <div id="cellContent_${item._idx}" style="font-size:13px; color:var(--g9); line-height:1.5; white-space:pre-wrap; word-break:break-word;">${escapeHtml(item.content || '(비어있음)')}</div>
            </div>
            <button onclick="startCellEdit(${item._idx})" title="직접 편집" style="flex-shrink:0; padding:4px 8px; border:1px solid var(--g2); border-radius:6px; background:var(--white); cursor:pointer; font-size:11px; color:var(--g6); transition:all 0.15s;" onmouseover="this.style.background='var(--g1)'" onmouseout="this.style.background='var(--white)'">✏️</button>
          </div>
        </div>
      `;
    }
    html += '</div>';
  }
  
  container.innerHTML = html;
};

function startCellEdit(idx) {
  const card = document.getElementById('cellCard_' + idx);
  if (!card) return;
  
  const fill = _currentFills[idx];
  if (!fill) return;
  
  const currentContent = fill.content || '';
  const label = fill.label || '(라벨 없음)';
  
  card.innerHTML = `
    <div style="font-size:11px; font-weight:600; color:var(--g6); margin-bottom:6px;">${escapeHtml(label)} <span style="color:var(--teal); font-size:10px;">편집 중</span></div>
    <textarea id="cellEditInput_${idx}" style="width:100%; min-height:80px; padding:10px 12px; border:2px solid var(--teal); border-radius:6px; font-family:var(--font); font-size:13px; line-height:1.5; outline:none; resize:vertical; box-sizing:border-box;">${escapeHtml(currentContent)}</textarea>
    <div style="display:flex; gap:6px; margin-top:8px; justify-content:flex-end;">
      <button onclick="cancelCellEdit(${idx})" style="padding:5px 12px; border:1px solid var(--g2); border-radius:6px; background:var(--white); cursor:pointer; font-size:12px; color:var(--g7);">취소</button>
      <button onclick="saveCellEdit(${idx})" style="padding:5px 14px; border:none; border-radius:6px; background:var(--teal); color:var(--white); cursor:pointer; font-size:12px; font-weight:700;">저장</button>
    </div>
  `;
  
  // textarea 자동 포커스 + 끝으로 커서
  const ta = document.getElementById('cellEditInput_' + idx);
  if (ta) {
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
    // 자동 높이 조절
    ta.style.height = 'auto';
    ta.style.height = Math.max(80, ta.scrollHeight) + 'px';
    ta.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = Math.max(80, this.scrollHeight) + 'px';
    });
  }
}

function cancelCellEdit(idx) {
  // 전체 다시 렌더링 (변경된 인덱스 유지 X, 그냥 원래 상태로)
  renderFillsList(_currentFills, []);
}

async function saveCellEdit(idx) {
  const ta = document.getElementById('cellEditInput_' + idx);
  if (!ta) return;
  const newContent = ta.value;
  
  if (!_currentFills[idx]) return;
  _currentFills[idx].content = newContent;
  
  // 화면 다시 그리기 (이 셀을 changed로 표시)
  renderFillsList(_currentFills, [idx]);
  
  // 저장된 이력 수정 모드면 백엔드에도 즉시 반영
  if (_currentAppliedId) {
    const token = localStorage.getItem('auth_token');
    try {
      await fetch(API_BASE + '/api/applied-templates/' + _currentAppliedId, {
        method: 'PUT',
        headers: {'Content-Type':'application/json', 'Authorization': 'Bearer ' + token},
        body: JSON.stringify({fills: _currentFills}),
      });
      showToast('셀이 수정되어 자동 저장되었습니다.', 'success');
    } catch (e) {
      console.error('자동 저장 실패:', e);
    }
  } else {
    showToast('셀이 수정되었습니다. (다운로드 또는 저장 시 반영됨)', 'success');
  }
}
'''

if 'function loadFileStorage' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + new_js + '\n' + html[last_close:]
        print("✅ 파일 보관함 + 셀 편집 JS 추가")

HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 50)
print("🎉 패치 완료!")
print("=" * 50)
print("\n변경 내용:")
print("  1. ✏️ '적용 이력에 저장' → '이 파일 저장'")
print("  2. ✏️ '이전에 적용한 양식' → '이 지도안의 저장된 파일들'")
print("  3. 📁 사이드바에 '파일 보관함' 메뉴 추가")
print("  4. 새 페이지: 파일 보관함 (모든 양식 적용 파일 모음)")
print("     - 검색 기능 포함")
print("     - 각 파일: 보기·수정 / 재다운로드 / 삭제")
print("  5. 양식 적용 미리보기 모달의 각 셀 카드에 ✏️ 버튼")
print("     - 클릭 시 인라인 텍스트 편집")
print("     - 텍스트 영역으로 변환 → 저장/취소")
print("     - 저장된 파일의 경우 자동으로 백엔드 반영")
print("\n브라우저 강제 새로고침(Cmd+Shift+R) 후 테스트하세요!")
