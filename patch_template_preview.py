#!/usr/bin/env python3
"""
patch_template_preview.py
==========================
양식 미리보기 + 양식으로 지도안 만들기 기능 추가

설치 필요:
    pip install mammoth

수행 작업:
1. main.py: /api/templates/{id}/preview API 추가 (docx → HTML 변환)
2. HTML: 
   - 양식 카드에 "👁 미리보기" + "✨ 이 양식으로 지도안 만들기 →" 버튼 추가
   - 미리보기 모달 추가
   - Scanner 진입 시 양식 자동 선택 로직 추가
"""
from pathlib import Path

MAIN_PATH = Path("main.py")
HTML_PATH = Path("static/edu-bridge-full.html")

if not MAIN_PATH.exists() or not HTML_PATH.exists():
    print("❌ backend/ 디렉토리에서 실행하세요.")
    exit(1)


# ============================================================
# 1) main.py에 미리보기 API 추가
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

preview_api = '''

@app.get("/api/templates/{template_id}/preview")
def api_preview_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """양식 미리보기 (docx → HTML 변환, hwp → 텍스트)"""
    tpl = db.query(UserTemplate).filter(
        UserTemplate.id == template_id,
        UserTemplate.user_id == current_user.id
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="양식을 찾을 수 없습니다.")

    file_path = Path(tpl.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다.")

    fname = tpl.original_filename.lower()
    
    # .docx → HTML 변환
    if fname.endswith(".docx"):
        try:
            import mammoth
            with open(file_path, "rb") as f:
                result = mammoth.convert_to_html(f)
                html_content = result.value
            return {
                "type": "html",
                "content": html_content,
                "filename": tpl.original_filename,
                "template_name": tpl.template_name,
            }
        except ImportError:
            raise HTTPException(status_code=500, detail="mammoth 패키지가 설치되지 않았습니다. pip install mammoth")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"변환 실패: {str(e)}")
    
    # .hwp → 텍스트 추출만 (이미 파싱된 raw_text 사용)
    elif fname.endswith(".hwp"):
        try:
            from services.template_parser import parse_hwp_template
            parsed = parse_hwp_template(str(file_path))
            if "error" in parsed:
                return {
                    "type": "text",
                    "content": f"<p style='color:#888;padding:2rem;text-align:center;'>{parsed['error']}</p>",
                    "filename": tpl.original_filename,
                    "template_name": tpl.template_name,
                }
            # 섹션 목록 + 일부 텍스트 표시
            sections = json.loads(tpl.sections_json) if tpl.sections_json else []
            sections_html = "<h3>감지된 섹션</h3><ul>"
            for s in sections:
                sections_html += f"<li>{s.get('name', '')}</li>"
            sections_html += "</ul><hr><h3>추출된 텍스트 (일부)</h3><pre style='white-space:pre-wrap;font-family:inherit;'>"
            sections_html += parsed.get("raw_text_sample", "")
            sections_html += "</pre>"
            return {
                "type": "text",
                "content": sections_html,
                "filename": tpl.original_filename,
                "template_name": tpl.template_name,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f".hwp 미리보기 실패: {str(e)}")
    
    raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식")

'''

if "/api/templates/{template_id}/preview" not in main_code:
    main_code = main_code.replace(
        '\n@app.get("/api/health")',
        preview_api + '\n@app.get("/api/health")'
    )
    MAIN_PATH.write_text(main_code, encoding="utf-8")
    print("✅ main.py: 미리보기 API 추가")
else:
    print("ℹ️  미리보기 API 이미 존재")


# ============================================================
# 2) HTML 패치 - 미리보기 모달 + 버튼 + JS
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_preview")
backup.write_text(html, encoding="utf-8")
print(f"✅ HTML 백업: {backup}")

# 2-1) 양식 카드 렌더링 JS 교체 (버튼 추가)
old_render = '''  list.innerHTML = templates.map(t => {
    const date = new Date(t.created_at).toLocaleDateString('ko-KR');
    const sectionNames = (t.sections || []).slice(0, 6).map(s => s.name).join(' · ');
    const moreCount = Math.max(0, (t.sections || []).length - 6);
    return `
      <li class="log-item">
        <div class="log-thumb">📄</div>
        <div class="log-content">
          <div class="log-title">${escapeHtml(t.template_name)}</div>
          <div class="log-meta">${escapeHtml(t.original_filename)} · ${t.structure_type === 'table' ? '표 형식' : '단락 형식'}</div>
          <div style="font-size:11px;color:var(--g5);margin-top:6px;">
            감지된 섹션 ${(t.sections||[]).length}개: ${escapeHtml(sectionNames)}${moreCount ? ' 외 ' + moreCount + '개' : ''}
          </div>
        </div>
        <div class="log-right">
          <div class="log-date">${date}</div>
          <div class="log-actions">
            <button class="log-action-btn" style="background:var(--coral-3);color:var(--coral);border:none;" onclick="deleteTemplate(${t.id})">🗑 삭제</button>
          </div>
        </div>
      </li>
    `;
  }).join('');'''

new_render = '''  list.innerHTML = templates.map(t => {
    const date = new Date(t.created_at).toLocaleDateString('ko-KR');
    const sectionNames = (t.sections || []).slice(0, 6).map(s => s.name).join(' · ');
    const moreCount = Math.max(0, (t.sections || []).length - 6);
    const tplName = escapeHtml(t.template_name);
    return `
      <li class="log-item">
        <div class="log-thumb">📄</div>
        <div class="log-content">
          <div class="log-title">${tplName}</div>
          <div class="log-meta">${escapeHtml(t.original_filename)} · ${t.structure_type === 'table' ? '표 형식' : t.structure_type === 'hwp_text' ? 'HWP 텍스트' : '단락 형식'}</div>
          <div style="font-size:11px;color:var(--g5);margin-top:6px;">
            감지된 섹션 ${(t.sections||[]).length}개: ${escapeHtml(sectionNames)}${moreCount ? ' 외 ' + moreCount + '개' : ''}
          </div>
          <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap;">
            <button class="log-action-btn" style="background:var(--blue-3);color:var(--blue);border:none;" onclick="previewTemplate(${t.id})">👁 미리보기</button>
            <button class="log-action-btn" style="background:var(--teal);color:var(--white);border:none;font-weight:700;" onclick="useTemplateForLesson(${t.id}, '${tplName.replace(/'/g, "\\\\'")}')">✨ 이 양식으로 지도안 만들기 →</button>
          </div>
        </div>
        <div class="log-right">
          <div class="log-date">${date}</div>
          <div class="log-actions">
            <button class="log-action-btn" style="background:var(--coral-3);color:var(--coral);border:none;" onclick="deleteTemplate(${t.id})">🗑 삭제</button>
          </div>
        </div>
      </li>
    `;
  }).join('');'''

if old_render in html:
    html = html.replace(old_render, new_render)
    print("✅ HTML: 양식 카드 버튼 추가")
else:
    print("⚠️  양식 카드 렌더링 패턴 못 찾음")

# 2-2) 미리보기 모달 추가 (페이지 끝, </script> 직전)
preview_modal = '''
<!-- 양식 미리보기 모달 -->
<div id="tplPreviewModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:9998; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeTplPreview();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; max-width:900px; max-height:90vh; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3); display:flex; flex-direction:column;">
    <div style="display:flex; align-items:center; justify-content:space-between; padding:18px 24px; border-bottom:1px solid var(--g2);">
      <div>
        <div id="tplPreviewTitle" style="font-size:17px; font-weight:700; color:var(--g9);"></div>
        <div id="tplPreviewFilename" style="font-size:12px; color:var(--g5); margin-top:2px;"></div>
      </div>
      <div style="display:flex; gap:8px;">
        <button id="tplPreviewUseBtn" style="padding:8px 14px; background:var(--teal); color:var(--white); border:none; border-radius:var(--r); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">✨ 이 양식으로 지도안 만들기 →</button>
        <button onclick="closeTplPreview()" style="width:36px; height:36px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px; color:var(--g7);">×</button>
      </div>
    </div>
    <div id="tplPreviewContent" style="flex:1; overflow-y:auto; padding:24px; background:var(--g0); color:var(--g9); font-size:13px; line-height:1.6;"></div>
  </div>
</div>

<style>
#tplPreviewContent table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  background: var(--white);
}
#tplPreviewContent table td, #tplPreviewContent table th {
  border: 1px solid var(--g3);
  padding: 8px 12px;
  vertical-align: top;
}
#tplPreviewContent table th {
  background: var(--g1);
  font-weight: 700;
}
#tplPreviewContent h1, #tplPreviewContent h2, #tplPreviewContent h3 {
  margin: 1em 0 0.5em;
  font-weight: 700;
}
#tplPreviewContent p { margin: 0.5em 0; }
#tplPreviewContent ul, #tplPreviewContent ol { margin: 0.5em 0; padding-left: 1.5em; }
</style>
'''

if 'id="tplPreviewModal"' not in html:
    html = html.replace('</script>\n</body>', '</script>\n' + preview_modal + '\n</body>')
    print("✅ HTML: 미리보기 모달 추가")
else:
    print("ℹ️  미리보기 모달 이미 존재")

# 2-3) JS 함수 추가
preview_js = '''

// ============================================================
// 양식 미리보기 + 양식 적용 기능
// ============================================================

let _pendingTemplateId = null;  // Scanner로 이동 후 자동 선택할 양식 ID

async function previewTemplate(templateId) {
  const token = localStorage.getItem('auth_token');
  if (!token) { showModal(); return; }

  const modal = document.getElementById('tplPreviewModal');
  const titleEl = document.getElementById('tplPreviewTitle');
  const filenameEl = document.getElementById('tplPreviewFilename');
  const contentEl = document.getElementById('tplPreviewContent');
  const useBtn = document.getElementById('tplPreviewUseBtn');

  contentEl.innerHTML = '<div style="text-align:center;padding:3rem;color:var(--g5);">미리보기 로딩 중...</div>';
  modal.style.display = 'block';

  try {
    const r = await fetch(API_BASE + '/api/templates/' + templateId + '/preview', {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || '미리보기 실패');
    }
    const data = await r.json();
    titleEl.textContent = '📄 ' + data.template_name;
    filenameEl.textContent = data.filename;
    contentEl.innerHTML = data.content;

    // "이 양식으로 만들기" 버튼 동작 설정
    useBtn.onclick = () => {
      closeTplPreview();
      useTemplateForLesson(templateId, data.template_name);
    };
  } catch (e) {
    contentEl.innerHTML = '<div style="text-align:center;padding:3rem;color:var(--coral);">❌ ' + e.message + '</div>';
  }
}

function closeTplPreview() {
  document.getElementById('tplPreviewModal').style.display = 'none';
}

function useTemplateForLesson(templateId, templateName) {
  _pendingTemplateId = templateId;
  showToast('"' + templateName + '" 양식이 선택되었습니다. Play-Scanner에서 검색해주세요.', 'success');
  // Scanner 페이지로 이동
  const scannerNav = document.querySelector('.nav-item[onclick*="scanner"]');
  showPage('scanner', scannerNav);
}

// Scanner 진입 시 보류 중인 양식이 있으면 드롭다운 자동 선택
const _origShowPagePV = showPage;
showPage = function(id, navEl, section) {
  _origShowPagePV(id, navEl, section);
  if (id === 'scanner' && _pendingTemplateId) {
    // 양식 목록이 로드된 다음 선택
    const trySelect = () => {
      const sel = document.getElementById('exportTplSelect');
      if (sel && sel.options.length > 1) {
        sel.value = String(_pendingTemplateId);
        // 시각적으로 강조 표시
        sel.style.border = '2px solid var(--teal)';
        sel.style.boxShadow = '0 0 0 3px rgba(29,158,117,0.2)';
        setTimeout(() => {
          sel.style.border = '';
          sel.style.boxShadow = '';
        }, 3000);
        _pendingTemplateId = null;
      } else {
        // 아직 목록 로드 안 됐으면 잠시 후 재시도
        setTimeout(trySelect, 300);
      }
    };
    // 양식 목록 로드 트리거
    if (typeof loadTemplates === 'function' && localStorage.getItem('auth_token')) {
      loadTemplates();
    }
    setTimeout(trySelect, 500);
  }
};
'''

if 'function previewTemplate' not in html:
    html = html.replace('</script>\n', preview_js + '\n</script>\n', 1)
    print("✅ HTML: 미리보기 + 양식적용 JS 추가")
else:
    print("ℹ️  미리보기 JS 이미 존재")

HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 50)
print("🎉 양식 미리보기 + 적용 기능 패치 완료!")
print("=" * 50)
print("\n다음 단계:")
print("  pip install mammoth")
print("\n테스트:")
print("  1. 📄 내 양식 페이지로 이동")
print("  2. 업로드한 양식 카드의 [👁 미리보기] 클릭 → 모달에 양식 내용 표시")
print("  3. [✨ 이 양식으로 지도안 만들기 →] 클릭")
print("     → Play-Scanner로 이동 + 양식 드롭다운 자동 선택 + 강조 표시")
print("  4. 검색해서 지도안 생성 → 📄 .docx 다운로드 시 그 양식 적용됨")
