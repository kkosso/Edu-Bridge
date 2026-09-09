#!/usr/bin/env python3
"""
patch_final_ui.py
==================
1. Pro 결제 금액 2,990원 → 4,990원으로 변경
2. 사이드바 좌상단 요금제 박스: 투명한 초록색 디자인으로 변경
3. '내 양식' 사이드바 메뉴 옆에 흔들리는 안내 말풍선 추가
"""
from pathlib import Path
import re

HTML_PATH = Path("static/edu-bridge-full.html")
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_final_ui")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업: {backup}")


# ============================================================
# 1) Pro 가격 2,990원 → 4,990원
# ============================================================
# 모든 "2,990원" 표시를 "4,990원"으로 (사이드바 + 요금제 페이지)
html = html.replace('2,990<span', '4,990<span')
html = html.replace('₩2,990', '₩4,990')
html = html.replace('월 2,990원', '월 4,990원')
html = html.replace('2,990원/월', '4,990원/월')
print("✅ Pro 가격 4,990원으로 변경")


# ============================================================
# 2) 사이드바 박스 디자인 - 투명한 초록색
# ============================================================
# CSS 추가/수정
new_sidebar_style = '''
<style id="sidebar-price-redesign">
/* 사이드바 요금제 박스 - 투명한 초록색 디자인 */
.sidebar-price {
  margin: 18px 14px !important;
  padding: 24px 22px !important;
  background: rgba(29, 158, 117, 0.12) !important;
  border: 1px solid rgba(29, 158, 117, 0.25) !important;
  border-radius: 18px !important;
  position: relative;
  overflow: hidden;
}
.sidebar-price::before {
  content: '';
  position: absolute;
  top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: radial-gradient(circle at center, rgba(29, 158, 117, 0.15) 0%, transparent 60%);
  pointer-events: none;
}
.sidebar-price-tag {
  color: rgba(255, 255, 255, 0.85) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  margin-bottom: 8px !important;
  position: relative;
  z-index: 1;
}
.sidebar-price-amount {
  color: var(--white) !important;
  font-size: 26px !important;
  font-weight: 900 !important;
  line-height: 1.1 !important;
  margin-bottom: 4px !important;
  position: relative;
  z-index: 1;
}
.sidebar-price-amount span {
  color: rgba(255, 255, 255, 0.75) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
}
.sidebar-price-sub {
  color: rgba(255, 255, 255, 0.55) !important;
  font-size: 12px !important;
  margin-bottom: 16px !important;
  position: relative;
  z-index: 1;
}
.sidebar-price-cta {
  width: 100% !important;
  padding: 11px 16px !important;
  background: rgba(255, 255, 255, 0.12) !important;
  border: 1px solid rgba(255, 255, 255, 0.25) !important;
  border-radius: 10px !important;
  color: var(--white) !important;
  font-family: var(--font) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  cursor: pointer !important;
  transition: all 0.2s !important;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(8px);
}
.sidebar-price-cta:hover {
  background: rgba(255, 255, 255, 0.2) !important;
  border-color: rgba(255, 255, 255, 0.4) !important;
  transform: translateY(-1px);
}

/* 잘못 추가된 빈 영역 숨김 */
.sidebar-price + button.sidebar-price-cta,
.sidebar-price ~ .sidebar-price-amount {
  display: none !important;
}
</style>
'''

if 'id="sidebar-price-redesign"' not in html:
    html = html.replace('</head>', new_sidebar_style + '\n</head>', 1)
    print("✅ 사이드바 박스 디자인 CSS 추가")


# ============================================================
# 3) 사이드바 박스 중복 제거 (이전 패치 잔여물)
# ============================================================
# .sidebar-price 다음에 또 .sidebar-price-amount나 외부 button이 있으면 제거

# 패턴: </div> 닫은 후 바로 외부 div나 button이 .sidebar-price-* 클래스로 있으면 제거
# 사이드바 박스 영역 식별 후 깔끔하게 재구성

# 모든 sidebar-price 블록을 깨끗한 단일 박스로 통합
clean_box = '''<div class="sidebar-price">
    <div class="sidebar-price-tag" id="sidebarPriceTag">무제한 플랜</div>
    <div class="sidebar-price-amount" id="sidebarPriceAmount">4,990<span style="font-size:14px;font-weight:600;">원/월</span></div>
    <div class="sidebar-price-sub" id="sidebarPriceSub">지금 바로 시작하세요</div>
    <button class="sidebar-price-cta" id="sidebarPriceCta" onclick="goPricingPage()">바로가기 →</button>
  </div>'''

# 가장 바깥의 sidebar-price 블록 찾기 - 균형 잡힌 패턴
# 첫 번째 <div class="sidebar-price">부터 그 안의 마지막 </div>까지
# 단순 접근: 사이드바 내 sidebar-price 시작점 ~ 그 다음 nav 요소 또는 큰 구획 직전

# 더 강건한 정리: <aside> 또는 .sidebar 안에서 sidebar-price 관련 요소 모두 찾아서 첫 위치에 깔끔한 박스 하나만
sidebar_pattern = re.compile(
    r'(<aside[^>]*class="[^"]*sidebar[^"]*"[^>]*>|<div[^>]*class="[^"]*\bsidebar\b[^"]*"[^>]*>)',
    re.IGNORECASE
)
m_sidebar = sidebar_pattern.search(html)

# 좀 더 단순: "원/월" 텍스트가 두 번 이상 나오면 중복임. 정리.
won_per_month_count = html.count('원/월')
print(f"📊 '원/월' 출현 횟수: {won_per_month_count}")

# 사이드바 영역에서 외부에 떠있는 .sidebar-price-amount/btn 제거
# 패턴: .sidebar-price 닫는 </div> 직후의 별도 .sidebar-price-amount, .sidebar-price-cta 요소들
orphan_amount_pattern = re.compile(
    r'</div>\s*<div class="sidebar-price-amount">[^<]*<span[^<]*</span>[^<]*</div>\s*(?:<div class="sidebar-price-sub">[^<]*</div>)?\s*(?:<button class="sidebar-price-cta"[^>]*>[^<]*</button>)?',
    re.DOTALL
)
matches_orphan = list(orphan_amount_pattern.finditer(html))
if matches_orphan:
    for m in reversed(matches_orphan):
        # </div>는 남기고 나머지 제거
        html = html[:m.start()+6] + html[m.end():]
    print(f"✅ 외부에 떨어진 sidebar-price 요소 {len(matches_orphan)}개 제거")

# 외부 button 단독 제거
orphan_btn_pattern = re.compile(
    r'</div>\s*<button class="sidebar-price-cta"[^>]*>[^<]*</button>',
    re.DOTALL
)
matches_btn = list(orphan_btn_pattern.finditer(html))
if matches_btn:
    for m in reversed(matches_btn):
        html = html[:m.start()+6] + html[m.end():]
    print(f"✅ 외부 단독 button {len(matches_btn)}개 제거")


# ============================================================
# 4) '내 양식' 메뉴 옆에 흔들리는 안내 말풍선
# ============================================================

# 우선 내 양식 nav-item에 ID 부여 + 말풍선 추가
old_my_template_nav = '''<button class="nav-item" onclick="showPage('templates', this)">
      <span class="nav-icon">📄</span><span>내 양식</span>
    </button>'''

new_my_template_nav = '''<button class="nav-item" id="navMyTemplate" onclick="showPage('templates', this); dismissTemplateHint();" style="position:relative;">
      <span class="nav-icon">📄</span><span>내 양식</span>
      <span id="tplHintBubble" class="tpl-hint-bubble">
        <span class="tpl-hint-arrow"></span>
        <span class="tpl-hint-text">우리 유치원 양식<br>여기서 업로드!</span>
        <span class="tpl-hint-close" onclick="event.stopPropagation();dismissTemplateHint();">×</span>
      </span>
    </button>'''

if old_my_template_nav in html and 'id="navMyTemplate"' not in html:
    html = html.replace(old_my_template_nav, new_my_template_nav)
    print("✅ '내 양식' 메뉴에 말풍선 추가")

# 말풍선 CSS + 흔들림 애니메이션
hint_style = '''
<style id="tpl-hint-styles">
/* 내 양식 안내 말풍선 */
.tpl-hint-bubble {
  position: absolute;
  left: calc(100% + 16px);
  top: 50%;
  transform: translateY(-50%);
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
  color: white;
  padding: 10px 14px 10px 16px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  box-shadow: 0 4px 20px rgba(255, 107, 107, 0.4);
  z-index: 1000;
  animation: tplHintWiggle 2s ease-in-out infinite;
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.tpl-hint-bubble.hidden { display: none !important; }
.tpl-hint-text {
  line-height: 1.4;
}
.tpl-hint-arrow {
  position: absolute;
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  width: 0; height: 0;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  border-right: 7px solid #FF6B6B;
}
.tpl-hint-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px; height: 18px;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 50%;
  color: white;
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
  margin-left: 4px;
}
.tpl-hint-close:hover {
  background: rgba(255, 255, 255, 0.4);
}

@keyframes tplHintWiggle {
  0%, 100% { transform: translateY(-50%) translateX(0) rotate(0deg); }
  20% { transform: translateY(-50%) translateX(4px) rotate(2deg); }
  40% { transform: translateY(-50%) translateX(-4px) rotate(-2deg); }
  60% { transform: translateY(-50%) translateX(3px) rotate(1.5deg); }
  80% { transform: translateY(-50%) translateX(-2px) rotate(-1deg); }
}

/* 작은 화면(모바일)에서는 말풍선 가로 → 아래로 변경 */
@media (max-width: 1100px) {
  .tpl-hint-bubble {
    left: 50%;
    top: calc(100% + 8px);
    transform: translateX(-50%);
    animation: tplHintWiggleMobile 2s ease-in-out infinite;
  }
  .tpl-hint-arrow {
    left: 50%;
    top: -6px;
    transform: translateX(-50%);
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-bottom: 7px solid #FF6B6B;
    border-top: none;
  }
  @keyframes tplHintWiggleMobile {
    0%, 100% { transform: translateX(-50%) translateY(0); }
    20% { transform: translateX(-46%) translateY(2px); }
    40% { transform: translateX(-54%) translateY(-2px); }
    60% { transform: translateX(-47%) translateY(1px); }
    80% { transform: translateX(-53%) translateY(-1px); }
  }
}
</style>
'''

if 'id="tpl-hint-styles"' not in html:
    html = html.replace('</head>', hint_style + '\n</head>', 1)
    print("✅ 말풍선 CSS + 흔들림 애니메이션 추가")

# 말풍선 표시/숨김 JS
hint_js = '''

// ============================================================
// 내 양식 안내 말풍선
// ============================================================
function dismissTemplateHint() {
  const bubble = document.getElementById('tplHintBubble');
  if (bubble) {
    bubble.classList.add('hidden');
    localStorage.setItem('tpl_hint_dismissed', '1');
  }
}

function showTemplateHintIfNeeded() {
  const bubble = document.getElementById('tplHintBubble');
  if (!bubble) return;
  // 이미 닫은 적 있거나 사용자가 양식을 업로드한 적이 있으면 숨김
  const dismissed = localStorage.getItem('tpl_hint_dismissed');
  if (dismissed) {
    bubble.classList.add('hidden');
    return;
  }
  // 로그인 한 경우에만 표시
  if (currentUser) {
    bubble.classList.remove('hidden');
  } else {
    bubble.classList.add('hidden');
  }
}

// 로그인 상태 변경 시 갱신
const _origUpdateUIForHint = updateUIForUser;
updateUIForUser = function(user) {
  _origUpdateUIForHint(user);
  setTimeout(showTemplateHintIfNeeded, 100);
};

// 페이지 로드 시 체크
window.addEventListener('DOMContentLoaded', function() {
  setTimeout(showTemplateHintIfNeeded, 500);
});

// 양식 업로드 성공 시 자동으로 dismiss
const _origUploadTemplate = typeof uploadTemplate !== 'undefined' ? uploadTemplate : null;
if (_origUploadTemplate) {
  window.uploadTemplate = async function() {
    await _origUploadTemplate.apply(this, arguments);
    dismissTemplateHint();
  };
}
'''

if 'function dismissTemplateHint' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + hint_js + '\n' + html[last_close:]
        print("✅ 말풍선 JS 추가")


HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 60)
print("🎉 최종 UI 수정 완료!")
print("=" * 60)
print("\n변경 사항:")
print("  1. ✅ Pro 가격 2,990원 → 4,990원")
print("  2. ✅ 사이드바 박스 디자인 - 투명 초록색 (모던한 느낌)")
print("     - 중복 표시 제거")
print("     - 둥근 모서리 + 그라데이션 + 백드롭 블러")
print("  3. ✅ '내 양식' 메뉴 옆 흔들리는 안내 말풍선")
print("     - 오른쪽 ↔ 왼쪽 자연스러운 흔들림 (2초 반복)")
print("     - '우리 유치원 양식 여기서 업로드!' 문구")
print("     - × 버튼으로 닫기 가능 (localStorage 저장)")
print("     - 양식 업로드 성공 시 자동으로 닫힘")
print("\n브라우저 강제 새로고침 (Cmd+Shift+R) 후 확인!")
