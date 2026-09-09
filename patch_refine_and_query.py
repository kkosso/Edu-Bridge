#!/usr/bin/env python3
"""
patch_refine_and_query.py
==========================
1. 지도안 생성 후 채팅으로 수정 요청 기능
2. 저장된 지도안에 원본 검색 프롬프트 한 줄 요약 표시
"""
from pathlib import Path

MAIN_PATH = Path("main.py")
HTML_PATH = Path("static/edu-bridge-full.html")


# ============================================================
# 1) main.py에 /api/lesson/refine API 추가
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

if "/api/lesson/refine" not in main_code:
    refine_api = '''

@app.post("/api/lesson/refine")
async def api_refine_lesson(body: dict):
    """
    지도안 수정 요청 (대화형)

    body: {
        "lesson_markdown": "...",
        "refinement_request": "도입 부분을 더 흥미롭게 바꿔줘",
        "conversation_history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
        ]  # 선택, 이전 대화 맥락
    }
    """
    from services.keyword_extractor import _get_client
    from google.genai import types as genai_types

    markdown = body.get("lesson_markdown", "")
    request_text = body.get("refinement_request", "")
    history = body.get("conversation_history", []) or []

    if not markdown or not request_text:
        raise HTTPException(status_code=400, detail="지도안과 수정 요청이 모두 필요합니다.")

    # 대화 맥락 포함한 프롬프트
    history_text = ""
    if history:
        history_text = "\\n\\n## 이전 대화 맥락\\n"
        for msg in history[-6:]:  # 최근 6개만
            role = "교사" if msg.get("role") == "user" else "AI 응답"
            history_text += f"\\n[{role}]: {msg.get('content', '')[:200]}\\n"

    prompt = f"""당신은 유치원 교사의 지도안 작성을 돕는 AI입니다.
교사가 기존 지도안에 대한 수정 요청을 했습니다. 요청에 따라 지도안을 수정해주세요.

## 현재 지도안 (마크다운)
{markdown}
{history_text}

## 교사의 수정 요청
{request_text}

## 작업 지침
1. 교사의 요청을 정확히 반영하세요. (특정 부분 수정, 추가, 삭제, 톤 변경 등)
2. 요청과 무관한 다른 부분은 그대로 유지하세요.
3. 마크다운 형식(헤더, 리스트, 굵은글씨)을 유지하세요.
4. 유아 발달 단계와 교육적 적절성을 고려하세요.
5. 수정 후 전체 지도안을 마크다운 형식으로 반환하세요.

## 출력 형식
오직 수정된 지도안 마크다운만 출력하세요. 설명이나 머리말 없이 바로 지도안 시작.
"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.5,
                max_output_tokens=8192,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )

        updated_md = response.text.strip()
        # 마크다운 fence 제거
        if updated_md.startswith("```"):
            updated_md = updated_md.split("```")[1]
            if updated_md.startswith("markdown"):
                updated_md = updated_md[8:].strip()
            updated_md = updated_md.rsplit("```", 1)[0].strip()

        # AI 응답 메시지 (요약) 생성
        summary = f"요청하신 대로 수정했어요. 변경된 부분을 확인해주세요!"

        return {
            "updated_markdown": updated_md,
            "assistant_message": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"수정 실패: {str(e)}")

'''

    main_code = main_code.replace(
        '\n@app.get("/api/health")',
        refine_api + '\n@app.get("/api/health")'
    )
    MAIN_PATH.write_text(main_code, encoding="utf-8")
    print("✅ main.py: /api/lesson/refine API 추가")
else:
    print("ℹ️  refine API 이미 존재")


# ============================================================
# 2) HTML 패치 - 수정 채팅 + 검색어 표시
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_refine")
backup.write_text(html, encoding="utf-8")
print(f"✅ HTML 백업: {backup}")


# 2-1) 저장된 지도안 카드의 검색어 표시 강조
old_meta = '''<div class="log-meta">${escapeHtml(l.search_query)} · 만 ${l.age}세 · ${l.duration}분</div>'''
new_meta = '''<div class="log-meta">만 ${l.age}세 · ${l.duration}분</div>
          <div style="display:inline-flex;align-items:center;gap:6px;margin-top:6px;padding:4px 10px;background:var(--g1);border-radius:12px;font-size:11px;color:var(--g7);">
            <span style="opacity:0.6;">🔍 검색어:</span>
            <span style="font-weight:600;">${escapeHtml(l.search_query)}</span>
          </div>'''

if old_meta in html:
    html = html.replace(old_meta, new_meta)
    print("✅ HTML: 저장된 지도안 검색어 표시 강조")


# 2-2) 지도안 출력 영역에 수정 채팅 UI 추가
# outputArea 끝부분에 채팅 박스 추가
old_output_end = '''<div id="outputContent"></div>
      </div>
    </div>
  </div>'''

new_output_end = '''<div id="outputContent"></div>

        <!-- 수정 채팅 -->
        <div id="refineChatBox" style="display:none; margin-top:1.5rem; border-top:1px solid var(--g2); padding-top:1.5rem;">
          <div style="font-size:14px; font-weight:700; color:var(--g8); margin-bottom:10px;">💬 지도안 수정 요청</div>
          <div id="refineChatHistory" style="max-height:200px; overflow-y:auto; margin-bottom:10px;"></div>
          <div style="display:flex; gap:8px;">
            <input type="text" id="refineInput" placeholder="예: 도입 부분을 동물 캐릭터를 활용해서 더 흥미롭게 바꿔줘" 
                   onkeypress="if(event.key==='Enter') sendRefineRequest()"
                   style="flex:1; height:40px; padding:0 14px; border:1.5px solid var(--g2); border-radius:var(--r); font-family:var(--font); font-size:13px; outline:none;">
            <button onclick="sendRefineRequest()" style="padding:0 18px; border:none; border-radius:var(--r); background:var(--teal); color:var(--white); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">전송</button>
          </div>
          <div style="font-size:11px; color:var(--g5); margin-top:8px;">💡 팁: "전개 단계에 협동 활동을 추가해줘", "준비물을 더 간단하게 바꿔줘" 등 자유롭게 요청하세요</div>
        </div>
      </div>
    </div>
  </div>'''

if old_output_end in html:
    html = html.replace(old_output_end, new_output_end)
    print("✅ HTML: Play-Scanner 수정 채팅 UI 추가")


# 2-3) 저장된 지도안 모달에도 수정 채팅 추가
old_detail_end = '''<div id="lessonDetailContent" class="lesson-md" style="padding:24px;"></div>
      </div>
    </div>
  </div>'''

new_detail_end = '''<div id="lessonDetailContent" class="lesson-md" style="padding:24px;"></div>

        <!-- 저장된 지도안 수정 채팅 -->
        <div id="savedRefineChatBox" style="border-top:1px solid var(--g2); padding:20px 24px; background:var(--g0);">
          <div style="font-size:13px; font-weight:700; color:var(--g8); margin-bottom:10px;">💬 이 지도안 수정 요청</div>
          <div id="savedRefineChatHistory" style="max-height:180px; overflow-y:auto; margin-bottom:10px;"></div>
          <div style="display:flex; gap:8px;">
            <input type="text" id="savedRefineInput" placeholder="수정 요청을 입력하세요 (예: 평가 기준을 더 구체적으로)" 
                   onkeypress="if(event.key==='Enter') sendSavedRefineRequest()"
                   style="flex:1; height:38px; padding:0 12px; border:1.5px solid var(--g2); border-radius:var(--r); font-family:var(--font); font-size:13px; outline:none; background:var(--white);">
            <button onclick="sendSavedRefineRequest()" style="padding:0 16px; border:none; border-radius:var(--r); background:var(--teal); color:var(--white); font-family:var(--font); font-size:12px; font-weight:700; cursor:pointer;">전송</button>
          </div>
        </div>
      </div>
    </div>
  </div>'''

if old_detail_end in html:
    html = html.replace(old_detail_end, new_detail_end)
    print("✅ HTML: 저장된 지도안 모달 수정 채팅 추가")


# 2-4) JS 추가
new_js = '''

// ============================================================
// 지도안 수정 채팅
// ============================================================

let _refineHistory = [];  // Play-Scanner용
let _savedRefineHistory = [];  // 저장된 지도안 모달용

// Play-Scanner 수정 채팅
async function sendRefineRequest() {
  const input = document.getElementById('refineInput');
  const request = input.value.trim();
  if (!request) return;
  
  const content = document.getElementById('outputContent');
  const md = content.dataset.markdown;
  if (!md) { showToast('수정할 지도안이 없습니다.', 'error'); return; }
  
  appendRefineMessage('refineChatHistory', 'user', request);
  _refineHistory.push({role: 'user', content: request});
  input.value = '';
  
  const loadingId = appendRefineMessage('refineChatHistory', 'assistant', '⏳ 수정 중...');
  
  try {
    const r = await fetch(API_BASE + '/api/lesson/refine', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        lesson_markdown: md,
        refinement_request: request,
        conversation_history: _refineHistory,
      })
    });
    if (!r.ok) throw new Error('수정 실패');
    const data = await r.json();
    
    // 지도안 업데이트
    content.dataset.markdown = data.updated_markdown;
    if (typeof marked !== 'undefined') {
      content.innerHTML = marked.parse(data.updated_markdown);
    } else {
      content.innerHTML = '<pre style="white-space:pre-wrap;">' + escapeHtml(data.updated_markdown) + '</pre>';
    }
    
    // 채팅 메시지 업데이트
    document.getElementById(loadingId).textContent = data.assistant_message || '✅ 수정 완료!';
    _refineHistory.push({role: 'assistant', content: data.assistant_message || '수정 완료'});
    showToast('지도안이 업데이트되었습니다!', 'success');
  } catch (e) {
    document.getElementById(loadingId).textContent = '❌ ' + e.message;
    showToast('수정 실패: ' + e.message, 'error');
  }
}

// 저장된 지도안 수정 채팅
async function sendSavedRefineRequest() {
  const input = document.getElementById('savedRefineInput');
  const request = input.value.trim();
  if (!request) return;
  
  if (!_currentSavedLesson) { showToast('지도안이 없습니다.', 'error'); return; }
  
  appendRefineMessage('savedRefineChatHistory', 'user', request);
  _savedRefineHistory.push({role: 'user', content: request});
  input.value = '';
  
  const loadingId = appendRefineMessage('savedRefineChatHistory', 'assistant', '⏳ 수정 중...');
  
  try {
    const r = await fetch(API_BASE + '/api/lesson/refine', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        lesson_markdown: _currentSavedLesson.lesson_markdown,
        refinement_request: request,
        conversation_history: _savedRefineHistory,
      })
    });
    if (!r.ok) throw new Error('수정 실패');
    const data = await r.json();
    
    // 메모리에서 지도안 업데이트
    _currentSavedLesson.lesson_markdown = data.updated_markdown;
    
    // 화면 업데이트
    const detailContent = document.getElementById('lessonDetailContent');
    if (typeof marked !== 'undefined') {
      detailContent.innerHTML = marked.parse(data.updated_markdown);
    } else {
      detailContent.innerHTML = '<pre style="white-space:pre-wrap;">' + escapeHtml(data.updated_markdown) + '</pre>';
    }
    detailContent.dataset.markdown = data.updated_markdown;
    
    document.getElementById(loadingId).textContent = data.assistant_message || '✅ 수정 완료!';
    _savedRefineHistory.push({role: 'assistant', content: data.assistant_message || '수정 완료'});
    showToast('지도안이 업데이트되었습니다! 저장하려면 다시 ⭐ 저장하세요.', 'success');
  } catch (e) {
    document.getElementById(loadingId).textContent = '❌ ' + e.message;
    showToast('수정 실패: ' + e.message, 'error');
  }
}

function appendRefineMessage(containerId, role, text) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const id = 'msg_' + Date.now() + '_' + Math.random().toString(36).slice(2,7);
  const isUser = role === 'user';
  const msgHtml = `
    <div style="display:flex; gap:8px; margin-bottom:8px; ${isUser ? 'justify-content:flex-end;' : ''}">
      ${!isUser ? '<div style="width:28px; height:28px; border-radius:50%; background:var(--teal); color:white; display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0;">🤖</div>' : ''}
      <div id="${id}" style="max-width:75%; padding:8px 12px; border-radius:12px; font-size:13px; line-height:1.4; ${isUser ? 'background:var(--teal); color:var(--white);' : 'background:var(--white); border:1px solid var(--g2); color:var(--g9);'}">${escapeHtml(text)}</div>
      ${isUser ? '<div style="width:28px; height:28px; border-radius:50%; background:var(--g3); color:white; display:flex; align-items:center; justify-content:center; font-size:13px; flex-shrink:0;">👤</div>' : ''}
    </div>
  `;
  container.insertAdjacentHTML('beforeend', msgHtml);
  container.scrollTop = container.scrollHeight;
  return id;
}

// 지도안 생성 완료 시 수정 채팅 박스 표시
const _origRenderLessonOutputForRefine = typeof renderLessonOutput !== 'undefined' ? renderLessonOutput : null;
if (_origRenderLessonOutputForRefine) {
  renderLessonOutput = function(card, markdown) {
    _origRenderLessonOutputForRefine(card, markdown);
    const box = document.getElementById('refineChatBox');
    if (box) box.style.display = 'block';
    // 채팅 히스토리 초기화
    _refineHistory = [];
    const history = document.getElementById('refineChatHistory');
    if (history) history.innerHTML = '';
  };
}

// 저장된 지도안 모달 열 때 히스토리 초기화
const _origViewLessonDetail = viewLessonDetail;
viewLessonDetail = async function(id) {
  _savedRefineHistory = [];
  const history = document.getElementById('savedRefineChatHistory');
  if (history) history.innerHTML = '';
  await _origViewLessonDetail(id);
};
'''

if 'function sendRefineRequest' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + new_js + '\n' + html[last_close:]
        print("✅ HTML: 수정 채팅 JS 추가")

HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 50)
print("🎉 수정 채팅 + 검색어 표시 패치 완료!")
print("=" * 50)
print("\n새 기능:")
print("  1. 지도안 생성 후 채팅으로 수정 요청 가능")
print("     - '도입 부분을 더 흥미롭게 바꿔줘'")
print("     - '평가 기준에 협동 평가 항목 추가해줘'")
print("  2. 저장된 지도안 보기에도 동일 기능")
print("  3. 저장된 지도안 카드에 🔍 검색어 뱃지 표시")
