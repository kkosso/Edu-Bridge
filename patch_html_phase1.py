#!/usr/bin/env python3
"""
patch_html_phase1.py
====================
edu-bridge-full.html에 지도안 저장/즐겨찾기 기능을 추가하는 패치 스크립트

사용법:
    cd backend
    python patch_html_phase1.py
"""

import re
from pathlib import Path

HTML_PATH = Path("static/edu-bridge-full.html")

if not HTML_PATH.exists():
    print(f"❌ {HTML_PATH}을 찾을 수 없습니다.")
    exit(1)

# 백업
backup = HTML_PATH.with_suffix(".html.bak_phase1")
html = HTML_PATH.read_text(encoding="utf-8")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업 생성: {backup}")


# ============================================================
# PATCH 1: 지도안 출력 영역에 ⭐ 저장 버튼 추가
# ============================================================
old_output_actions = '''<div class="output-actions">
            <button class="btn-copy" onclick="copyOutput()">📋 복사</button>
            <button class="btn-edit" onclick="downloadLessonPlan()">📥 다운로드</button>
          </div>'''

new_output_actions = '''<div class="output-actions">
            <button class="btn-copy" onclick="copyOutput()">📋 복사</button>
            <button class="btn-edit" onclick="downloadLessonPlan()">📥 다운로드</button>
            <button class="btn-save-lesson" id="btnSaveLesson" onclick="saveLessonPlan()" style="display:none; background:var(--amber-3); color:var(--amber-dark, #854F0B); border:none; padding:6px 14px; border-radius:var(--r); font-family:var(--font); font-size:13px; font-weight:600; cursor:pointer; transition:all 0.15s;">⭐ 저장</button>
          </div>'''

if old_output_actions in html:
    html = html.replace(old_output_actions, new_output_actions)
    print("✅ PATCH 1: 저장 버튼 추가 완료")
else:
    print("⚠️  PATCH 1: output-actions 패턴을 찾을 수 없습니다. 수동 추가 필요.")


# ============================================================
# PATCH 2: 활동 기록지 페이지를 DB 연동 버전으로 교체
# ============================================================
old_activitylog_start = '  <div class="page" id="page-activitylog">'
old_activitylog_end = '  <!-- ════ COMMUNITY PAGE ════ -->'

# 새로운 활동 기록지 페이지
new_activitylog = '''  <div class="page" id="page-activitylog">
    <div style="padding:2rem;">
      <div class="page-title">📋 내 지도안 보관함</div>
      <div class="page-sub">생성한 지도안을 저장하고, 즐겨찾기로 관리하세요</div>
      <div style="display:flex;gap:10px;margin-bottom:1.5rem;flex-wrap:wrap;align-items:center;">
        <select id="logFilterFav" onchange="loadMyLessons()" style="height:38px;border:1px solid var(--g2);border-radius:var(--r);padding:0 12px;font-family:var(--font);font-size:13px;background:var(--white);color:var(--g9);outline:none;">
          <option value="all">전체 지도안</option>
          <option value="fav">⭐ 즐겨찾기만</option>
        </select>
        <button class="btn-primary" style="height:38px;margin-left:auto;" onclick="showPage('scanner', document.querySelector('.nav-item:nth-child(2)'))">+ 새 지도안 생성</button>
      </div>

      <!-- 로그인 안 된 상태 -->
      <div id="logNeedLogin" style="display:none; text-align:center; padding:3rem 1rem;">
        <div style="font-size:48px; margin-bottom:16px;">🔐</div>
        <div style="font-size:16px; font-weight:700; color:var(--g7); margin-bottom:8px;">로그인이 필요합니다</div>
        <div style="font-size:13px; color:var(--g5); margin-bottom:20px;">지도안을 저장하려면 먼저 로그인해주세요</div>
        <button class="btn-primary" onclick="showAuthModal()">로그인 / 회원가입</button>
      </div>

      <!-- 빈 상태 -->
      <div id="logEmpty" style="display:none; text-align:center; padding:3rem 1rem;">
        <div style="font-size:48px; margin-bottom:16px;">📂</div>
        <div style="font-size:16px; font-weight:700; color:var(--g7); margin-bottom:8px;">저장된 지도안이 없습니다</div>
        <div style="font-size:13px; color:var(--g5);">Play-Scanner에서 지도안을 생성하고 ⭐ 저장해보세요</div>
      </div>

      <!-- 지도안 목록 -->
      <ul class="log-list" id="logList"></ul>
    </div>
  </div>

  <!-- 지도안 상세 보기 모달 -->
  <div id="lessonDetailModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:9998; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeLessonDetail();">
    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; max-width:800px; max-height:85vh; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3); overflow-y:auto;">
      <div style="display:flex; align-items:center; justify-content:space-between; padding:20px 24px; border-bottom:1px solid var(--g2); position:sticky; top:0; background:var(--white); z-index:1;">
        <div id="lessonDetailTitle" style="font-size:18px; font-weight:700; color:var(--g9);"></div>
        <div style="display:flex; gap:8px;">
          <button onclick="copyLessonDetail()" style="padding:6px 12px; border:1px solid var(--g2); border-radius:var(--r); background:var(--white); font-family:var(--font); font-size:12px; cursor:pointer;">📋 복사</button>
          <button onclick="closeLessonDetail()" style="width:32px; height:32px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px; color:var(--g7);">×</button>
        </div>
      </div>
      <div id="lessonDetailContent" class="lesson-md" style="padding:24px;"></div>
    </div>
  </div>

  <!-- ════ COMMUNITY PAGE ════ -->'''

# 패턴 매칭으로 교체
start_idx = html.find(old_activitylog_start)
end_idx = html.find(old_activitylog_end)

if start_idx != -1 and end_idx != -1:
    html = html[:start_idx] + new_activitylog + html[end_idx + len(old_activitylog_end):]
    print("✅ PATCH 2: 활동 기록지 페이지 교체 완료")
else:
    print("⚠️  PATCH 2: 활동 기록지 페이지 패턴을 찾을 수 없습니다.")


# ============================================================
# PATCH 3: 사이드바 "활동 기록지" 이름 변경
# ============================================================
html = html.replace(
    '<span class="nav-icon">📋</span><span>활동 기록지</span>',
    '<span class="nav-icon">📋</span><span>내 지도안</span>'
)
print("✅ PATCH 3: 사이드바 메뉴 이름 변경 완료")


# ============================================================
# PATCH 4: JS 함수 추가 (</script> 바로 앞에 삽입)
# ============================================================

new_js = '''

// ============================================================
// 지도안 저장/즐겨찾기 기능
// ============================================================

// 저장 버튼 표시 (로그인 시에만)
function updateSaveButton() {
  const btn = document.getElementById('btnSaveLesson');
  if (btn) {
    const token = localStorage.getItem('auth_token');
    btn.style.display = token ? 'inline-block' : 'none';
  }
}

// 지도안 저장
async function saveLessonPlan() {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    showAuthModal();
    return;
  }

  const content = document.getElementById('outputContent');
  const md = content.dataset.markdown;
  const countryCode = content.dataset.country;
  if (!md) {
    showToast('저장할 지도안이 없습니다.', 'error');
    return;
  }

  const card = _state.cards && _state.cards[_state.selectedCardIdx];
  const title = card ? card.card_title : '지도안';

  const btn = document.getElementById('btnSaveLesson');
  const origText = btn.textContent;
  btn.textContent = '저장 중...';
  btn.disabled = true;

  try {
    const res = await fetch(API_BASE + '/api/lessons/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token,
      },
      body: JSON.stringify({
        title: title,
        search_query: _state.searchQuery,
        country_code: countryCode,
        age: _state.age,
        duration: _state.duration,
        card_data: card || null,
        lesson_markdown: md,
      }),
    });

    if (res.status === 401) {
      localStorage.removeItem('auth_token');
      showAuthModal();
      return;
    }

    const data = await res.json();
    if (res.ok) {
      btn.textContent = '✅ 저장됨!';
      btn.style.background = 'var(--teal-3)';
      btn.style.color = 'var(--teal-dark, #085041)';
      showToast('지도안이 저장되었습니다! 📋 내 지도안에서 확인하세요.', 'success');
      setTimeout(() => {
        btn.textContent = '⭐ 저장';
        btn.style.background = 'var(--amber-3)';
        btn.style.color = 'var(--amber-dark, #854F0B)';
        btn.disabled = false;
      }, 2000);
    } else {
      throw new Error(data.detail || '저장 실패');
    }
  } catch (e) {
    showToast('저장 실패: ' + e.message, 'error');
    btn.textContent = origText;
    btn.disabled = false;
  }
}

// 내 지도안 목록 로드
async function loadMyLessons() {
  const token = localStorage.getItem('auth_token');
  const loginMsg = document.getElementById('logNeedLogin');
  const emptyMsg = document.getElementById('logEmpty');
  const list = document.getElementById('logList');

  if (!token) {
    loginMsg.style.display = 'block';
    emptyMsg.style.display = 'none';
    list.innerHTML = '';
    return;
  }

  loginMsg.style.display = 'none';

  try {
    const res = await fetch(API_BASE + '/api/lessons/my', {
      headers: { 'Authorization': 'Bearer ' + token },
    });

    if (res.status === 401) {
      loginMsg.style.display = 'block';
      return;
    }

    const lessons = await res.json();
    const filter = document.getElementById('logFilterFav').value;
    const filtered = filter === 'fav' ? lessons.filter(l => l.is_favorite) : lessons;

    if (filtered.length === 0) {
      emptyMsg.style.display = 'block';
      list.innerHTML = '';
      return;
    }

    emptyMsg.style.display = 'none';
    list.innerHTML = filtered.map(l => {
      const flag = FLAGS[l.country_code] || '🌐';
      const date = new Date(l.created_at).toLocaleDateString('ko-KR');
      const favClass = l.is_favorite ? 'style="color:#EF9F27;"' : 'style="color:var(--g3);"';
      return `
        <li class="log-item">
          <div class="log-thumb">${flag}</div>
          <div class="log-content">
            <div class="log-title">${escapeHtml(l.title)}</div>
            <div class="log-meta">${escapeHtml(l.search_query)} · 만 ${l.age}세 · ${l.duration}분</div>
            <div class="log-badges">
              <span class="log-badge" style="background:var(--teal-3);color:var(--teal-dark, #085041)">${l.country_code}</span>
              ${l.is_favorite ? '<span class="log-badge" style="background:#FAEEDA;color:#854F0B">⭐ 즐겨찾기</span>' : ''}
            </div>
          </div>
          <div class="log-right">
            <div class="log-date">${date}</div>
            <div class="log-actions">
              <button class="log-action-btn" ${favClass} onclick="toggleFavorite(${l.id}, event)" title="즐겨찾기">
                ${l.is_favorite ? '⭐' : '☆'}
              </button>
              <button class="log-action-btn" style="background:var(--teal-3);color:var(--teal-dark, #085041);border:none;" onclick="viewLessonDetail(${l.id})">📖 보기</button>
              <button class="log-action-btn" style="background:var(--g1);color:var(--coral);border:1px solid var(--g2);" onclick="deleteLesson(${l.id}, event)">🗑</button>
            </div>
          </div>
        </li>
      `;
    }).join('');
  } catch (e) {
    console.error('지도안 목록 로드 실패:', e);
    list.innerHTML = '<li style="padding:2rem;text-align:center;color:var(--g5);">목록을 불러올 수 없습니다.</li>';
  }
}

// 즐겨찾기 토글
async function toggleFavorite(lessonId, event) {
  event.stopPropagation();
  const token = localStorage.getItem('auth_token');
  if (!token) return;

  try {
    const res = await fetch(API_BASE + `/api/lessons/${lessonId}/favorite`, {
      method: 'PATCH',
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (res.ok) {
      loadMyLessons();
    }
  } catch (e) {
    console.error('즐겨찾기 토글 실패:', e);
  }
}

// 지도안 상세 보기
async function viewLessonDetail(lessonId) {
  const token = localStorage.getItem('auth_token');
  if (!token) return;

  try {
    const res = await fetch(API_BASE + `/api/lessons/${lessonId}`, {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (!res.ok) throw new Error('조회 실패');
    const lesson = await res.json();

    const flag = FLAGS[lesson.country_code] || '🌐';
    document.getElementById('lessonDetailTitle').textContent = `${flag} ${lesson.title}`;

    let html;
    if (typeof marked !== 'undefined') {
      html = marked.parse(lesson.lesson_markdown);
    } else {
      html = '<pre style="white-space:pre-wrap;">' + escapeHtml(lesson.lesson_markdown) + '</pre>';
    }
    document.getElementById('lessonDetailContent').innerHTML = html;
    document.getElementById('lessonDetailContent').dataset.markdown = lesson.lesson_markdown;
    document.getElementById('lessonDetailModal').style.display = 'block';
  } catch (e) {
    showToast('지도안을 불러올 수 없습니다.', 'error');
  }
}

function closeLessonDetail() {
  document.getElementById('lessonDetailModal').style.display = 'none';
}

function copyLessonDetail() {
  const md = document.getElementById('lessonDetailContent').dataset.markdown;
  if (md) {
    navigator.clipboard.writeText(md).then(() => showToast('복사되었습니다!', 'success'));
  }
}

// 지도안 삭제
async function deleteLesson(lessonId, event) {
  event.stopPropagation();
  if (!confirm('이 지도안을 삭제하시겠습니까?')) return;

  const token = localStorage.getItem('auth_token');
  if (!token) return;

  try {
    const res = await fetch(API_BASE + `/api/lessons/${lessonId}`, {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (res.ok) {
      showToast('지도안이 삭제되었습니다.', 'info');
      loadMyLessons();
    }
  } catch (e) {
    showToast('삭제 실패', 'error');
  }
}

// 활동 기록지 페이지 진입 시 자동 로드
const _origShowPage = showPage;
showPage = function(id, navEl) {
  _origShowPage(id, navEl);
  if (id === 'activitylog') {
    loadMyLessons();
  }
  updateSaveButton();
};

// 지도안 생성 완료 후 저장 버튼 표시
const _origRenderLessonOutput = renderLessonOutput;
renderLessonOutput = function(card, markdown) {
  _origRenderLessonOutput(card, markdown);
  updateSaveButton();
};

'''

# </script> 바로 앞에 삽입
close_script_tag = '</script>\n</body>'
if close_script_tag in html:
    html = html.replace(close_script_tag, new_js + '\n</script>\n</body>')
    print("✅ PATCH 4: JS 함수 추가 완료")
else:
    # 좀 다른 형태일 수 있음
    alt_close = '</script>\n</body>\n</html>'
    if alt_close in html:
        html = html.replace(alt_close, new_js + '\n</script>\n</body>\n</html>')
        print("✅ PATCH 4: JS 함수 추가 완료 (alt)")
    else:
        print("⚠️  PATCH 4: </script> 패턴을 찾을 수 없습니다.")


# ============================================================
# 저장
# ============================================================
HTML_PATH.write_text(html, encoding="utf-8")
print(f"\n🎉 패치 완료! {HTML_PATH}")
print("서버가 --reload 모드라면 자동으로 반영됩니다.")
print("\n테스트 방법:")
print("  1. 브라우저에서 http://localhost:8000 접속")
print("  2. 로그인 후 지도안 생성")
print("  3. ⭐ 저장 버튼 클릭")
print("  4. 사이드바 '내 지도안' 클릭해서 확인")
