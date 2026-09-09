#!/usr/bin/env python3
"""
patch_kidsnote_vlm_fix.py
====================
알림장 페이지의 하드코딩된 VLM 분석 텍스트 제거
실제 분석은 알림장 생성 시 백엔드에서 멀티모달로 수행
"""
from pathlib import Path

HTML_PATH = Path("static/edu-bridge-full.html")
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_vlm_fix")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업 생성: {backup}")

# handleKidsUpload 함수에서 하드코딩 부분 제거
old_handler = '''function handleKidsUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const preview = document.getElementById('kidsImgPreview');
  preview.src = URL.createObjectURL(file);
  preview.classList.add('show');
  document.getElementById('kidsUploadZone').style.display = 'none';
  setTimeout(() => {
    document.getElementById('vlmOutput').classList.add('show');
    typeText('vlmText', '아이가 솔방울을 양손으로 쌓으며 미소 짓고 있습니다. 소근육을 활발히 사용하며 집중하는 모습이 관찰됩니다.', 30);
    document.getElementById('pipe1').textContent = '✅ 완료';
    document.getElementById('pipe1').style.color = 'var(--teal)';
  }, 800);
}'''

new_handler = '''function handleKidsUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const preview = document.getElementById('kidsImgPreview');
  preview.src = URL.createObjectURL(file);
  preview.classList.add('show');
  document.getElementById('kidsUploadZone').style.display = 'none';
  // 실제 VLM 분석은 알림장 생성 시 백엔드에서 수행
  const vlmOutput = document.getElementById('vlmOutput');
  if (vlmOutput) vlmOutput.classList.remove('show');
}'''

if old_handler in html:
    html = html.replace(old_handler, new_handler)
    print("✅ VLM 하드코딩 제거 완료")
    HTML_PATH.write_text(html, encoding="utf-8")
    print("✅ HTML 저장 완료")
else:
    print("⚠️  패턴 못 찾음 - 수동 확인 필요")

print("\n🎉 패치 완료!")
print("이제 사진 업로드해도 가짜 VLM 텍스트가 안 나타납니다.")
print("실제 분석은 '알림장 생성하기' 클릭 시 백엔드에서 수행돼요.")
