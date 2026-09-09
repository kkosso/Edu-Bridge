#!/usr/bin/env python3
"""
patch_kidsnote.py
====================
AI 알림장(학부모 알리미) 기능을 실제 API 연동으로 교체

사용법:
    cd backend
    python3 patch_kidsnote.py
"""
from pathlib import Path

HTML_PATH = Path("static/edu-bridge-full.html")
MAIN_PATH = Path("main.py")

if not HTML_PATH.exists():
    print(f"❌ {HTML_PATH}을 찾을 수 없습니다.")
    exit(1)

html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_kidsnote")
backup.write_text(html, encoding="utf-8")
print(f"✅ 백업 생성: {backup}")


# ============================================================
# PATCH 1: 알림장 입력란에 텍스트 입력창 추가
# ============================================================
old_select = '''          <div class="card" style="margin-bottom:1rem;">
            <div class="card-title" style="font-size:14px;margin-bottom:10px;">수업 목표 선택 <span style="font-size:11px;color:var(--g5);font-weight:400">(Pipeline 1 연동)</span></div>
            <select style="width:100%;height:40px;border:1.5px solid var(--g2);border-radius:var(--r);padding:0 1rem;font-family:var(--font);font-size:13px;outline:none;background:var(--white);color:var(--g9);">
              <option>자연물을 통한 크기 비교 및 소근육 발달</option>
              <option>색채 인식 및 미적 감각 향상</option>
              <option>수 개념 이해 및 논리적 사고</option>
              <option>협동 놀이를 통한 사회성 발달</option>
            </select>
          </div>'''

new_select = '''          <div class="card" style="margin-bottom:1rem;">
            <div class="card-title" style="font-size:14px;margin-bottom:10px;">오늘의 활동 내용 입력</div>
            <textarea id="kidsActivityText" placeholder="예: 오늘은 나뭇잎과 물감을 활용하여 협동 놀이를 진행했습니다. 아이들이 색깔을 섞으며 즐거워했어요." style="width:100%;min-height:90px;border:1.5px solid var(--g2);border-radius:var(--r);padding:10px 14px;font-family:var(--font);font-size:13px;outline:none;background:var(--white);color:var(--g9);resize:vertical;line-height:1.5;" onkeyup="updateActivityCount()"></textarea>
            <div style="text-align:right;font-size:11px;color:var(--g5);margin-top:4px;"><span id="activityCharCount">0</span>자</div>
          </div>'''

if old_select in html:
    html = html.replace(old_select, new_select)
    print("✅ PATCH 1: 활동 내용 입력창 추가")
else:
    print("⚠️  PATCH 1: 패턴 못 찾음")


# ============================================================
# PATCH 2: 복사 버튼 추가
# ============================================================
old_actions = '''          <div class="note-actions">
            <button class="btn-regen" onclick="generateNote()">🔄 다시 생성</button>
            <button class="btn-send">📤 학부모 발송</button>
          </div>'''

new_actions = '''          <div class="note-actions">
            <button class="btn-regen" onclick="generateNote()">🔄 다시 생성</button>
            <button class="btn-regen" onclick="copyNote()" id="btnCopyNote" style="background:var(--g1);color:var(--g7);border:1px solid var(--g2);">📋 복사</button>
          </div>'''

if old_actions in html:
    html = html.replace(old_actions, new_actions)
    print("✅ PATCH 2: 복사 버튼 추가")
else:
    print("⚠️  PATCH 2: 패턴 못 찾음")


# ============================================================
# PATCH 3: mock generateNote → 실제 API 호출로 교체
# ============================================================
old_generate = '''function generateNote() {
  const btn = document.getElementById('genNoteBtn');
  const spinner = document.getElementById('noteSpinner');
  const text = document.getElementById('noteGenText');
  const output = document.getElementById('noteOutputText');

  btn.classList.add('loading');
  spinner.classList.add('show');
  text.textContent = '생성 중...';

  document.getElementById('pipe2').textContent = '⚙️ 처리중';
  document.getElementById('pipe2').style.color = 'var(--amber)';

  setTimeout(() => {
    document.getElementById('pipe2').textContent = '✅ 완료';
    document.getElementById('pipe2').style.color = 'var(--teal)';
    document.getElementById('pipe3').textContent = '⚙️ 처리중';
    document.getElementById('pipe3').style.color = 'var(--amber)';

    setTimeout(() => {
      const activeTone = document.querySelector('.tone-chip.active');
      const tone = activeTone ? activeTone.textContent.trim() : '🤗 다정하게';
      const noteText = NOTES[tone] || NOTES['🤗 다정하게'];

      output.style.color = 'var(--g9)';
      output.style.fontStyle = 'normal';

      document.getElementById('pipe3').textContent = '✅ 완료';
      document.getElementById('pipe3').style.color = 'var(--teal)';

      typeText('noteOutputText', noteText, 20, () => {
        document.getElementById('noteCharCount').textContent = noteText.length + ' / 300자';
      });

      btn.classList.remove('loading');
      spinner.classList.remove('show');
      text.textContent = '✨ 알림장 생성하기';
    }, 600);
  }, 800);
}'''

new_generate = '''function updateActivityCount() {
  const t = document.getElementById('kidsActivityText');
  if (t) document.getElementById('activityCharCount').textContent = t.value.length;
}

async function generateNote() {
  const activityText = document.getElementById('kidsActivityText')?.value.trim();
  if (!activityText) {
    showToast('활동 내용을 입력해주세요!', 'error');
    return;
  }

  const btn = document.getElementById('genNoteBtn');
  const spinner = document.getElementById('noteSpinner');
  const text = document.getElementById('noteGenText');
  const output = document.getElementById('noteOutputText');
  const activeTone = document.querySelector('.tone-chip.active');
  const tone = activeTone ? activeTone.textContent.trim() : '🤗 다정하게';

  // UI 로딩 상태
  btn.classList.add('loading');
  spinner.classList.add('show');
  text.textContent = '생성 중...';
  output.textContent = '알림장을 작성하고 있습니다...';
  output.style.color = 'var(--g5)';

  document.getElementById('pipe1').textContent = '⚙️ 처리중';
  document.getElementById('pipe1').style.color = 'var(--amber)';
  document.getElementById('pipe2').textContent = '대기중';
  document.getElementById('pipe3').textContent = '대기중';

  try {
    // 이미지가 있으면 FormData로 전송
    const formData = new FormData();
    formData.append('activity_text', activityText);
    formData.append('tone', tone);

    const kidsFile = document.getElementById('kidsFile');
    if (kidsFile && kidsFile.files[0]) {
      formData.append('image', kidsFile.files[0]);
    }

    document.getElementById('pipe1').textContent = '✅ 완료';
    document.getElementById('pipe1').style.color = 'var(--teal)';
    document.getElementById('pipe2').textContent = '⚙️ 처리중';
    document.getElementById('pipe2').style.color = 'var(--amber)';

    const res = await fetch(API_BASE + '/api/kidsnote/generate', {
      method: 'POST',
      body: formData,
    });

    document.getElementById('pipe2').textContent = '✅ 완료';
    document.getElementById('pipe2').style.color = 'var(--teal)';
    document.getElementById('pipe3').textContent = '⚙️ 처리중';
    document.getElementById('pipe3').style.color = 'var(--amber)';

    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || '생성 실패');

    document.getElementById('pipe3').textContent = '✅ 완료';
    document.getElementById('pipe3').style.color = 'var(--teal)';

    output.style.color = 'var(--g9)';
    output.style.fontStyle = 'normal';

    // 타이핑 효과로 표시
    typeText('noteOutputText', data.note, 20, () => {
      document.getElementById('noteCharCount').textContent = data.note.length + ' / 300자';
    });

    // 오늘 날짜 표시
    const today = new Date().toLocaleDateString('ko-KR', {year:'numeric', month:'long', day:'numeric'});
    const dateEl = document.querySelector('.note-output [style*="border-bottom"]');
    if (dateEl) dateEl.textContent = today + ' · 오늘의 활동 알림';

  } catch (e) {
    output.textContent = '생성 실패: ' + e.message;
    output.style.color = 'var(--coral)';
    document.getElementById('pipe1').textContent = '대기중';
    document.getElementById('pipe2').textContent = '대기중';
    document.getElementById('pipe3').textContent = '대기중';
    showToast('알림장 생성 실패: ' + e.message, 'error');
  } finally {
    btn.classList.remove('loading');
    spinner.classList.remove('show');
    text.textContent = '✨ 알림장 생성하기';
  }
}

function copyNote() {
  const text = document.getElementById('noteOutputText').textContent;
  if (!text || text === '왼쪽에서 사진을 업로드하고 알림장을 생성해 보세요.') {
    showToast('먼저 알림장을 생성해주세요!', 'error');
    return;
  }
  navigator.clipboard.writeText(text).then(() => {
    showToast('알림장이 복사되었습니다!', 'success');
  });
}'''

if old_generate in html:
    html = html.replace(old_generate, new_generate)
    print("✅ PATCH 3: generateNote 실제 API 연동으로 교체")
else:
    print("⚠️  PATCH 3: generateNote 패턴 못 찾음")


# ============================================================
# 저장
# ============================================================
HTML_PATH.write_text(html, encoding="utf-8")
print(f"✅ HTML 패치 완료!")


# ============================================================
# main.py에 알림장 API 추가
# ============================================================
if not MAIN_PATH.exists():
    print("⚠️  main.py를 찾을 수 없습니다. API 추가 생략.")
else:
    main_code = MAIN_PATH.read_text(encoding="utf-8")

    new_api = '''

# ============================================================
# 학부모 알림장 API
# ============================================================

@app.post("/api/kidsnote/generate")
async def api_kidsnote_generate(
    activity_text: str = Form(...),
    tone: str = Form("🤗 다정하게"),
    image: Optional[UploadFile] = File(None),
):
    """
    학부모 알림장 자동 생성

    입력: 활동 내용 텍스트 + 톤 선택 + 활동 사진(선택)
    출력: 학부모용 알림장 200~300자
    """
    from services.keyword_extractor import get_gemini_client
    import google.genai.types as genai_types

    # 톤 매핑
    tone_map = {
        "🤗 다정하게": "따뜻하고 다정한 말투로, 부모가 읽으면 미소 짓게 되는",
        "📚 전문적으로": "교육적 전문성이 느껴지는 신뢰감 있는 말투로",
        "😊 밝고 활기차게": "밝고 생동감 넘치는 말투로, 이모지를 적절히 활용하여",
        "🌿 자연스럽게": "편안하고 자연스러운 일상적인 말투로",
    }
    tone_desc = tone_map.get(tone, tone_map["🤗 다정하게"])

    prompt = f"""당신은 유치원 담임 교사입니다. 오늘 하루 있었던 활동 내용을 바탕으로 학부모에게 보낼 알림장을 작성해주세요.

활동 내용: {activity_text}
말투: {tone_desc} 말투

다음 조건을 반드시 지켜주세요:
- 200~300자 이내
- 학부모 입장에서 아이의 하루를 생생하게 느낄 수 있도록
- 내일에 대한 기대감이나 따뜻한 마무리 문장 포함
- 서두에 "안녕하세요" 같은 인사말 생략, 바로 활동 내용부터 시작
- 오직 알림장 본문만 출력 (제목, 설명 없이)"""

    image_path = None
    tmp_file = None

    try:
        # 이미지가 있으면 멀티모달로 분석
        if image is not None:
            suffix = Path(image.filename or "img.jpg").suffix
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            content = await image.read()
            tmp_file.write(content)
            tmp_file.close()
            image_path = tmp_file.name

            # 이미지 분석 추가 프롬프트
            prompt = f"""당신은 유치원 담임 교사입니다. 첨부된 아이 활동 사진과 활동 내용을 바탕으로 학부모에게 보낼 알림장을 작성해주세요.

활동 내용: {activity_text}
말투: {tone_desc} 말투

사진 속 아이의 모습과 활동을 자연스럽게 녹여서 작성해주세요.

다음 조건을 반드시 지켜주세요:
- 200~300자 이내
- 학부모 입장에서 아이의 하루를 생생하게 느낄 수 있도록
- 내일에 대한 기대감이나 따뜻한 마무리 문장 포함
- 서두 인사말 생략, 바로 활동 내용부터 시작
- 오직 알림장 본문만 출력"""

        client = get_gemini_client()

        if image_path:
            import PIL.Image
            img = PIL.Image.open(image_path)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, img],
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=1024,
                    temperature=0.8,
                )
            )
        else:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=1024,
                    temperature=0.8,
                )
            )

        note_text = response.text.strip()

        return {"note": note_text, "char_count": len(note_text)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림장 생성 실패: {str(e)}")
    finally:
        if tmp_file:
            Path(tmp_file.name).unlink(missing_ok=True)

'''

    # health check API 앞에 삽입
    target = '\n@app.get("/api/health")'
    if target in main_code:
        main_code = main_code.replace(target, new_api + target)
        MAIN_PATH.write_text(main_code, encoding="utf-8")
        print("✅ main.py: 알림장 API 추가 완료!")
    else:
        print("⚠️  main.py: 삽입 위치를 찾을 수 없습니다.")

print("\n🎉 Phase 2 패치 완료!")
print("\n테스트 방법:")
print("  1. AI 알림장 페이지로 이동")
print("  2. 활동 내용 입력: '오늘은 나뭇잎과 물감으로 협동 놀이를 했습니다'")
print("  3. 톤 선택 후 '알림장 생성하기' 클릭")
print("  4. 학부모용 알림장 자동 생성 확인")
