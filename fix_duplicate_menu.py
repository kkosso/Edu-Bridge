#!/usr/bin/env python3
"""
fix_duplicate_menu.py
======================
사이드바와 페이지에 중복된 '내 양식' 항목을 정리
"""
from pathlib import Path
import re

HTML_PATH = Path("static/edu-bridge-full.html")
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_dedupe")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업 생성: {backup}")

# 1) 사이드바 '내 양식' 메뉴 중복 확인 및 정리
menu_pattern = re.compile(
    r"""\s*<button class="nav-item" onclick="showPage\('templates', this\)">\s*<span class="nav-icon">📄</span><span>내 양식</span>\s*</button>""",
    re.DOTALL
)
menu_matches = menu_pattern.findall(html)
print(f"  사이드바 '내 양식' 메뉴: {len(menu_matches)}개 발견")

if len(menu_matches) > 1:
    # 첫 번째만 남기고 나머지 제거
    first_match = menu_matches[0]
    # 모든 발생 위치 찾기
    html_temp = html
    # 첫 번째 위치만 보존
    first_idx = html_temp.find(first_match)
    # 첫 번째 이후의 나머지 매치들 제거
    after_first = html_temp[first_idx + len(first_match):]
    after_first_cleaned = menu_pattern.sub("", after_first)
    html = html_temp[:first_idx + len(first_match)] + after_first_cleaned
    print(f"✅ 사이드바 중복 메뉴 {len(menu_matches) - 1}개 제거")

# 2) page-templates div 중복 확인 및 정리
page_count = html.count('id="page-templates"')
print(f"  '내 양식' 페이지: {page_count}개 발견")

if page_count > 1:
    # page-templates 시작부터 다음 <!-- 까지의 블록을 찾기
    page_pattern = re.compile(
        r'<!-- ════ MY TEMPLATES PAGE ════ -->\s*<div class="page" id="page-templates">.*?</div>\s*</div>\s*',
        re.DOTALL
    )
    page_matches = page_pattern.findall(html)
    if len(page_matches) > 1:
        first_page = page_matches[0]
        first_idx = html.find(first_page)
        after = html[first_idx + len(first_page):]
        after_cleaned = page_pattern.sub("", after)
        html = html[:first_idx + len(first_page)] + after_cleaned
        print(f"✅ 중복 페이지 {len(page_matches) - 1}개 제거")

# 3) loadTemplates 함수 중복 정리 (있으면)
js_pattern = re.compile(
    r'\n// ============================================================\n// Phase 3: 커스텀 양식 기능\n// ============================================================.*?\n// showPage 후크에 templates 페이지 자동 로드 추가\nconst _origShowPageT = showPage;\nshowPage = function\(id, navEl, section\) \{\n  _origShowPageT\(id, navEl, section\);\n  if \(id === \'templates\'\) loadTemplates\(\);\n.*?\n\};',
    re.DOTALL
)
js_matches = js_pattern.findall(html)
print(f"  Phase 3 JS 블록: {len(js_matches)}개 발견")

if len(js_matches) > 1:
    first_js = js_matches[0]
    first_idx = html.find(first_js)
    after = html[first_idx + len(first_js):]
    after_cleaned = js_pattern.sub("", after)
    html = html[:first_idx + len(first_js)] + after_cleaned
    print(f"✅ 중복 JS {len(js_matches) - 1}개 제거")

HTML_PATH.write_text(html, encoding="utf-8")
print("\n🎉 중복 정리 완료!")
print("브라우저 새로고침 (Cmd+Shift+R) 후 확인하세요.")
