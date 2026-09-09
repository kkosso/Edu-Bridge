#!/usr/bin/env python3
"""
patch_force_overwrite.py
=========================
양식의 예시 내용도 무조건 새로운 내용으로 덮어쓰기

문제: 양식에 예시 텍스트가 채워져 있으면 (예: "수업일시: 2026.04.29") 
      덮어쓰지 않고 그대로 남음
해결: 라벨 셀을 식별하면, 옆/아래의 데이터 셀은 무조건 덮어쓰기
"""
from pathlib import Path

SERVICES = Path("services")
docx_writer_path = SERVICES / "docx_writer.py"

if not docx_writer_path.exists():
    print("❌ services/docx_writer.py 없음")
    exit(1)

code = docx_writer_path.read_text(encoding="utf-8")
backup = docx_writer_path.with_suffix(".py.bak_force")
backup.write_text(code, encoding="utf-8")
print(f"✅ 백업: {backup}")

# 새 _fill_template 함수 - 라벨 셀 옆은 무조건 덮어쓰기
new_fill = '''def _fill_template(template_path: str, output_path: str, sections_data: Dict[str, str]):
    """
    사용자 양식 docx를 열어서 각 섹션에 값을 채워 넣기.

    핵심 전략:
    - 라벨 셀(예: "지도교사", "수업일시", "학습 주제")이 발견되면
    - 옆/아래의 데이터 셀을 **무조건 덮어쓰기** (예시 내용 무시)
    - sections_data에 매칭되는 값이 있을 때만 덮어쓰기
    """
    doc = Document(template_path)
    filled_cells = set()  # 이미 채운 셀 추적

    # 1) 표 기반 채우기
    for table in doc.tables:
        rows = list(table.rows)
        for row_idx, row in enumerate(rows):
            cells = row.cells
            for col_idx, cell in enumerate(cells):
                cell_id = (id(table), row_idx, col_idx)
                if cell_id in filled_cells:
                    continue

                cell_text = cell.text.strip().rstrip(":：").strip()
                if not cell_text:
                    continue

                # 이 셀이 "라벨"인지 판단 (짧은 텍스트 + sections_data와 매칭)
                if not _looks_like_label(cell_text):
                    continue

                value = _find_matching_value(cell_text, sections_data)
                if not value:
                    continue

                # 전략 1: 같은 행의 다음 셀 (예시 내용이 있어도 무조건 덮어쓰기)
                if col_idx + 1 < len(cells):
                    next_cell = cells[col_idx + 1]
                    next_id = (id(table), row_idx, col_idx + 1)
                    next_text = next_cell.text.strip()
                    # 다음 셀이 또 다른 라벨이 아니면 (= 데이터 셀이면) 덮어쓰기
                    if next_id not in filled_cells and not _looks_like_label(next_text):
                        _replace_cell_text(next_cell, value)
                        filled_cells.add(next_id)
                        # 같은 값이 병합되어 옆 셀에도 있으면 그것도 채우기
                        merged_idx = col_idx + 2
                        while merged_idx < len(cells) and cells[merged_idx].text.strip() == next_text:
                            _replace_cell_text(cells[merged_idx], value)
                            filled_cells.add((id(table), row_idx, merged_idx))
                            merged_idx += 1
                        continue

                # 전략 2: 바로 아래 행의 같은 위치 셀
                if row_idx + 1 < len(rows):
                    below_cells = rows[row_idx + 1].cells
                    if col_idx < len(below_cells):
                        below_cell = below_cells[col_idx]
                        below_id = (id(table), row_idx + 1, col_idx)
                        below_text = below_cell.text.strip()
                        if below_id not in filled_cells and not _looks_like_label(below_text):
                            _replace_cell_text(below_cell, value)
                            filled_cells.add(below_id)

    # 2) 단락 기반 채우기
    paragraphs = doc.paragraphs
    for i, para in enumerate(paragraphs):
        text = para.text.strip().rstrip(":：").strip()
        if not text or not _looks_like_label(text):
            continue
        value = _find_matching_value(text, sections_data)
        if value and i + 1 < len(paragraphs):
            next_para = paragraphs[i + 1]
            # 단락은 비어있을 때만 (덮어쓰면 본문 망가짐)
            if not next_para.text.strip() or _is_filler(next_para.text):
                next_para.add_run(value)

    doc.save(output_path)


SECTION_LABEL_KEYWORDS = [
    "활동명", "주제", "제목", "단원", "차시",
    "대상", "연령", "인원", "장소", "일시", "날짜",
    "목표", "목적", "성취",
    "준비물", "교재", "교구", "재료",
    "도입", "전개", "정리", "마무리", "활동내용",
    "활동", "수업", "지도",
    "평가", "유의", "참고", "비고",
    "교사", "유아", "역할", "학생",
    "학교", "학년", "반", "학과",
    "단계", "내용", "형태",
]


def _looks_like_label(text: str) -> bool:
    """이 텍스트가 양식의 라벨(헤더)처럼 보이는지 판단"""
    text = text.strip()
    if not text or len(text) > 30:
        return False
    # 줄바꿈이 적고 짧으면 라벨일 가능성 높음
    if "\\n" in text:
        # 줄바꿈이 있어도 각 줄이 짧으면 라벨 ("학습\\n단계" 같은 경우)
        lines = [l.strip() for l in text.split("\\n") if l.strip()]
        if all(len(l) <= 10 for l in lines):
            for kw in SECTION_LABEL_KEYWORDS:
                if kw in text:
                    return True
            return False
        return False
    # 콜론으로 끝나면 거의 확실히 라벨
    if text.endswith(":") or text.endswith("："):
        return True
    # 키워드 매칭
    for kw in SECTION_LABEL_KEYWORDS:
        if kw in text:
            return True
    return False


def _replace_cell_text(cell, value: str):
    """셀의 기존 텍스트를 모두 제거하고 새 값 삽입"""
    # 첫 단락만 남기고 나머지 단락 제거
    for para in cell.paragraphs[1:]:
        p_element = para._element
        p_element.getparent().remove(p_element)
    # 첫 단락의 모든 run 제거
    first_para = cell.paragraphs[0]
    for run in first_para.runs:
        run.text = ""
    # 새 텍스트 삽입 (줄바꿈 처리)
    lines = value.split("\\n")
    if lines:
        first_para.add_run(lines[0])
        for extra_line in lines[1:]:
            new_para = cell.add_paragraph()
            new_para.add_run(extra_line)'''

# 기존 _fill_template 함수 전체 찾아서 교체
import re
pattern = re.compile(
    r'def _fill_template\(template_path: str.*?(?=\ndef |\nSECTION_LABEL|\Z)',
    re.DOTALL
)

# 기존 _replace_cell_text도 같이 제거 (새 코드에 포함됨)
match = pattern.search(code)
if match:
    # 기존 함수 제거하고 새 함수 삽입
    # _fill_template 부터 시작해서 _replace_cell_text 끝까지 제거
    old_block_pattern = re.compile(
        r'def _fill_template\(template_path: str.*?def _replace_cell_text\(cell, value: str\):.*?new_para\.add_run\(extra_line\)',
        re.DOTALL
    )
    new_block_match = old_block_pattern.search(code)
    if new_block_match:
        code = code[:new_block_match.start()] + new_fill + code[new_block_match.end():]
        print("✅ _fill_template + _replace_cell_text 함수 교체")
    else:
        # 부분적으로만 있을 경우 - 그냥 끝에 추가
        # 일단 _fill_template만 교체
        code = pattern.sub(new_fill + "\n\n", code, count=1)
        print("⚠️  _replace_cell_text 못 찾음, _fill_template만 교체")
else:
    print("❌ _fill_template 함수 못 찾음")
    exit(1)

docx_writer_path.write_text(code, encoding="utf-8")

print("\n🎉 패치 완료!")
print("\n핵심 변경:")
print("  - 라벨 셀(지도교사, 수업일시, 학습 주제 등) 옆의 셀은")
print("    예시 내용이 있어도 무조건 새 내용으로 덮어쓰기")
print("  - 라벨 키워드 확대: 학과, 학년, 단계, 내용, 형태 등 추가")
print("  - 병합된 셀(같은 값이 옆 셀에 반복)도 일관되게 처리")
