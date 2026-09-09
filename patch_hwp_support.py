#!/usr/bin/env python3
"""
patch_hwp_support.py
=====================
.hwp 파일 업로드 지원 추가

설치 필요:
    pip install pyhwp olefile

수행 작업:
1. services/template_parser.py 패치 (parse_hwp_template 추가)
2. main.py 패치 (.hwp 허용)
3. HTML 패치 (accept=".docx,.hwp", 안내 문구 추가)
"""
from pathlib import Path

PARSER_PATH = Path("services/template_parser.py")
MAIN_PATH = Path("main.py")
HTML_PATH = Path("static/edu-bridge-full.html")

if not PARSER_PATH.exists():
    print("❌ services/template_parser.py가 없습니다. patch_phase3_templates.py를 먼저 실행하세요.")
    exit(1)


# ============================================================
# 1) template_parser.py에 .hwp 파싱 함수 추가
# ============================================================
parser_code = PARSER_PATH.read_text(encoding="utf-8")

hwp_function = '''

def parse_hwp_template(file_path: str) -> dict:
    """
    .hwp 파일에서 텍스트를 추출하고 섹션을 감지.
    
    한계: .hwp는 표 구조를 정확히 파싱하기 어려워서 텍스트 기반으로만 분석.
    """
    text_lines = []
    
    # 방법 1: pyhwp(hwp5) 사이 라이브러리 시도
    try:
        from hwp5.proc import rawunicode
        from hwp5.xmlmodel import Hwp5File
        from hwp5.binmodel import ParaText
        
        with Hwp5File(file_path) as hwp:
            for paragraph in hwp.bodytext.section(0):
                if hasattr(paragraph, 'text'):
                    text = paragraph.text
                    if text and text.strip():
                        text_lines.append(text.strip())
    except Exception:
        # 방법 2: olefile로 raw 텍스트 추출
        try:
            import olefile
            import zlib
            
            ole = olefile.OleFileIO(file_path)
            
            # BodyText 스트림 읽기
            dirs = ole.listdir()
            for path in dirs:
                if "BodyText" in path[0] if path else False:
                    try:
                        stream = ole.openstream(path)
                        data = stream.read()
                        # HWP는 zlib 압축된 경우가 많음
                        try:
                            data = zlib.decompress(data, -15)
                        except:
                            pass
                        # 유니코드 텍스트 추출 시도
                        try:
                            text = data.decode("utf-16-le", errors="ignore")
                            # 제어 문자 제거
                            text = "".join(c for c in text if c.isprintable() or c in "\\n\\r\\t")
                            for line in text.split("\\n"):
                                line = line.strip()
                                if line and len(line) > 1:
                                    text_lines.append(line)
                        except Exception:
                            pass
                    except Exception:
                        continue
            ole.close()
        except Exception as e:
            return {"error": f".hwp 파일 파싱 실패: {e}. .docx로 변환 후 업로드해주세요."}
    
    if not text_lines:
        return {"error": "텍스트를 추출할 수 없습니다. .docx로 변환 후 업로드해주세요."}
    
    # 섹션 감지
    sections = []
    seen = set()
    order = 0
    for line in text_lines:
        if _looks_like_section_header(line) and not _is_filler_text(line):
            name = _clean_section_name(line)
            if name and name not in seen:
                seen.add(name)
                sections.append({
                    "name": name,
                    "type": "hwp_text",
                    "order": order,
                })
                order += 1
    
    return {
        "sections": sections,
        "has_tables": False,  # hwp는 표 구조 보존 불가
        "raw_text_sample": "\\n".join(text_lines[:10]),
        "structure_type": "hwp_text",
        "total_sections": len(sections),
        "warning": "⚠️ .hwp는 텍스트만 추출됩니다. 출력은 .docx로만 가능합니다.",
    }
'''

if "parse_hwp_template" not in parser_code:
    parser_code = parser_code + hwp_function
    PARSER_PATH.write_text(parser_code, encoding="utf-8")
    print("✅ template_parser.py: parse_hwp_template 추가")
else:
    print("ℹ️  parse_hwp_template 이미 존재")


# ============================================================
# 2) main.py 패치 - .hwp 허용
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

old_check = '''    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="현재는 .docx 파일만 지원합니다.")'''
new_check = '''    fname_lower = file.filename.lower()
    if not (fname_lower.endswith(".docx") or fname_lower.endswith(".hwp")):
        raise HTTPException(status_code=400, detail=".docx 또는 .hwp 파일만 지원합니다.")
    is_hwp = fname_lower.endswith(".hwp")'''

if old_check in main_code:
    main_code = main_code.replace(old_check, new_check)
    print("✅ main.py: .hwp 파일 허용")

# 파싱 함수 분기 추가
old_parse = '''        # 파싱
        from services.template_parser import parse_docx_template
        parsed = parse_docx_template(str(saved_path))'''
new_parse = '''        # 파싱 (.docx 또는 .hwp)
        if is_hwp:
            from services.template_parser import parse_hwp_template
            parsed = parse_hwp_template(str(saved_path))
        else:
            from services.template_parser import parse_docx_template
            parsed = parse_docx_template(str(saved_path))'''

if old_parse in main_code:
    main_code = main_code.replace(old_parse, new_parse)
    print("✅ main.py: .hwp/.docx 파싱 분기 추가")

# 응답에 warning 포함
old_response = '''        return {
            "id": tpl.id,
            "template_name": tpl.template_name,
            "sections": parsed["sections"],
            "structure_type": parsed["structure_type"],
            "total_sections": parsed["total_sections"],
            "message": "양식이 업로드되었습니다.",
        }'''
new_response = '''        return {
            "id": tpl.id,
            "template_name": tpl.template_name,
            "sections": parsed["sections"],
            "structure_type": parsed["structure_type"],
            "total_sections": parsed["total_sections"],
            "warning": parsed.get("warning"),
            "is_hwp": is_hwp,
            "message": "양식이 업로드되었습니다.",
        }'''

if old_response in main_code:
    main_code = main_code.replace(old_response, new_response)
    print("✅ main.py: 응답에 warning 포함")

MAIN_PATH.write_text(main_code, encoding="utf-8")


# ============================================================
# 3) HTML 패치 - 파일 입력에 .hwp 추가 + 안내
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")

# 파일 입력 accept 변경
html = html.replace(
    '<input id="tplFile" type="file" accept=".docx"',
    '<input id="tplFile" type="file" accept=".docx,.hwp"'
)

# 라벨 텍스트 변경
html = html.replace(
    '<label style="display:block;font-size:12px;font-weight:600;color:var(--g7);margin-bottom:6px;">파일 (.docx만)</label>',
    '<label style="display:block;font-size:12px;font-weight:600;color:var(--g7);margin-bottom:6px;">파일 (.docx 또는 .hwp)</label>'
)

# 안내 문구 추가 (양식 페이지 상단)
old_sub = '<div class="page-sub">우리 유치원 양식(.docx)을 업로드하면 그 양식에 맞춰 지도안을 생성합니다</div>'
new_sub = '''<div class="page-sub">우리 유치원 양식(.docx 또는 .hwp)을 업로드하면 그 양식에 맞춰 지도안을 생성합니다</div>
      <div style="margin-bottom:1rem;padding:12px 14px;background:var(--amber-3);border-left:3px solid var(--amber);border-radius:6px;font-size:12px;color:var(--g7);line-height:1.6;">
        💡 <b>.hwp 파일 안내:</b> .hwp는 텍스트만 추출되며, 출력은 .docx로만 가능합니다. 한컴오피스에서 .docx로 열어서 .hwp로 저장하세요.
      </div>'''
if old_sub in html:
    html = html.replace(old_sub, new_sub)
    print("✅ HTML: .hwp 안내 문구 추가")

# JS 검증 로직도 .hwp 허용으로 변경
html = html.replace(
    "if (!file.name.endsWith('.docx')) { showToast('.docx 파일만 가능합니다.', 'error'); return; }",
    "if (!file.name.toLowerCase().match(/\\.(docx|hwp)$/)) { showToast('.docx 또는 .hwp 파일만 가능합니다.', 'error'); return; }"
)

# 업로드 성공 시 warning이 있으면 표시
old_success = """      resultEl.style.color = 'var(--teal)';
      resultEl.innerHTML = '✅ 업로드 완료! 감지된 섹션: <b>' + data.total_sections + '개</b>';"""
new_success = """      resultEl.style.color = 'var(--teal)';
      let msg = '✅ 업로드 완료! 감지된 섹션: <b>' + data.total_sections + '개</b>';
      if (data.warning) msg += '<br><span style="color:var(--amber);font-size:11px;">' + data.warning + '</span>';
      resultEl.innerHTML = msg;"""

if old_success in html:
    html = html.replace(old_success, new_success)
    print("✅ HTML: warning 표시 로직 추가")

HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 50)
print("🎉 .hwp 지원 패치 완료!")
print("=" * 50)
print("\n다음 단계:")
print("  pip install pyhwp olefile")
print("\n서버 자동 재시작 후 테스트하세요.")
print("\n⚠️ 한계:")
print("  - .hwp는 텍스트만 추출 (표 구조 보존 안 됨)")
print("  - 출력은 항상 .docx")
print("  - 일부 .hwp 파일은 파싱 실패할 수 있음 (한컴이 비공개 포맷이라)")
