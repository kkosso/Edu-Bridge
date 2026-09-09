#!/usr/bin/env python3
"""
fix_download_override.py
=========================
downloadAsDocx / downloadSavedAsDocx 함수 오버라이드가 안 먹는 문제 수정
→ 원본 함수를 직접 교체하는 방식으로 변경
"""
from pathlib import Path
import re

HTML_PATH = Path("static/edu-bridge-full.html")
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_override_fix")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업: {backup}")

# 1) 기존 downloadAsDocx 함수 본체를 통째로 새 로직으로 교체
old_dl1 = re.compile(
    r'async function downloadAsDocx\(\) \{.*?showToast\(\'다운로드 실패: \' \+ e\.message, \'error\'\);\s*\n\s*\}\s*\n\}',
    re.DOTALL
)
new_dl1 = '''async function downloadAsDocx() {
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
}'''

m1 = old_dl1.search(html)
if m1:
    html = html[:m1.start()] + new_dl1 + html[m1.end():]
    print("✅ downloadAsDocx 직접 교체")
else:
    print("⚠️  downloadAsDocx 패턴 못 찾음")


# 2) 기존 downloadSavedAsDocx 함수 본체 교체
old_dl2 = re.compile(
    r'async function downloadSavedAsDocx\(\) \{.*?showToast\(\'다운로드 실패: \' \+ e\.message, \'error\'\);\s*\n\s*\}\s*\n\}',
    re.DOTALL
)
new_dl2 = '''async function downloadSavedAsDocx() {
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
}'''

m2 = old_dl2.search(html)
if m2:
    html = html[:m2.start()] + new_dl2 + html[m2.end():]
    print("✅ downloadSavedAsDocx 직접 교체")
else:
    print("⚠️  downloadSavedAsDocx 패턴 못 찾음")


# 3) 끝에 추가된 오버라이드 코드 제거 (더 이상 필요 없음)
override_pattern = re.compile(
    r'// =+\s*\n// 기존 다운로드 함수를 인터셉트해서 personal info 체크\s*\n// =+\s*\n'
    r'const _origDownloadAsDocx = downloadAsDocx;.*?'
    r'await checkAndShowPersonalInfo\(\{\s*\n'
    r'\s*markdown: _currentSavedLesson\.lesson_markdown,.*?\}\);\s*\n\};',
    re.DOTALL
)
if override_pattern.search(html):
    html = override_pattern.sub("", html)
    print("✅ 기존 오버라이드 코드 제거")
else:
    print("ℹ️  기존 오버라이드 코드 없거나 이미 제거됨")


HTML_PATH.write_text(html, encoding="utf-8")
print("\n🎉 수정 완료! 브라우저 강제 새로고침(Cmd+Shift+R) 후 다시 테스트하세요.")
