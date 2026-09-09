#!/usr/bin/env python3
"""
patch_new_ui.py
====================
새 디자인 edu-bridge-full.html에 인증 + 저장 기능을 추가하는 패치 스크립트

사용법:
    cd backend
    python3 patch_new_ui.py
"""
from pathlib import Path

HTML_PATH = Path("static/edu-bridge-full.html")
if not HTML_PATH.exists():
    print(f"❌ {HTML_PATH}을 찾을 수 없습니다.")
    exit(1)

html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_newui")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업 생성: {backup}")

# ============================================================
# PATCH 1: 사이드바에 "내 지도안" 메뉴 추가
# ============================================================
old_nav = '''    <div class="nav-section-label">소통</div>'''
new_nav = '''    <div class="nav-section-label">관리</div>
    <button class="nav-item" onclick="showPage('activitylog', this)">
      <span class="nav-icon">📋</span><span>내 지도안</span>
    </button>
    <div class="nav-section-label">소통</div>'''

if old_nav in html:
    html = html.replace(old_nav, new_nav, 1)
    print("✅ PATCH 1: 사이드바 '내 지도안' 메뉴 추가")
else:
    print("⚠️  PATCH 1: 패턴 못 찾음")

# ============================================================
# PATCH 2: 지도안 출력 영역에 ⭐ 저장 버튼 추가
# ============================================================
old_actions = '''<div class="output-actions">
            <button class="btn-copy" onclick="copyOutput()">📋 복사</button>
            <button class="btn-edit" onclick="downloadLessonPlan()">📥 다운로드</button>'''
new_actions = '''<div class="output-actions">
            <button class="btn-copy" onclick="copyOutput()">📋 복사</button>
            <button class="btn-edit" onclick="downloadLessonPlan()">📥 다운로드</button>
            <button class="btn-edit" id="btnSaveLesson" onclick="saveLessonPlan()" style="display:none; background:var(--amber); border:none;">⭐ 저장</button>'''

if old_actions in html:
    html = html.replace(old_actions, new_actions, 1)
    print("✅ PATCH 2: ⭐ 저장 버튼 추가")
else:
    print("⚠️  PATCH 2: 패턴 못 찾음")

# ============================================================
# PATCH 3: 로그인 모달 → 실제 인증 모달로 교체
# ============================================================
old_modal = '''<!-- LOGIN MODAL -->
<div class="modal-overlay" id="loginModal">
  <div class="modal-box">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="modal-title">EDU-bridge 로그인</div>
    <div class="modal-sub">교사 전용 글로벌 교육안 플랫폼</div>
    <div class="login-fields">
      <input type="text" placeholder="아이디">
      <input type="password" placeholder="비밀번호">
    </div>
    <button class="btn-modal-primary" onclick="doLogin()">로그인</button>
    <div style="text-align:center;margin-top:12px;font-size:13px;color:var(--g5);">계정이 없으신가요? <span style="color:var(--teal);font-weight:700;cursor:pointer;">회원가입</span></div>
  </div>
</div>'''

new_modal = '''<!-- AUTH MODAL -->
<div class="modal-overlay" id="loginModal">
  <div class="modal-box" style="max-width:420px;">
    <button class="modal-close" onclick="closeModal()">✕</button>

    <!-- 탭 -->
    <div style="display:flex; border-bottom:1px solid var(--g2); margin:-24px -28px 20px; padding:0 28px;">
      <button id="tab-login" onclick="switchAuthTab('login')" style="flex:1; padding:14px; border:none; background:none; font-family:var(--font); font-size:14px; font-weight:600; color:var(--teal); border-bottom:2px solid var(--teal); cursor:pointer;">로그인</button>
      <button id="tab-signup" onclick="switchAuthTab('signup')" style="flex:1; padding:14px; border:none; background:none; font-family:var(--font); font-size:14px; font-weight:600; color:var(--g5); border-bottom:2px solid transparent; cursor:pointer;">회원가입</button>
    </div>

    <!-- 로그인 폼 -->
    <div id="form-login">
      <div class="modal-title">EDU-bridge 로그인</div>
      <div class="modal-sub">교사 전용 글로벌 교육안 플랫폼</div>
      <div class="login-fields">
        <input type="email" id="login-email" placeholder="이메일" autocomplete="email">
        <input type="password" id="login-password" placeholder="비밀번호" autocomplete="current-password">
      </div>
      <div id="login-error" style="display:none; padding:10px 12px; background:var(--coral-3); border-radius:var(--r); color:var(--coral); font-size:13px; margin-bottom:12px;"></div>
      <button class="btn-modal-primary" onclick="handleLogin()">로그인</button>
      <div style="text-align:center;margin-top:12px;font-size:13px;color:var(--g5);">계정이 없으신가요? <span style="color:var(--teal);font-weight:700;cursor:pointer;" onclick="switchAuthTab('signup')">회원가입</span></div>
    </div>

    <!-- 회원가입 폼 -->
    <div id="form-signup" style="display:none;">
      <div class="modal-title">새 계정 만들기</div>
      <div class="modal-sub">글로벌 교육안 설계를 시작하세요</div>
      <div class="login-fields">
        <input type="email" id="signup-email" placeholder="이메일" autocomplete="email">
        <input type="text" id="signup-username" placeholder="사용자명" autocomplete="username">
        <input type="text" id="signup-fullname" placeholder="이름 (선택)" autocomplete="name">
        <input type="password" id="signup-password" placeholder="비밀번호 (6자 이상)" autocomplete="new-password">
        <input type="password" id="signup-password-confirm" placeholder="비밀번호 확인" autocomplete="new-password">
      </div>
      <div id="signup-error" style="display:none; padding:10px 12px; background:var(--coral-3); border-radius:var(--r); color:var(--coral); font-size:13px; margin-bottom:12px;"></div>
      <button class="btn-modal-primary" onclick="handleSignup()">회원가입</button>
      <div style="text-align:center;margin-top:12px;font-size:13px;color:var(--g5);">이미 계정이 있으신가요? <span style="color:var(--teal);font-weight:700;cursor:pointer;" onclick="switchAuthTab('login')">로그인</span></div>
    </div>
  </div>
</div>'''

if old_modal in html:
    html = html.replace(old_modal, new_modal)
    print("✅ PATCH 3: 인증 모달 교체")
else:
    print("⚠️  PATCH 3: 로그인 모달 패턴 못 찾음")

# ============================================================
# PATCH 4: 활동 기록지 → 내 지도안 DB 연동
# ============================================================
old_log_start = '  <!-- ════ ACTIVITY LOG PAGE ════ -->'
old_log_end = '  <!-- ════ COMMUNITY PAGE ════ -->'

new_log = '''  <!-- ════ MY LESSONS PAGE ════ -->
  <div class="page" id="page-activitylog">
    <div style="padding:2rem;">
      <div class="page-title">📋 내 지도안 보관함</div>
      <div class="page-sub">생성한 지도안을 저장하고 즐겨찾기로 관리하세요</div>
      <div style="display:flex;gap:10px;margin-bottom:1.5rem;flex-wrap:wrap;align-items:center;">
        <select id="logFilterFav" onchange="loadMyLessons()" style="height:38px;border:1px solid var(--g2);border-radius:var(--r);padding:0 12px;font-family:var(--font);font-size:13px;background:var(--white);color:var(--g9);outline:none;">
          <option value="all">전체 지도안</option>
          <option value="fav">⭐ 즐겨찾기만</option>
        </select>
        <button class="btn-primary" style="height:38px;margin-left:auto;" onclick="showPage('scanner', document.querySelector('.nav-item:nth-child(3)'))">+ 새 지도안 생성</button>
      </div>
      <div id="logNeedLogin" style="display:none; text-align:center; padding:3rem 1rem;">
        <div style="font-size:48px; margin-bottom:16px;">🔐</div>
        <div style="font-size:16px; font-weight:700; color:var(--g7); margin-bottom:8px;">로그인이 필요합니다</div>
        <div style="font-size:13px; color:var(--g5); margin-bottom:20px;">지도안을 저장하려면 먼저 로그인해주세요</div>
        <button class="btn-primary" onclick="showModal()">로그인 / 회원가입</button>
      </div>
      <div id="logEmpty" style="display:none; text-align:center; padding:3rem 1rem;">
        <div style="font-size:48px; margin-bottom:16px;">📂</div>
        <div style="font-size:16px; font-weight:700; color:var(--g7); margin-bottom:8px;">저장된 지도안이 없습니다</div>
        <div style="font-size:13px; color:var(--g5);">Play-Scanner에서 지도안을 생성하고 ⭐ 저장해보세요</div>
      </div>
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

start_i = html.find(old_log_start)
end_i = html.find(old_log_end)
if start_i != -1 and end_i != -1:
    html = html[:start_i] + new_log + html[end_i + len(old_log_end):]
    print("✅ PATCH 4: 내 지도안 페이지 교체")
else:
    print("⚠️  PATCH 4: 패턴 못 찾음")

# ============================================================
# PATCH 5: 기존 mock JS 교체 + 인증/저장 JS 추가
# ============================================================
old_js = '''// ─ MODAL ─
function showModal() { document.getElementById('loginModal').classList.add('show'); }
function closeModal() { document.getElementById('loginModal').classList.remove('show'); }
function doLogin() {
  // 로그인 처리 (하드코딩 데모)
  document.getElementById('greeting-block').style.display = 'block';
  document.getElementById('sidebar-profile').style.display = 'flex';
  document.getElementById('notif-btn').style.display = 'flex';
  document.getElementById('login-btn-area').innerHTML = '<span style="font-size:13px;color:var(--g7);font-weight:600;">김선생님 환영합니다 👋</span>';
  // 사이드바 하단 로그인 버튼도 숨김
  var sidebarLogin = document.getElementById('sidebar-login-btn');
  if (sidebarLogin) sidebarLogin.style.display = 'none';
  closeModal();
}
document.getElementById('loginModal').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});'''

new_js = r'''// ─ MODAL ─
function showModal() { document.getElementById('loginModal').classList.add('show'); switchAuthTab('login'); }
function closeModal() {
  document.getElementById('loginModal').classList.remove('show');
  document.getElementById('login-error').style.display = 'none';
  document.getElementById('signup-error').style.display = 'none';
}
document.getElementById('loginModal').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

// ─ AUTH TAB ─
function switchAuthTab(tab) {
  const tl = document.getElementById('tab-login'), ts = document.getElementById('tab-signup');
  const fl = document.getElementById('form-login'), fs = document.getElementById('form-signup');
  if (tab === 'login') {
    tl.style.color = 'var(--teal)'; tl.style.borderBottomColor = 'var(--teal)';
    ts.style.color = 'var(--g5)'; ts.style.borderBottomColor = 'transparent';
    fl.style.display = 'block'; fs.style.display = 'none';
  } else {
    ts.style.color = 'var(--teal)'; ts.style.borderBottomColor = 'var(--teal)';
    tl.style.color = 'var(--g5)'; tl.style.borderBottomColor = 'transparent';
    fs.style.display = 'block'; fl.style.display = 'none';
  }
}

// ─ AUTH STATE ─
let currentUser = null;

window.addEventListener('DOMContentLoaded', () => { checkAuthStatus(); });

async function checkAuthStatus() {
  const token = localStorage.getItem('auth_token');
  if (!token) { updateUIForGuest(); return; }
  try {
    const r = await fetch('/api/me', { headers: { 'Authorization': 'Bearer ' + token } });
    if (r.ok) { currentUser = await r.json(); updateUIForUser(currentUser); }
    else { localStorage.removeItem('auth_token'); updateUIForGuest(); }
  } catch(e) { updateUIForGuest(); }
}

function updateUIForUser(user) {
  const name = user.full_name || user.username;
  const initial = name ? name[0] : '?';
  // sidebar
  var sb = document.getElementById('sidebar-login-btn'); if (sb) sb.style.display = 'none';
  var sp = document.getElementById('sidebar-profile'); if (sp) { sp.style.display = 'flex'; sp.innerHTML = '<div class="avatar-circle">' + initial + '</div><div><div class="user-name">' + name + '</div><div class="user-role">유치원 교사</div></div>'; }
  // topbar
  var lb = document.getElementById('login-btn-area'); if (lb) lb.innerHTML = '<span style="font-size:13px;color:var(--g7);font-weight:600;cursor:pointer;" onclick="handleLogout()">' + name + '님 (로그아웃)</span>';
  // greeting
  var gb = document.getElementById('greeting-block'); if (gb) gb.style.display = 'block';
  var nb = document.getElementById('notif-btn'); if (nb) nb.style.display = 'flex';
  var pt = document.querySelector('#page-dashboard .page-title'); if (pt) pt.textContent = '안녕하세요, ' + name + '님 👋';
  updateSaveButton();
}

function updateUIForGuest() {
  currentUser = null;
  var sb = document.getElementById('sidebar-login-btn'); if (sb) sb.style.display = 'block';
  var sp = document.getElementById('sidebar-profile'); if (sp) sp.style.display = 'none';
  var lb = document.getElementById('login-btn-area'); if (lb) lb.innerHTML = '<button class="btn-primary" style="height:34px;padding:0 14px;font-size:13px;" onclick="showModal()">로그인</button>';
  updateSaveButton();
}

async function handleLogin() {
  const email = document.getElementById('login-email').value.trim();
  const pw = document.getElementById('login-password').value;
  const err = document.getElementById('login-error');
  if (!email || !pw) { err.textContent = '이메일과 비밀번호를 입력해주세요.'; err.style.display = 'block'; return; }
  try {
    const r = await fetch('/api/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email, password:pw}) });
    const d = await r.json();
    if (r.ok) { localStorage.setItem('auth_token', d.access_token); currentUser = d.user; updateUIForUser(d.user); closeModal(); showToast('로그인되었습니다!','success'); }
    else { err.textContent = d.detail || '로그인 실패'; err.style.display = 'block'; }
  } catch(e) { err.textContent = '서버 오류'; err.style.display = 'block'; }
}

async function handleSignup() {
  const email = document.getElementById('signup-email').value.trim();
  const username = document.getElementById('signup-username').value.trim();
  const fullname = document.getElementById('signup-fullname').value.trim();
  const pw = document.getElementById('signup-password').value;
  const pw2 = document.getElementById('signup-password-confirm').value;
  const err = document.getElementById('signup-error');
  if (!email||!username||!pw) { err.textContent='이메일, 사용자명, 비밀번호는 필수입니다.'; err.style.display='block'; return; }
  if (pw.length<6) { err.textContent='비밀번호는 6자 이상이어야 합니다.'; err.style.display='block'; return; }
  if (pw!==pw2) { err.textContent='비밀번호가 일치하지 않습니다.'; err.style.display='block'; return; }
  try {
    const r = await fetch('/api/signup', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email, username, password:pw, full_name:fullname||null}) });
    const d = await r.json();
    if (r.ok) { localStorage.setItem('auth_token', d.access_token); currentUser = d.user; updateUIForUser(d.user); closeModal(); showToast('환영합니다! 회원가입 완료!','success'); }
    else { err.textContent = d.detail || '회원가입 실패'; err.style.display = 'block'; }
  } catch(e) { err.textContent = '서버 오류'; err.style.display = 'block'; }
}

function handleLogout() {
  if (confirm('로그아웃하시겠습니까?')) { localStorage.removeItem('auth_token'); currentUser = null; updateUIForGuest(); showToast('로그아웃되었습니다.','info'); }
}

document.addEventListener('keypress', function(e) {
  if (e.key === 'Enter' && document.getElementById('login-password') === document.activeElement) handleLogin();
  if (e.key === 'Enter' && document.getElementById('signup-password-confirm') === document.activeElement) handleSignup();
});

// ─ TOAST ─
function showToast(msg, type) {
  const t = document.createElement('div');
  const bg = type==='success' ? 'var(--teal)' : type==='error' ? 'var(--coral)' : 'var(--g7)';
  t.style.cssText = 'position:fixed;top:80px;right:20px;background:'+bg+';color:var(--white);padding:14px 20px;border-radius:var(--r);box-shadow:0 4px 16px rgba(0,0,0,0.2);z-index:10000;font-size:14px;font-weight:600;transition:opacity 0.3s;';
  t.textContent = msg; document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3000);
}

// ─ SAVE LESSON ─
function updateSaveButton() {
  const btn = document.getElementById('btnSaveLesson');
  if (btn) btn.style.display = localStorage.getItem('auth_token') ? 'inline-block' : 'none';
}

async function saveLessonPlan() {
  const token = localStorage.getItem('auth_token');
  if (!token) { showModal(); return; }
  const content = document.getElementById('outputContent');
  const md = content.dataset.markdown, cc = content.dataset.country;
  if (!md) { showToast('저장할 지도안이 없습니다.','error'); return; }
  const card = _state.cards && _state.cards[_state.selectedCardIdx];
  const title = card ? card.card_title : '지도안';
  const btn = document.getElementById('btnSaveLesson');
  btn.textContent = '저장 중...'; btn.disabled = true;
  try {
    const r = await fetch(API_BASE+'/api/lessons/save', { method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+token}, body:JSON.stringify({title, search_query:_state.searchQuery, country_code:cc, age:_state.age, duration:_state.duration, card_data:card||null, lesson_markdown:md}) });
    if (r.status===401) { localStorage.removeItem('auth_token'); showModal(); return; }
    const d = await r.json();
    if (r.ok) { btn.textContent='✅ 저장됨!'; showToast('지도안이 저장되었습니다!','success'); setTimeout(()=>{btn.textContent='⭐ 저장';btn.disabled=false;},2000); }
    else throw new Error(d.detail);
  } catch(e) { showToast('저장 실패: '+e.message,'error'); btn.textContent='⭐ 저장'; btn.disabled=false; }
}

// ─ MY LESSONS ─
async function loadMyLessons() {
  const token = localStorage.getItem('auth_token');
  const needLogin = document.getElementById('logNeedLogin');
  const empty = document.getElementById('logEmpty');
  const list = document.getElementById('logList');
  if (!needLogin) return;
  if (!token) { needLogin.style.display='block'; empty.style.display='none'; list.innerHTML=''; return; }
  needLogin.style.display='none';
  try {
    const r = await fetch(API_BASE+'/api/lessons/my', { headers:{'Authorization':'Bearer '+token} });
    if (r.status===401) { needLogin.style.display='block'; return; }
    const lessons = await r.json();
    const filter = document.getElementById('logFilterFav').value;
    const filtered = filter==='fav' ? lessons.filter(l=>l.is_favorite) : lessons;
    if (!filtered.length) { empty.style.display='block'; list.innerHTML=''; return; }
    empty.style.display='none';
    list.innerHTML = filtered.map(l => {
      const flag = FLAGS[l.country_code]||'🌐', date = new Date(l.created_at).toLocaleDateString('ko-KR');
      return '<li class="log-item"><div class="log-thumb">'+flag+'</div><div class="log-content"><div class="log-title">'+escapeHtml(l.title)+'</div><div class="log-meta">'+escapeHtml(l.search_query)+' · 만 '+l.age+'세 · '+l.duration+'분</div><div class="log-badges"><span class="log-badge" style="background:var(--teal-3);color:var(--teal-dark)">'+l.country_code+'</span>'+(l.is_favorite?'<span class="log-badge" style="background:#FAEEDA;color:#854F0B">⭐ 즐겨찾기</span>':'')+'</div></div><div class="log-right"><div class="log-date">'+date+'</div><div class="log-actions"><button class="log-action-btn" style="color:'+(l.is_favorite?'#EF9F27':'var(--g3)')+'" onclick="toggleFavorite('+l.id+',event)">'+(l.is_favorite?'⭐':'☆')+'</button><button class="log-action-btn" style="background:var(--teal-3);color:var(--teal-dark);border:none;" onclick="viewLessonDetail('+l.id+')">📖 보기</button><button class="log-action-btn" style="background:var(--g1);color:var(--coral);border:1px solid var(--g2);" onclick="deleteLesson('+l.id+',event)">🗑</button></div></div></li>';
    }).join('');
  } catch(e) { list.innerHTML='<li style="padding:2rem;text-align:center;color:var(--g5);">불러오기 실패</li>'; }
}

async function toggleFavorite(id, e) {
  e.stopPropagation();
  const token = localStorage.getItem('auth_token'); if(!token) return;
  try { await fetch(API_BASE+'/api/lessons/'+id+'/favorite', {method:'PATCH',headers:{'Authorization':'Bearer '+token}}); loadMyLessons(); } catch(e) {}
}

async function viewLessonDetail(id) {
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
}
function closeLessonDetail() { document.getElementById('lessonDetailModal').style.display='none'; }
function copyLessonDetail() { const md = document.getElementById('lessonDetailContent').dataset.markdown; if(md) navigator.clipboard.writeText(md).then(()=>showToast('복사됨!','success')); }

async function deleteLesson(id, e) {
  e.stopPropagation(); if(!confirm('삭제하시겠습니까?')) return;
  const token = localStorage.getItem('auth_token'); if(!token) return;
  try { const r = await fetch(API_BASE+'/api/lessons/'+id, {method:'DELETE',headers:{'Authorization':'Bearer '+token}}); if(r.ok){showToast('삭제됨','info');loadMyLessons();} } catch(e) {}
}

// ─ PAGE HOOK ─
const _origShowPage = showPage;
showPage = function(id, navEl, section) {
  _origShowPage(id, navEl, section);
  if (id === 'activitylog') loadMyLessons();
  updateSaveButton();
};
const _origRenderLesson = typeof renderLessonOutput !== 'undefined' ? renderLessonOutput : null;
if (_origRenderLesson) {
  renderLessonOutput = function(card, md) { _origRenderLesson(card, md); updateSaveButton(); };
}'''

if old_js in html:
    html = html.replace(old_js, new_js)
    print("✅ PATCH 5: 인증/저장 JS 추가")
else:
    print("⚠️  PATCH 5: mock JS 패턴 못 찾음")

# ============================================================
# 저장
# ============================================================
HTML_PATH.write_text(html, encoding="utf-8")
print(f"\n🎉 패치 완료! {HTML_PATH}")
print("서버 재시작 후 테스트:")
print("  1. 회원가입 → 로그인")
print("  2. Play-Scanner → 지도안 생성 → ⭐ 저장")
print("  3. 📋 내 지도안 → 목록 확인")
