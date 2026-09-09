#!/usr/bin/env python3
"""
patch_ui_fixes.py
==================
1. 사이드바 요금제 박스 UI 깨짐 수정 (이중 표시 제거)
2. FAQ 안내 문구 변경 (캡스톤 → 베타 테스트, 정식 출시 일자)
3. 사이드바 좌하단 프로필 영역 클릭 → 마이페이지로 이동
4. 푸터 카피라이트 + 광고 문의 이메일 변경
"""
from pathlib import Path
import re

HTML_PATH = Path("static/edu-bridge-full.html")
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_ui_fixes")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업: {backup}")


# ============================================================
# 1) 사이드바 요금제 박스 - 이중 표시 제거 + 깔끔하게 정돈
# ============================================================
# 현재 두 개의 sidebar-price 박스가 있어서 충돌하는 듯
# 첫 번째 박스(또는 잘못된 박스) 제거하고 깨끗한 하나만 남기기

# 모든 sidebar-price 블록 찾기
sidebar_price_pattern = re.compile(
    r'<div class="sidebar-price">.*?</div>\s*</div>',
    re.DOTALL
)
matches = list(sidebar_price_pattern.finditer(html))
print(f"📊 sidebar-price 블록 개수: {len(matches)}")

# 정리된 깨끗한 박스
clean_sidebar_box = '''<div class="sidebar-price">
    <div class="sidebar-price-tag" id="sidebarPriceTag">무제한 플랜</div>
    <div class="sidebar-price-amount" id="sidebarPriceAmount">2,990<span style="font-size:14px;font-weight:600;">원/월</span></div>
    <div class="sidebar-price-sub" id="sidebarPriceSub">지금 바로 시작하세요</div>
    <button class="sidebar-price-cta" id="sidebarPriceCta" onclick="goPricingPage()">바로가기 →</button>
  </div>'''

# 모든 sidebar-price 블록을 하나로 통합
# 단순한 패턴으로 다시 시도
simpler_pattern = re.compile(
    r'<div class="sidebar-price">(?:(?!<div class="sidebar-price">).)*?</div>\s*</div>',
    re.DOTALL
)
all_blocks = simpler_pattern.findall(html)
print(f"📊 단순 패턴 매칭: {len(all_blocks)}개")

# 더 정확한 패턴: <div class="sidebar-price">로 시작해서 닫는 </div>를 찾기
# 균형 잡힌 패턴 사용 (간단한 방식: 처음 </div></div> 만나는 곳까지)
balanced_pattern = re.compile(
    r'<div class="sidebar-price">.*?<button[^>]*sidebar-price-cta[^>]*>.*?</button>\s*</div>',
    re.DOTALL
)
balanced_matches = list(balanced_pattern.finditer(html))
print(f"📊 balanced 패턴 매칭: {len(balanced_matches)}개")

# 모든 매치를 하나의 깨끗한 박스로 교체 (마지막 하나만 남기고 제거)
if len(balanced_matches) > 1:
    # 뒤에서부터 제거 (인덱스 안 꼬이게)
    for m in reversed(balanced_matches[1:]):
        html = html[:m.start()] + html[m.end():]
    print(f"✅ 중복 sidebar-price 박스 {len(balanced_matches)-1}개 제거")

# 남은 하나를 깨끗한 버전으로 교체
balanced_matches_after = list(balanced_pattern.finditer(html))
if balanced_matches_after:
    m = balanced_matches_after[0]
    html = html[:m.start()] + clean_sidebar_box + html[m.end():]
    print("✅ sidebar-price 박스 깨끗하게 교체")


# ============================================================
# 2) FAQ 안내 문구 변경
# ============================================================
old_faq_payment = '''<div style="margin-bottom:1rem;"><b style="color:var(--g9);">Q. 결제는 어떻게 하나요?</b><br>현재는 학부 캡스톤 프로젝트로 운영 중이며, 실제 결제 시스템은 도입 예정입니다. 데모용으로 즉시 활성화됩니다.</div>'''
new_faq_payment = '''<div style="margin-bottom:1rem;"><b style="color:var(--g9);">Q. 결제는 어떻게 하나요?</b><br>현재 베타 테스트 중이며 정식 출시를 앞두고 있습니다. 정식 출시는 <b>2026년 6월 말 ~ 7월 초</b> 예정이며, 그 전까지는 결제 시스템이 비활성화되어 있습니다. 데모용으로 즉시 Pro 기능을 체험하실 수 있습니다.</div>'''

if old_faq_payment in html:
    html = html.replace(old_faq_payment, new_faq_payment)
    print("✅ FAQ 결제 안내 문구 변경 (베타 테스트)")
else:
    print("⚠️  FAQ 결제 패턴 못 찾음")


# ============================================================
# 3) 사이드바 좌하단 프로필 영역 → 마이페이지로 이동
# ============================================================
# 사용자 프로필 영역 찾기 (송민서 / 유치원 교사 표시되는 곳)
# 보통 sidebar-user 또는 비슷한 클래스

# 여러 가능한 패턴 시도
profile_patterns = [
    # 패턴 1: sidebar-user 클래스
    (
        r'<div class="sidebar-user"([^>]*)>',
        r'<div class="sidebar-user"\1 style="cursor:pointer;" onclick="openMyPage()">'
    ),
    # 패턴 2: user-profile 클래스
    (
        r'<div class="user-profile"([^>]*)>',
        r'<div class="user-profile"\1 style="cursor:pointer;" onclick="openMyPage()">'
    ),
]

profile_added = False
for pat, repl in profile_patterns:
    if re.search(pat, html) and 'openMyPage()' not in html[:html.find(re.search(pat, html).group())+200] if re.search(pat, html) else False:
        # 이미 onclick 있으면 스킵
        m = re.search(pat, html)
        if m and 'openMyPage()' not in html[max(0, m.start()-100):m.end()+100]:
            html = re.sub(pat, repl, html, count=1)
            print(f"✅ 사이드바 프로필 영역에 onclick 추가")
            profile_added = True
            break

# 패턴이 안 맞으면 송민서 / 유치원 교사 텍스트 근처 찾기
if not profile_added:
    # "송민서" 또는 사용자 이름이 표시되는 부분 찾기
    user_display_pattern = re.compile(
        r'(<div[^>]*class="[^"]*sidebar[^"]*"[^>]*>(?:[^<]|<(?!/?div))*?(?:송민서|유치원 교사|<span[^>]*>(?:송|민서|유치원)))',
        re.DOTALL
    )
    m = user_display_pattern.search(html)
    if m:
        # 해당 div에 onclick 추가
        original = m.group(1)
        # 첫 번째 <div ... > 에 style/onclick 추가
        new_div = re.sub(
            r'<div([^>]*?)>',
            r'<div\1 style="cursor:pointer;" onclick="openMyPage()">',
            original,
            count=1
        )
        html = html.replace(original, new_div, 1)
        print("✅ 사용자 표시 영역에 마이페이지 onclick 추가")
        profile_added = True

# 그래도 못 찾으면 currentUser 표시 영역 강제 검색
if not profile_added:
    # 일반적으로 사이드바 좌하단의 사용자 표시는 .sidebar 영역 끝부분에 있음
    # avatar circle 패턴 찾기
    avatar_pattern = re.compile(
        r'(<div[^>]*style="[^"]*border-radius:\s*50%[^"]*"[^>]*>[^<]*(?:송|S|U)[^<]*</div>)',
        re.DOTALL
    )
    m = avatar_pattern.search(html)
    if m:
        # 그 div의 부모를 찾아서 클릭 가능하게
        # 간단히 그 div 자체에 onclick 추가
        original = m.group(1)
        new_div = re.sub(
            r'<div([^>]*style="[^"]*?)"',
            r'<div\1; cursor:pointer;" onclick="openMyPage()"',
            original,
            count=1
        )
        html = html.replace(original, new_div, 1)
        print("✅ 아바타 영역에 마이페이지 onclick 추가")
        profile_added = True

if not profile_added:
    print("⚠️  프로필 영역 못 찾음 - 수동 확인 필요")


# ============================================================
# 4) 푸터 카피라이트 변경
# ============================================================
old_copyright = '<div>학부 캡스톤 프로젝트 · 송민서</div>'
new_copyright = '<div>Team 초코소라빵 · <a href="mailto:minseosong5@gmail.com" style="color:#9ca3af; text-decoration:none;">minseosong5@gmail.com</a></div>'

if old_copyright in html:
    html = html.replace(old_copyright, new_copyright)
    print("✅ 푸터 카피라이트 변경 (Team 초코소라빵)")

# 광고 문의 이메일 변경 (edubridge@example.com → minseosong5@gmail.com)
html = html.replace(
    'href="mailto:edubridge@example.com"',
    'href="mailto:minseosong5@gmail.com"'
)
html = html.replace(
    'edubridge@example.com',
    'minseosong5@gmail.com'
)
print("✅ 광고 문의 이메일 변경 (minseosong5@gmail.com)")


# ============================================================
# 5) 추가 안전장치: openMyPage 함수가 호출 가능한지 보장
# ============================================================
# 사이드바 좌하단의 마이페이지 진입을 위한 글로벌 onclick 추가 (fallback)
# 이미 패치가 있어도 추가하지 않도록 체크
if 'window.openMyPage' not in html:
    fallback_js = '''

// 사이드바 좌하단 프로필 클릭 fallback
document.addEventListener('DOMContentLoaded', function() {
  // 사용자 정보가 표시되는 영역들에 클릭 핸들러 자동 추가
  setTimeout(function() {
    const userNameEls = document.querySelectorAll('.sidebar-user, .user-profile, [class*="user-info"]');
    userNameEls.forEach(function(el) {
      if (!el.dataset.mypageBound) {
        el.style.cursor = 'pointer';
        el.addEventListener('click', function(e) {
          if (typeof openMyPage === 'function') {
            e.stopPropagation();
            openMyPage();
          }
        });
        el.dataset.mypageBound = '1';
      }
    });
    // window 전역에도 등록
    window.openMyPage = window.openMyPage || function() {
      const modal = document.getElementById('myPageModal');
      if (modal) modal.style.display = 'block';
    };
  }, 500);
});
'''
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + fallback_js + html[last_close:]
        print("✅ 마이페이지 fallback JS 추가")


HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 60)
print("🎉 UI 수정 패치 완료!")
print("=" * 60)
print("\n변경 사항:")
print("  1. ✅ 사이드바 요금제 박스 이중 표시 제거")
print("  2. ✅ FAQ 안내: 베타 테스트 + 6월말~7월초 정식 출시 예정")
print("  3. ✅ 사이드바 좌하단 프로필 클릭 → 마이페이지")
print("  4. ✅ 푸터: 'Team 초코소라빵' + minseosong5@gmail.com")
print("\n브라우저 강제 새로고침 (Cmd+Shift+R) 후 확인하세요!")
