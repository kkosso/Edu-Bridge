#!/usr/bin/env python3
"""
patch_landing_and_fixes.py
===========================
1. 마이페이지 클릭 핸들러 강제 바인딩 (좌하단 프로필 클릭 → 마이페이지)
2. 랜딩 페이지 추가 (첫 방문 시 자동 표시, '사용해보기' 버튼으로 진입)
3. 좌상단 로고 클릭 → 홈 대시보드로 이동
"""
from pathlib import Path
import re

HTML_PATH = Path("static/edu-bridge-full.html")
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_landing")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업: {backup}")


# ============================================================
# 1) 랜딩 페이지 CSS + HTML 추가
# ============================================================
landing_styles = '''
<style id="landing-styles">
/* 랜딩 페이지 전용 스타일 */
#landingOverlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: var(--white);
  z-index: 99999;
  overflow-y: auto;
  font-family: var(--font);
  display: none;
}

#landingOverlay.show { display: block; }

.landing-nav {
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--g1);
  padding: 16px 5%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 100;
}
.landing-nav-logo {
  font-family: var(--font);
  font-size: 22px;
  font-weight: 900;
  color: var(--g9);
}
.landing-nav-logo span { color: var(--teal); }
.landing-nav-cta {
  padding: 10px 22px;
  border: none;
  border-radius: 999px;
  background: var(--teal);
  color: var(--white);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.landing-nav-cta:hover {
  background: var(--teal-dark, #085041);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(29, 158, 117, 0.3);
}

/* 히어로 섹션 */
.landing-hero {
  padding: 80px 5% 100px;
  text-align: center;
  background: linear-gradient(180deg, #f0fdf9 0%, #ffffff 100%);
  position: relative;
  overflow: hidden;
}
.landing-hero-badge {
  display: inline-block;
  padding: 6px 14px;
  background: var(--teal-3);
  color: var(--teal-dark, #085041);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 24px;
  animation: fadeInUp 0.6s ease-out;
}
.landing-hero h1 {
  font-size: clamp(32px, 5vw, 56px);
  font-weight: 900;
  color: var(--g9);
  line-height: 1.25;
  margin: 0 0 20px;
  animation: fadeInUp 0.7s ease-out;
}
.landing-hero h1 .highlight {
  background: linear-gradient(120deg, var(--teal) 0%, var(--teal-dark, #085041) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.landing-hero p {
  font-size: 17px;
  color: var(--g6);
  margin: 0 auto 36px;
  max-width: 600px;
  line-height: 1.7;
  animation: fadeInUp 0.8s ease-out;
}
.landing-hero-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 16px 36px;
  background: var(--teal);
  color: var(--white);
  border: none;
  border-radius: 999px;
  font-family: var(--font);
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s;
  box-shadow: 0 8px 30px rgba(29, 158, 117, 0.25);
  animation: fadeInUp 0.9s ease-out;
}
.landing-hero-cta:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 12px 40px rgba(29, 158, 117, 0.4);
}
.landing-hero-sub {
  margin-top: 16px;
  font-size: 12px;
  color: var(--g5);
  animation: fadeInUp 1s ease-out;
}

/* 섹션 공통 */
.landing-section {
  padding: 100px 5%;
  max-width: 1200px;
  margin: 0 auto;
}
.landing-section-title {
  text-align: center;
  margin-bottom: 60px;
}
.landing-section-eyebrow {
  font-size: 13px;
  font-weight: 700;
  color: var(--teal);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 12px;
}
.landing-section-h2 {
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 900;
  color: var(--g9);
  line-height: 1.3;
  margin: 0;
}
.landing-section-p {
  font-size: 16px;
  color: var(--g6);
  line-height: 1.7;
  max-width: 600px;
  margin: 16px auto 0;
}

/* 기능 카드 */
.landing-features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px;
}
.landing-feature-card {
  background: var(--white);
  border: 1.5px solid var(--g1);
  border-radius: 20px;
  padding: 36px 28px;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: default;
  position: relative;
  overflow: hidden;
}
.landing-feature-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--teal-3) 0%, transparent 60%);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}
.landing-feature-card:hover {
  transform: translateY(-8px) scale(1.02);
  border-color: var(--teal);
  box-shadow: 0 16px 50px rgba(29, 158, 117, 0.15);
}
.landing-feature-card:hover::before { opacity: 0.4; }
.landing-feature-icon {
  font-size: 44px;
  margin-bottom: 20px;
  display: inline-block;
  transition: transform 0.3s;
}
.landing-feature-card:hover .landing-feature-icon { transform: scale(1.15) rotate(-5deg); }
.landing-feature-title {
  font-size: 19px;
  font-weight: 900;
  color: var(--g9);
  margin: 0 0 12px;
}
.landing-feature-desc {
  font-size: 14px;
  color: var(--g6);
  line-height: 1.7;
  margin: 0;
}

/* 흐름 단계 */
.landing-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 30px;
  position: relative;
}
.landing-step {
  text-align: center;
  padding: 30px 20px;
}
.landing-step-num {
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, var(--teal), var(--teal-dark, #085041));
  color: var(--white);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 900;
  box-shadow: 0 8px 24px rgba(29, 158, 117, 0.25);
  transition: transform 0.3s;
}
.landing-step:hover .landing-step-num {
  transform: scale(1.1) rotate(10deg);
}
.landing-step-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--g9);
  margin: 0 0 8px;
}
.landing-step-desc {
  font-size: 13px;
  color: var(--g6);
  line-height: 1.7;
  margin: 0;
}

/* 신뢰 / 통계 */
.landing-stats {
  background: linear-gradient(135deg, #f0fdf9 0%, #ecfeff 100%);
  border-radius: 24px;
  padding: 60px 40px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 30px;
  text-align: center;
}
.landing-stat-num {
  font-size: 44px;
  font-weight: 900;
  color: var(--teal);
  line-height: 1;
}
.landing-stat-label {
  font-size: 13px;
  color: var(--g7);
  margin-top: 8px;
}

/* 최종 CTA */
.landing-final-cta {
  text-align: center;
  padding: 100px 5%;
  background: linear-gradient(135deg, var(--g9) 0%, #2a2a2a 100%);
  color: var(--white);
}
.landing-final-cta h2 {
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 900;
  margin: 0 0 16px;
  line-height: 1.3;
}
.landing-final-cta p {
  font-size: 16px;
  color: #9ca3af;
  margin: 0 auto 36px;
  max-width: 500px;
  line-height: 1.7;
}
.landing-final-cta button {
  padding: 16px 40px;
  background: var(--teal);
  color: var(--white);
  border: none;
  border-radius: 999px;
  font-family: var(--font);
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s;
}
.landing-final-cta button:hover {
  transform: translateY(-3px) scale(1.03);
  background: #2ab883;
}

/* 푸터 */
.landing-footer {
  background: #1a1a1a;
  color: #9ca3af;
  padding: 40px 5% 30px;
  text-align: center;
  font-size: 12px;
  line-height: 1.7;
}
.landing-footer a { color: var(--teal); text-decoration: none; }

/* 애니메이션 */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.reveal {
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.7s ease-out;
}
.reveal.revealed {
  opacity: 1;
  transform: translateY(0);
}
</style>
'''

landing_html = '''
<!-- ════ 랜딩 페이지 ════ -->
<div id="landingOverlay">
  <!-- 상단 네비 -->
  <nav class="landing-nav">
    <div class="landing-nav-logo" onclick="enterMainApp()" style="cursor:pointer;">EDU<span>-bridge</span></div>
    <button class="landing-nav-cta" onclick="enterMainApp()">사용해보기 →</button>
  </nav>

  <!-- 히어로 -->
  <section class="landing-hero">
    <div class="landing-hero-badge">🎁 2주 무료 체험 · 신용카드 불필요</div>
    <h1>
      더 좋은 수업에 집중하세요.<br>
      <span class="highlight">지도안은 AI가 도와드립니다.</span>
    </h1>
    <p>
      10개국 유아교육과정 데이터 기반 AI 추천 지도안.<br>
      검색 한 번이면, 우리 학교 양식에 맞춰 자동 완성됩니다.
    </p>
    <button class="landing-hero-cta" onclick="enterMainApp()">
      <span>지금 사용해보기</span>
      <span style="font-size:20px;">→</span>
    </button>
    <div class="landing-hero-sub">베타 테스트 중 · 2026년 6월 말 ~ 7월 초 정식 출시 예정</div>
  </section>

  <!-- 핵심 기능 -->
  <section class="landing-section">
    <div class="landing-section-title reveal">
      <div class="landing-section-eyebrow">Core Features</div>
      <h2 class="landing-section-h2">선생님이 진짜 필요한 4가지 기능</h2>
      <p class="landing-section-p">행정 업무가 줄어들수록, 아이들을 위한 시간이 늘어납니다.</p>
    </div>

    <div class="landing-features-grid">
      <div class="landing-feature-card reveal">
        <div class="landing-feature-icon">🎯</div>
        <h3 class="landing-feature-title">Play-Scanner</h3>
        <p class="landing-feature-desc">"숫자를 활용한 협동 놀이"처럼 자유롭게 검색하면, 10개국 교육과정을 분석한 AI가 즉시 지도안 카드를 제안합니다.</p>
      </div>
      <div class="landing-feature-card reveal">
        <div class="landing-feature-icon">📋</div>
        <h3 class="landing-feature-title">내 양식 자동 채우기</h3>
        <p class="landing-feature-desc">우리 유치원 양식(.docx)을 업로드만 하면, AI가 각 칸의 의미를 분석해 적절한 내용을 자동으로 채워드립니다.</p>
      </div>
      <div class="landing-feature-card reveal">
        <div class="landing-feature-icon">💌</div>
        <h3 class="landing-feature-title">AI 알림장</h3>
        <p class="landing-feature-desc">사진 한 장과 짧은 메모만으로 학부모에게 보낼 따뜻한 알림장이 완성됩니다. 톤도 자유롭게 선택하세요.</p>
      </div>
      <div class="landing-feature-card reveal">
        <div class="landing-feature-icon">💬</div>
        <h3 class="landing-feature-title">교사 커뮤니티</h3>
        <p class="landing-feature-desc">현장의 노하우, 활동 자료, 자유로운 질문까지. 전국 선생님들과 함께 성장하세요.</p>
      </div>
    </div>
  </section>

  <!-- 이용 흐름 -->
  <section class="landing-section" style="background:#fafafa; max-width:none; margin:0; border-radius:0;">
    <div style="max-width:1200px; margin:0 auto;">
      <div class="landing-section-title reveal">
        <div class="landing-section-eyebrow">How It Works</div>
        <h2 class="landing-section-h2">3단계로 시작하세요</h2>
      </div>

      <div class="landing-steps">
        <div class="landing-step reveal">
          <div class="landing-step-num">1</div>
          <h3 class="landing-step-title">회원가입 + 2주 체험</h3>
          <p class="landing-step-desc">신용카드 없이 가입 즉시 모든 Pro 기능을 무료로 사용하세요.</p>
        </div>
        <div class="landing-step reveal">
          <div class="landing-step-num">2</div>
          <h3 class="landing-step-title">수업 주제 검색</h3>
          <p class="landing-step-desc">Play-Scanner에서 자유롭게 검색하고 AI가 추천한 지도안 카드를 선택하세요.</p>
        </div>
        <div class="landing-step reveal">
          <div class="landing-step-num">3</div>
          <h3 class="landing-step-title">내 양식으로 받기</h3>
          <p class="landing-step-desc">우리 유치원 양식에 맞춰 자동 채워진 .docx 파일을 다운로드하세요.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- 신뢰 통계 -->
  <section class="landing-section">
    <div class="landing-stats reveal">
      <div>
        <div class="landing-stat-num">10</div>
        <div class="landing-stat-label">개국 유아교육과정 데이터</div>
      </div>
      <div>
        <div class="landing-stat-num">∞</div>
        <div class="landing-stat-label">맞춤형 지도안 생성</div>
      </div>
      <div>
        <div class="landing-stat-num">2주</div>
        <div class="landing-stat-label">무료 체험 기간</div>
      </div>
      <div>
        <div class="landing-stat-num">100%</div>
        <div class="landing-stat-label">교사 친화적 UX</div>
      </div>
    </div>
  </section>

  <!-- 최종 CTA -->
  <section class="landing-final-cta">
    <h2>오늘부터, 지도안 작성이 즐거워집니다.</h2>
    <p>지금 가입하면 모든 Pro 기능을 <b style="color:var(--teal);">2주 동안 무료</b>로 사용할 수 있습니다.</p>
    <button onclick="enterMainApp()">지금 사용해보기 →</button>
  </section>

  <!-- 푸터 -->
  <footer class="landing-footer">
    <div style="font-size:14px; color:var(--white); margin-bottom:10px; font-weight:700;">EDU-bridge</div>
    <div>글로벌 유아교육안 설계 플랫폼 · 베타 테스트 중</div>
    <div>© 2026 Team 초코소라빵 · <a href="mailto:minseosong5@gmail.com">minseosong5@gmail.com</a></div>
  </footer>
</div>
'''

# 랜딩 스타일 + HTML 추가
if 'id="landingOverlay"' not in html:
    # </head> 직전에 스타일 삽입
    html = html.replace('</head>', landing_styles + '\n</head>', 1)
    # <body> 다음에 랜딩 HTML 삽입
    html = re.sub(r'(<body[^>]*>)', r'\1\n' + landing_html, html, count=1)
    print("✅ 랜딩 페이지 추가")


# ============================================================
# 2) JS: 랜딩 표시/숨김 + 마이페이지 클릭 fix + 로고 클릭
# ============================================================
landing_js = '''

// ============================================================
// 랜딩 페이지 + 마이페이지 클릭 + 로고 홈이동
// ============================================================

function showLanding() {
  const overlay = document.getElementById('landingOverlay');
  if (overlay) {
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
    // 스크롤을 맨 위로
    overlay.scrollTop = 0;
    // reveal 애니메이션 다시 트리거
    setTimeout(initLandingReveal, 100);
  }
}

function enterMainApp() {
  const overlay = document.getElementById('landingOverlay');
  if (overlay) {
    overlay.classList.remove('show');
    document.body.style.overflow = '';
    localStorage.setItem('edubridge_visited', '1');
  }
  // 홈 페이지로 이동
  goHome();
}

function goHome() {
  // 사이드바의 첫 번째 메뉴 (대시보드/홈) 찾아서 클릭
  const homeBtn = document.querySelector('.nav-item[onclick*="dashboard"], .nav-item[onclick*="home"]');
  if (homeBtn) {
    homeBtn.click();
  } else {
    // 못 찾으면 첫 번째 nav-item 클릭
    const firstNav = document.querySelector('.nav-item');
    if (firstNav) firstNav.click();
  }
  window.scrollTo(0, 0);
}

// Intersection Observer로 스크롤 시 reveal 애니메이션
function initLandingReveal() {
  const reveals = document.querySelectorAll('#landingOverlay .reveal');
  reveals.forEach(el => el.classList.remove('revealed'));
  
  if (!('IntersectionObserver' in window)) {
    // 폴리필 없으면 그냥 다 표시
    reveals.forEach(el => el.classList.add('revealed'));
    return;
  }
  
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
  
  reveals.forEach(el => observer.observe(el));
}

// 첫 방문 시 자동 표시
window.addEventListener('DOMContentLoaded', function() {
  const visited = localStorage.getItem('edubridge_visited');
  if (!visited) {
    showLanding();
  }
});

// ============================================================
// 마이페이지 클릭 강제 바인딩
// ============================================================
function bindMyPageHandlers() {
  // 가능한 모든 사용자 표시 영역에 클릭 핸들러 추가
  const selectors = [
    '.sidebar-user',
    '.user-profile',
    '.sidebar-bottom',
    '[class*="user-info"]',
    '[class*="profile"]',
  ];
  
  selectors.forEach(sel => {
    document.querySelectorAll(sel).forEach(el => {
      if (!el.dataset.mypageBound) {
        el.style.cursor = 'pointer';
        el.addEventListener('click', function(e) {
          // 안에 있는 로그아웃 버튼이나 다른 버튼 클릭은 무시
          if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
          if (typeof openMyPage === 'function') {
            e.stopPropagation();
            openMyPage();
          }
        });
        el.dataset.mypageBound = '1';
      }
    });
  });
  
  // "송민서" 같은 사용자 이름이 표시된 영역도 찾기
  // 사이드바 안쪽의 사용자 이름 텍스트 노드 찾기
  const sidebar = document.querySelector('.sidebar, [class*="sidebar"]');
  if (sidebar) {
    // 사이드바 하단 영역 (보통 user-profile)
    const allDivs = sidebar.querySelectorAll('div');
    allDivs.forEach(div => {
      const text = div.textContent || '';
      if ((text.includes('유치원 교사') || text.includes('님 (로그아웃)')) && !div.dataset.mypageBound) {
        // 부모 div도 함께 클릭 가능하게
        const parent = div.closest('div[class*="user"], div[class*="profile"]') || div.parentElement;
        if (parent && !parent.dataset.mypageBound) {
          parent.style.cursor = 'pointer';
          parent.addEventListener('click', function(e) {
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
            if (typeof openMyPage === 'function') {
              e.stopPropagation();
              openMyPage();
            }
          });
          parent.dataset.mypageBound = '1';
        }
      }
    });
  }
}

// 로딩 완료 + 로그인 후 모두 바인딩 시도
window.addEventListener('DOMContentLoaded', function() {
  setTimeout(bindMyPageHandlers, 300);
  setTimeout(bindMyPageHandlers, 1500);
});

// updateUIForUser 시점에도 바인딩
if (typeof updateUIForUser !== 'undefined') {
  const _origUpdateForBind = updateUIForUser;
  updateUIForUser = function(user) {
    _origUpdateForBind(user);
    setTimeout(bindMyPageHandlers, 200);
  };
}

// ============================================================
// 좌상단 로고 클릭 → 홈으로
// ============================================================
function bindLogoClick() {
  // 로고 또는 사이드바 상단의 EDU-bridge 텍스트
  const logoSelectors = [
    '.sidebar-logo',
    '.logo',
    '[class*="brand"]',
  ];
  
  logoSelectors.forEach(sel => {
    document.querySelectorAll(sel).forEach(el => {
      if (!el.dataset.logoBound) {
        el.style.cursor = 'pointer';
        el.addEventListener('click', function() {
          goHome();
        });
        el.dataset.logoBound = '1';
      }
    });
  });
  
  // 텍스트로 찾기 - "EDU-bridge" 텍스트가 있는 div
  const sidebar = document.querySelector('.sidebar, [class*="sidebar"]');
  if (sidebar) {
    const allEls = sidebar.querySelectorAll('div, h1, h2, span');
    allEls.forEach(el => {
      const text = (el.textContent || '').trim();
      if (text === 'EDU-bridge' || text.startsWith('EDU-bridge')) {
        if (!el.dataset.logoBound) {
          // 부모 컨테이너에 핸들러 추가
          const target = el.closest('[class*="logo"], [class*="brand"], [class*="top"]') || el;
          if (!target.dataset.logoBound) {
            target.style.cursor = 'pointer';
            target.addEventListener('click', function() {
              goHome();
            });
            target.dataset.logoBound = '1';
          }
        }
      }
    });
  }
}

window.addEventListener('DOMContentLoaded', function() {
  setTimeout(bindLogoClick, 300);
});
'''

if 'function showLanding' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + landing_js + '\n' + html[last_close:]
        print("✅ 랜딩 + 마이페이지 + 로고 JS 추가")


HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 60)
print("🎉 패치 완료!")
print("=" * 60)
print("\n새 기능:")
print("  1. ✅ 랜딩 페이지 (첫 방문 시 자동 표시)")
print("     - 히어로 / 핵심 기능 4종 / 3단계 이용 흐름 / 통계 / 최종 CTA")
print("     - 카드 호버 시 확대 + 그림자 효과")
print("     - 스크롤 시 페이드인 애니메이션")
print("  2. ✅ 마이페이지 클릭 강제 바인딩")
print("     - 좌하단 프로필/사용자명 클릭 → 마이페이지 모달")
print("  3. ✅ 로고 클릭 → 홈 대시보드 이동")
print("\n💡 랜딩 페이지 다시 보려면:")
print("  브라우저 콘솔에서: localStorage.removeItem('edubridge_visited'); location.reload();")
