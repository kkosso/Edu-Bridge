#!/usr/bin/env python3
"""
fix_insert_modals.py
=====================
fillsPreviewModal과 appliedTemplatesSection이 HTML에 들어갔는지 확인하고
없으면 수동 삽입
"""
from pathlib import Path

HTML_PATH = Path("static/edu-bridge-full.html")
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_insert_fix")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업: {backup}")


# 1) fillsPreviewModal 삽입
fills_preview_modal = '''
<!-- 양식 적용 결과 미리보기/수정 모달 -->
<div id="fillsPreviewModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10000; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeFillsPreview();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:92%; max-width:1100px; max-height:92vh; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3); display:flex; flex-direction:column;">
    <div style="padding:20px 24px; border-bottom:1px solid var(--g2); display:flex; align-items:center; justify-content:space-between;">
      <div>
        <div style="font-size:17px; font-weight:700; color:var(--g9);">📝 양식 적용 결과</div>
        <div id="fillsPreviewSubtitle" style="font-size:12px; color:var(--g5); margin-top:3px;"></div>
      </div>
      <button onclick="closeFillsPreview()" style="width:34px; height:34px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px; color:var(--g7);">×</button>
    </div>
    <div style="flex:1; overflow:hidden; display:flex; gap:1px; background:var(--g2); min-height:400px;">
      <div style="flex:1.4; background:var(--g0); overflow-y:auto; padding:20px;">
        <div id="fillsCellsList"></div>
      </div>
      <div style="flex:1; background:var(--white); display:flex; flex-direction:column;">
        <div style="padding:14px 18px; border-bottom:1px solid var(--g2); font-size:13px; font-weight:700; color:var(--g8);">💬 수정 요청 채팅</div>
        <div id="fillsChatHistory" style="flex:1; overflow-y:auto; padding:14px 18px; min-height:200px;"></div>
        <div style="padding:14px 18px; border-top:1px solid var(--g2);">
          <div style="display:flex; gap:8px;">
            <input type="text" id="fillsChatInput" placeholder="예: 학습 목표를 더 구체적으로" onkeypress="if(event.key==='Enter') sendFillsRefineRequest()" style="flex:1; height:38px; padding:0 12px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; outline:none;">
            <button onclick="sendFillsRefineRequest()" style="padding:0 16px; border:none; border-radius:8px; background:var(--teal); color:var(--white); font-family:var(--font); font-size:12px; font-weight:700; cursor:pointer;">전송</button>
          </div>
          <div style="font-size:11px; color:var(--g5); margin-top:6px; line-height:1.5;">
            💡 예시: "전개의 활동 1을 더 구체적으로", "평가 기준에 협동 항목 추가"
          </div>
        </div>
      </div>
    </div>
    <div style="padding:14px 24px; border-top:1px solid var(--g2); display:flex; gap:10px; justify-content:flex-end; flex-wrap:wrap;">
      <button id="fillsSaveBtn" onclick="saveFillsToHistory()" style="padding:10px 16px; border:1.5px solid var(--teal); border-radius:8px; background:var(--white); color:var(--teal); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer; display:none;">💾 적용 이력에 저장</button>
      <button onclick="downloadFromFillsModal()" style="padding:10px 18px; border:none; border-radius:8px; background:var(--teal); color:var(--white); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">📄 .docx 다운로드</button>
    </div>
  </div>
</div>
'''

if 'id="fillsPreviewModal"' not in html:
    # </body> 직전에 삽입
    if '</body>' in html:
        html = html.replace('</body>', fills_preview_modal + '\n</body>', 1)
        print("✅ fillsPreviewModal 삽입 완료 (</body> 직전)")
    else:
        print("❌ </body> 못 찾음")
else:
    print("ℹ️  fillsPreviewModal 이미 존재")


# 2) appliedTemplatesSection 확인
if 'id="appliedTemplatesSection"' not in html:
    # lessonDetailContent 뒤에 삽입
    old_marker = '<div id="lessonDetailContent" class="lesson-md" style="padding:24px;"></div>'
    new_marker = '''<div id="lessonDetailContent" class="lesson-md" style="padding:24px;"></div>

        <!-- 적용한 양식 이력 -->
        <div id="appliedTemplatesSection" style="border-top:1px solid var(--g2); padding:18px 24px; background:#FAFBFC;">
          <div style="font-size:13px; font-weight:700; color:var(--g8); margin-bottom:10px;">📎 이전에 적용한 양식</div>
          <div id="appliedTemplatesList" style="font-size:12px; color:var(--g6);">불러오는 중...</div>
        </div>'''
    if old_marker in html:
        html = html.replace(old_marker, new_marker)
        print("✅ appliedTemplatesSection 삽입 완료")
    else:
        print("⚠️  lessonDetailContent 패턴 못 찾음")
else:
    print("ℹ️  appliedTemplatesSection 이미 존재")

HTML_PATH.write_text(html, encoding="utf-8")

print("\n🎉 완료!")
print("브라우저 강제 새로고침(Cmd+Shift+R) 후 다시 테스트하세요.")
