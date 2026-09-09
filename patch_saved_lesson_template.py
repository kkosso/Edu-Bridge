#!/usr/bin/env python3
"""
patch_saved_lesson_template.py
================================
'내 지도안' 페이지의 상세 모달에 양식 적용 다운로드 기능 추가

저장된 지도안 보기 → 양식 선택 → 그 양식에 맞춰 .docx 다운로드
"""
from pathlib import Path

HTML_PATH = Path("static/edu-bridge-full.html")
if not HTML_PATH.exists():
    print("❌ static/edu-bridge-full.html 없음")
    exit(1)

html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_saved_tpl")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업 생성: {backup}")


# ============================================================
# 1) 지도안 상세 모달 헤더 부분 교체 - 양식 선택 + 다운로드 추가
# ============================================================
old_header = '''<div style="display:flex; align-items:center; justify-content:space-between; padding:20px 24px; border-bottom:1px solid var(--g2); position:sticky; top:0; background:var(--white); z-index:1;">
        <div id="lessonDetailTitle" style="font-size:18px; font-weight:700; color:var(--g9);"></div>
        <div style="display:flex; gap:8px;">
          <button onclick="copyLessonDetail()" style="padding:6px 12px; border:1px solid var(--g2); border-radius:var(--r); background:var(--white); font-family:var(--font); font-size:12px; cursor:pointer;">📋 복사</button>
          <button onclick="closeLessonDetail()" style="width:32px; height:32px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px; color:var(--g7);">×</button>
        </div>
      </div>'''

new_header = '''<div style="padding:20px 24px; border-bottom:1px solid var(--g2); position:sticky; top:0; background:var(--white); z-index:1;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
          <div id="lessonDetailTitle" style="font-size:18px; font-weight:700; color:var(--g9);"></div>
          <button onclick="closeLessonDetail()" style="width:32px; height:32px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px; color:var(--g7);">×</button>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
          <button onclick="copyLessonDetail()" style="padding:7px 12px; border:1px solid var(--g2); border-radius:var(--r); background:var(--white); font-family:var(--font); font-size:12px; cursor:pointer; height:34px;">📋 복사</button>
          <button onclick="downloadSavedAsMd()" style="padding:7px 12px; border:1px solid var(--g2); border-radius:var(--r); background:var(--white); font-family:var(--font); font-size:12px; cursor:pointer; height:34px;">📥 .md</button>
          <div style="flex:1; min-width:0;"></div>
          <select id="savedLessonTplSelect" style="height:34px; padding:0 10px; border:1px solid var(--g2); border-radius:var(--r); font-family:var(--font); font-size:12px; background:var(--white); color:var(--g7); outline:none; max-width:200px;">
            <option value="">기본 양식</option>
          </select>
          <button onclick="downloadSavedAsDocx()" style="padding:7px 14px; border:none; border-radius:var(--r); background:var(--teal); color:var(--white); font-family:var(--font); font-size:12px; font-weight:700; cursor:pointer; height:34px;">📄 .docx 다운로드</button>
        </div>
      </div>'''

if old_header in html:
    html = html.replace(old_header, new_header)
    print("✅ 지도안 상세 모달 헤더 교체")
else:
    print("⚠️  지도안 상세 모달 패턴 못 찾음")


# ============================================================
# 2) JS 함수 추가/교체
# ============================================================

# viewLessonDetail 함수에 _currentSavedLesson 저장 추가
old_view = '''async function viewLessonDetail(id) {
  const token = localStorage.getItem('auth_token'); if(!token) return;
  try {
    const r = await fetch(API_BASE+'/api/lessons/'+id, {headers:{'Authorization':'Bearer '+token}});
    const l = await r.json();
    document.getElementById('lessonDetailTitle').textContent = (FLAGS[l.country_code]||'🌐')+' '+l.title;
    const h = typeof marked!=='undefined' ? marked.parse(l.lesson_markdown) : '<pre>'+escapeHtml(l.lesson_markdown)+'</pre>';
    document.getElementById('lessonDetailContent').innerHTML = h;
    document.getElementById('lessonDetailContent').dataset.markdown = l.lesson_markdown;
    document.getElementById('lessonDetailModal').style.display = 'block';
  } catch(e) { showToast('불러오기 실패','error'); }
}'''

new_view = '''let _currentSavedLesson = null;

async function viewLessonDetail(id) {
  const token = localStorage.getItem('auth_token'); if(!token) return;
  try {
    const r = await fetch(API_BASE+'/api/lessons/'+id, {headers:{'Authorization':'Bearer '+token}});
    const l = await r.json();
    _currentSavedLesson = l;
    document.getElementById('lessonDetailTitle').textContent = (FLAGS[l.country_code]||'🌐')+' '+l.title;
    const h = typeof marked!=='undefined' ? marked.parse(l.lesson_markdown) : '<pre>'+escapeHtml(l.lesson_markdown)+'</pre>';
    document.getElementById('lessonDetailContent').innerHTML = h;
    document.getElementById('lessonDetailContent').dataset.markdown = l.lesson_markdown;
    document.getElementById('lessonDetailModal').style.display = 'block';
    // 양식 드롭다운 채우기
    populateSavedLessonTplSelect();
  } catch(e) { showToast('불러오기 실패','error'); }
}

async function populateSavedLessonTplSelect() {
  const sel = document.getElementById('savedLessonTplSelect');
  if (!sel) return;
  const token = localStorage.getItem('auth_token');
  if (!token) return;
  
  // 이미 로드된 _userTemplates 사용, 비어있으면 로드
  if (!_userTemplates || _userTemplates.length === 0) {
    try {
      const r = await fetch(API_BASE + '/api/templates/my', {
        headers: { 'Authorization': 'Bearer ' + token },
      });
      if (r.ok) _userTemplates = await r.json();
    } catch (e) { /* ignore */ }
  }
  
  const opts = ['<option value="">기본 양식</option>'];
  for (const t of (_userTemplates || [])) {
    opts.push('<option value="' + t.id + '">' + escapeHtml(t.template_name) + '</option>');
  }
  sel.innerHTML = opts.join('');
}

function downloadSavedAsMd() {
  if (!_currentSavedLesson) { showToast('지도안이 없습니다.', 'error'); return; }
  const blob = new Blob([_currentSavedLesson.lesson_markdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (_currentSavedLesson.title || '지도안') + '.md';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('.md 다운로드 완료!', 'success');
}

async function downloadSavedAsDocx() {
  if (!_currentSavedLesson) { showToast('지도안이 없습니다.', 'error'); return; }
  
  const tplSelect = document.getElementById('savedLessonTplSelect');
  const templateId = tplSelect && tplSelect.value ? parseInt(tplSelect.value) : null;
  const md = _currentSavedLesson.lesson_markdown;
  const title = _currentSavedLesson.title || '지도안';
  
  showToast(templateId ? '양식 적용해서 docx 생성 중...' : '.docx 생성 중...', 'info');
  
  let sectionsData = null;
  if (templateId) {
    try {
      const r = await fetch(API_BASE + '/api/lesson/parse-sections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markdown: md }),
      });
      sectionsData = await r.json();
    } catch (e) {
      console.error('섹션 파싱 실패:', e);
    }
  }
  
  try {
    const r = await fetch(API_BASE + '/api/lesson/export-docx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        markdown: md,
        title: title,
        template_id: templateId,
        sections_data: sectionsData,
      }),
    });
    if (!r.ok) throw new Error('생성 실패');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = title + '.docx';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('.docx 다운로드 완료!', 'success');
  } catch (e) {
    showToast('다운로드 실패: ' + e.message, 'error');
  }
}'''

if old_view in html:
    html = html.replace(old_view, new_view)
    print("✅ viewLessonDetail + 다운로드 함수 추가")
else:
    print("⚠️  viewLessonDetail 패턴 못 찾음")

HTML_PATH.write_text(html, encoding="utf-8")

print("\n🎉 패치 완료!")
print("\n사용법:")
print("  1. 📋 내 지도안 → 저장된 지도안 [📖 보기] 클릭")
print("  2. 모달 상단에 양식 선택 드롭다운 표시")
print("  3. 원하는 양식 선택 후 [📄 .docx 다운로드] 클릭")
print("  4. 선택한 양식에 지도안 내용이 채워진 .docx 다운로드됨")
