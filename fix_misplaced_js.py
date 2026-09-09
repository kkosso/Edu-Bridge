#!/usr/bin/env python3
"""
fix_misplaced_js.py
====================
marked.min.js 스크립트 태그 안에 잘못 들어간 미리보기 JS를 
올바른 위치(맨 마지막 </script> 직전)로 이동
"""
from pathlib import Path
import re

HTML_PATH = Path("static/edu-bridge-full.html")
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_fix_js")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업: {backup}")

# 1) marked.min.js 태그 안에서 잘못 삽입된 부분 추출
pattern = re.compile(
    r'(<script src="https://cdn\.jsdelivr\.net/npm/marked/marked\.min\.js">)\s*\n(.*?)\n(</script>)',
    re.DOTALL
)
m = pattern.search(html)

if not m:
    print("⚠️  패턴 못 찾음. 이미 올바를 수도 있음.")
    exit(0)

opening_tag = m.group(1)
misplaced_js = m.group(2)
closing_tag = m.group(3)

print(f"✅ 잘못 삽입된 JS 발견 ({len(misplaced_js)}자)")

# 2) 잘못된 부분 제거 - 빈 marked.min.js 태그로 복원
correct_marked = opening_tag + closing_tag
html = html.replace(m.group(0), correct_marked, 1)
print("✅ marked.min.js 태그 복원")

# 3) 추출한 JS를 맨 마지막 </script> 직전에 삽입
last_script_close = html.rfind('</script>')
if last_script_close == -1:
    print("❌ </script> 못 찾음")
    exit(1)

insert_text = '\n' + misplaced_js + '\n'
html = html[:last_script_close] + insert_text + html[last_script_close:]
print("✅ JS를 올바른 위치로 이동 (페이지 끝 </script> 직전)")

HTML_PATH.write_text(html, encoding="utf-8")
print("\n🎉 복구 완료! 브라우저 강제 새로고침(Cmd+Shift+R)하세요.")
