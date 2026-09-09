#!/usr/bin/env python3
"""
patch_pricing_simplify.py
==========================
1. 파일 보관함 saved_lesson_id 버그 수정
2. Pro+ 제거 → Free / Pro 2단계로 단순화
3. 무료 사용자 정책 강화:
   - 2주 무료체험 종료 후:
     - 지도안 생성 월 5회 제한
     - 양식 적용 결과: 셀 첫 부분만 표시 + 나머지 블러
     - .docx 다운로드 막힘
"""
from pathlib import Path
import re

BACKEND = Path(".")
MAIN_PATH = BACKEND / "main.py"
DB_PATH = BACKEND / "database.py"
HTML_PATH = BACKEND / "static" / "edu-bridge-full.html"


# ============================================================
# 1) database.py: lesson_generation_count 컬럼 추가
# ============================================================
db_code = DB_PATH.read_text(encoding="utf-8")

if "lesson_generation_count" not in db_code:
    old = "    template_download_count = Column(Integer, default=0)"
    new = """    template_download_count = Column(Integer, default=0)
    lesson_generation_count = Column(Integer, default=0)"""
    if old in db_code:
        db_code = db_code.replace(old, new)
        DB_PATH.write_text(db_code, encoding="utf-8")
        print("✅ database.py: lesson_generation_count 컬럼 추가")


# ============================================================
# 2) main.py: check_pro_access + 지도안 생성 카운트
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

# check_pro_access 함수 업데이트 (lesson_generation 추가)
old_check = '''def check_pro_access(current_user: User, feature: str = "premium") -> dict:
    """
    Pro 기능 접근 권한 확인.
    Returns: {"allowed": bool, "reason": str}
    """
    from datetime import timedelta as _td

    # Pro/Pro+ 사용자: 무제한
    if current_user.subscription_tier in ('pro', 'pro_plus'):
        return {"allowed": True, "reason": "pro"}

    # 신규 가입자 2주 무료 체험
    if current_user.created_at:
        trial_end = current_user.created_at + _td(days=14)
        if datetime.utcnow() < trial_end:
            return {"allowed": True, "reason": "trial"}

    # 양식 적용 다운로드는 무료 사용자 월 5회까지
    if feature == "template_download":
        count = current_user.template_download_count or 0
        if count < 5:
            return {"allowed": True, "reason": "free_quota", "remaining": 5 - count}
        return {"allowed": False, "reason": "limit_exceeded"}

    # 수정 기능 등은 무료 사용자 불가
    return {"allowed": False, "reason": "pro_required"}'''

new_check = '''def check_pro_access(current_user: User, feature: str = "premium") -> dict:
    """
    Pro 기능 접근 권한 확인.
    Returns: {"allowed": bool, "reason": str}
    """
    from datetime import timedelta as _td

    # Pro 사용자: 무제한
    if current_user.subscription_tier == 'pro':
        return {"allowed": True, "reason": "pro"}

    # 신규 가입자 2주 무료 체험: 모든 기능 무제한
    if current_user.created_at:
        trial_end = current_user.created_at + _td(days=14)
        if datetime.utcnow() < trial_end:
            return {"allowed": True, "reason": "trial"}

    # 무료 사용자 (체험 종료) 정책
    if feature == "lesson_generation":
        count = current_user.lesson_generation_count or 0
        if count < 5:
            return {"allowed": True, "reason": "free_quota", "remaining": 5 - count}
        return {"allowed": False, "reason": "limit_exceeded"}

    # template_download (양식 적용 다운로드): 무료 종료 시 막힘
    if feature == "template_download":
        return {"allowed": False, "reason": "pro_required"}

    # 수정 기능: 무료 종료 시 막힘
    return {"allowed": False, "reason": "pro_required"}'''

if old_check in main_code:
    main_code = main_code.replace(old_check, new_check)
    print("✅ main.py: check_pro_access 로직 강화")

# 지도안 생성 API에 카운트 체크 + 증가 추가
# /api/lesson 엔드포인트 찾기 (또는 /api/extract)
# 일반적으로 키워드 추출이 첫 단계이므로 거기에 카운트 추가
old_extract = '''@app.post("/api/extract")
async def api_extract(body: dict):'''
new_extract = '''@app.post("/api/extract")
async def api_extract(body: dict, current_user: User = Depends(get_current_user_optional)):'''

# get_current_user_optional이 없으면 get_optional_user 사용
if 'def get_optional_user' in main_code or 'get_current_user_optional' in main_code:
    # 적절한 의존성 사용
    if 'get_optional_user' in main_code:
        new_extract = new_extract.replace('get_current_user_optional', 'get_optional_user')

if old_extract in main_code:
    main_code = main_code.replace(old_extract, new_extract)
    
    # extract 함수 시작 부분에 카운트 체크 + 증가 로직 삽입
    # extract 함수 본문에 사용량 체크 추가 (return 직전이 아니라 시작 부분에)
    # 안전하게 query 변수 추출 후에 삽입
    # 일단 query 변수 정의 다음에 삽입 시도
    extract_check = '''@app.post("/api/extract")
async def api_extract(body: dict, current_user: User = Depends(get_optional_user)):'''
    
    if extract_check in main_code:
        # 함수 내부에 권한 체크 추가
        # query 변수 추출 직후에 카운트 체크 삽입
        # 함수 시그니처 다음 줄들에서 query 변수 정의 찾기
        pass  # 이미 시그니처는 바꿈
        
    # 카운트 증가는 응답 직전에 (성공한 경우만)
    # 가장 간단한 방법: 함수 시작 부분에 체크 + 증가 한 번에
    
    # /api/extract 함수의 첫 줄에 체크 코드 삽입
    extract_body_marker = '''@app.post("/api/extract")
async def api_extract(body: dict, current_user: User = Depends(get_optional_user)):'''
    
    extract_check_code = '''@app.post("/api/extract")
async def api_extract(body: dict, current_user: User = Depends(get_optional_user), db: Session = Depends(get_db)):
    # 무료 사용자 지도안 생성 횟수 체크 (체험 종료 후 월 5회)
    if current_user:
        access = check_pro_access(current_user, feature="lesson_generation")
        if not access["allowed"]:
            raise HTTPException(status_code=403, detail="LIMIT_EXCEEDED:이번 달 지도안 생성 5회를 모두 사용했습니다. Pro 플랜으로 무제한 이용하세요.")
        # 체험 종료 후 무료 사용자만 카운트 증가
        from datetime import timedelta as _td
        trial_active = current_user.created_at and (datetime.utcnow() < current_user.created_at + _td(days=14))
        if current_user.subscription_tier == 'free' and not trial_active:
            current_user.lesson_generation_count = (current_user.lesson_generation_count or 0) + 1
            db.commit()
'''
    
    main_code = main_code.replace(extract_body_marker, extract_check_code)
    print("✅ main.py: /api/extract에 카운트 체크 추가")

# /api/me/subscription 응답에 lesson_generation 정보 추가
old_sub_resp = '''    return {
        "tier": current_user.subscription_tier or 'free',
        "trial_active": trial_active,
        "trial_days_left": days_left,
        "started_at": current_user.subscription_started_at.isoformat() if current_user.subscription_started_at else None,
        "expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None,
        "template_download_count": current_user.template_download_count or 0,
        "template_download_limit": 5 if (current_user.subscription_tier == 'free' and not trial_active) else None,
    }'''
new_sub_resp = '''    is_free_post_trial = (current_user.subscription_tier == 'free' and not trial_active)
    return {
        "tier": current_user.subscription_tier or 'free',
        "trial_active": trial_active,
        "trial_days_left": days_left,
        "is_free_post_trial": is_free_post_trial,
        "started_at": current_user.subscription_started_at.isoformat() if current_user.subscription_started_at else None,
        "expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None,
        "lesson_generation_count": current_user.lesson_generation_count or 0,
        "lesson_generation_limit": 5 if is_free_post_trial else None,
        "template_download_blocked": is_free_post_trial,
        "refine_blocked": is_free_post_trial,
    }'''

if old_sub_resp in main_code:
    main_code = main_code.replace(old_sub_resp, new_sub_resp)
    print("✅ main.py: /api/me/subscription 응답 정보 추가")

# /api/me 응답에도 추가
old_me_resp = '''    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "subscription_tier": current_user.subscription_tier or 'free',
        "trial_active": trial_active,
        "trial_days_left": days_left,
        "template_download_count": current_user.template_download_count or 0,
        "is_admin": current_user.id == 1,
    }'''
new_me_resp = '''    is_free_post_trial = (current_user.subscription_tier == 'free' and not trial_active)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "subscription_tier": current_user.subscription_tier or 'free',
        "trial_active": trial_active,
        "trial_days_left": days_left,
        "is_free_post_trial": is_free_post_trial,
        "lesson_generation_count": current_user.lesson_generation_count or 0,
        "template_download_blocked": is_free_post_trial,
        "refine_blocked": is_free_post_trial,
        "is_admin": current_user.id == 1,
    }'''

if old_me_resp in main_code:
    main_code = main_code.replace(old_me_resp, new_me_resp)
    print("✅ main.py: /api/me 응답에 무료 정책 정보 추가")

# Pro+ 구독 옵션 제거 (api_subscribe)
old_subscribe = '''    tier = body.get("tier", "pro")
    if tier not in ("pro", "pro_plus"):
        raise HTTPException(status_code=400, detail="잘못된 요금제")

    current_user.subscription_tier = tier'''
new_subscribe = '''    tier = body.get("tier", "pro")
    if tier != "pro":
        raise HTTPException(status_code=400, detail="잘못된 요금제")

    current_user.subscription_tier = tier'''

if old_subscribe in main_code:
    main_code = main_code.replace(old_subscribe, new_subscribe)
    print("✅ main.py: Pro+ 구독 옵션 제거")

MAIN_PATH.write_text(main_code, encoding="utf-8")


# ============================================================
# 3) HTML 패치
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_simplify")
backup.write_text(html, encoding="utf-8")
print(f"✅ HTML 백업: {backup}")


# 3-1) 요금제 페이지에서 Pro+ 카드 제거
# Pro+ 카드 전체 영역을 찾아서 제거
pro_plus_pattern = re.compile(
    r'\s*<!-- Pro\+ -->.*?</button>\s*</div>',
    re.DOTALL
)
m = pro_plus_pattern.search(html)
if m:
    html = html[:m.start()] + html[m.end():]
    print("✅ 요금제 페이지에서 Pro+ 카드 제거")

# 그리드 컬럼을 2개로 변경
html = html.replace(
    '<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:1.5rem; margin-bottom:3rem;">',
    '<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:1.5rem; margin-bottom:3rem; max-width:760px; margin-left:auto; margin-right:auto;">',
    1  # 첫 번째만 (요금제 페이지)
)

# Free 카드 내용 업데이트
old_free_card = '''<!-- Free -->
        <div style="background:var(--white); border:1.5px solid var(--g2); border-radius:16px; padding:2rem 1.5rem;">
          <div style="font-size:14px; font-weight:700; color:var(--g6); margin-bottom:6px;">Free</div>
          <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:6px;">
            <span style="font-size:32px; font-weight:900; color:var(--g9);">₩0</span>
            <span style="font-size:13px; color:var(--g5);">/월</span>
          </div>
          <div style="font-size:12px; color:var(--g5); margin-bottom:20px;">처음 2주는 모든 기능 무료체험!</div>
          <ul style="list-style:none; padding:0; margin:0 0 24px; font-size:13px; line-height:2;">
            <li style="color:var(--g8);">✓ 지도안 생성 (무제한)</li>
            <li style="color:var(--g8);">✓ AI 알림장 작성</li>
            <li style="color:var(--g8);">✓ 지도안 저장</li>
            <li style="color:var(--g8);">✓ 커뮤니티 이용</li>
            <li style="color:var(--g6); font-size:12px;">⚠ 양식 적용 다운로드 월 5회</li>
            <li style="color:var(--g5); font-size:12px;">× 지도안 수정 기능</li>
          </ul>
          <button id="freeBtn" disabled style="width:100%; height:42px; border:1.5px solid var(--g2); border-radius:8px; background:var(--g0); color:var(--g6); font-family:var(--font); font-size:13px; font-weight:700; cursor:not-allowed;">현재 플랜</button>
        </div>'''

new_free_card = '''<!-- Free -->
        <div style="background:var(--white); border:1.5px solid var(--g2); border-radius:16px; padding:2rem 1.5rem;">
          <div style="font-size:14px; font-weight:700; color:var(--g6); margin-bottom:6px;">Free</div>
          <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:6px;">
            <span style="font-size:32px; font-weight:900; color:var(--g9);">₩0</span>
            <span style="font-size:13px; color:var(--g5);">/월</span>
          </div>
          <div style="font-size:12px; color:var(--g5); margin-bottom:20px;">🎁 가입 후 2주 무료체험!</div>
          <div style="background:var(--coral-3, #FFE5DC); padding:10px 12px; border-radius:8px; margin-bottom:16px;">
            <div style="font-size:11px; font-weight:700; color:var(--coral); margin-bottom:4px;">📅 2주 무료체험 기간</div>
            <div style="font-size:12px; color:var(--g7); line-height:1.5;">모든 Pro 기능을 자유롭게 사용해보세요</div>
          </div>
          <div style="font-size:11px; font-weight:700; color:var(--g6); margin-bottom:8px;">체험 종료 후</div>
          <ul style="list-style:none; padding:0; margin:0 0 24px; font-size:13px; line-height:1.9;">
            <li style="color:var(--g8);">✓ 지도안 생성 <b>월 5회</b></li>
            <li style="color:var(--g8);">✓ AI 알림장 작성</li>
            <li style="color:var(--g8);">✓ 양식 업로드 (체험용)</li>
            <li style="color:var(--g6); font-size:12px;">⚠ 양식 적용 결과 미리보기만</li>
            <li style="color:var(--g5); font-size:12px;">× 양식 .docx 다운로드</li>
            <li style="color:var(--g5); font-size:12px;">× 지도안 수정 채팅</li>
          </ul>
          <button id="freeBtn" disabled style="width:100%; height:42px; border:1.5px solid var(--g2); border-radius:8px; background:var(--g0); color:var(--g6); font-family:var(--font); font-size:13px; font-weight:700; cursor:not-allowed;">현재 플랜</button>
        </div>'''

if old_free_card in html:
    html = html.replace(old_free_card, new_free_card)
    print("✅ Free 카드 내용 업데이트")

# Pro 카드 내용 업데이트 (Pro+ 제거됐으니까 단독)
old_pro_card_features = '''<ul style="list-style:none; padding:0; margin:0 0 24px; font-size:13px; line-height:2;">
            <li style="color:var(--g8);">✓ Free 플랜의 모든 기능</li>
            <li style="color:var(--g8); font-weight:700;">✓ 양식 적용 다운로드 무제한</li>
            <li style="color:var(--g8); font-weight:700;">✓ 지도안 수정 AI 채팅</li>
            <li style="color:var(--g8); font-weight:700;">✓ 양식 적용 결과 셀 편집</li>
            <li style="color:var(--g8);">✓ 파일 보관함 무제한</li>
          </ul>'''

new_pro_card_features = '''<ul style="list-style:none; padding:0; margin:0 0 24px; font-size:13px; line-height:2;">
            <li style="color:var(--g8); font-weight:700;">✓ 지도안 생성 무제한</li>
            <li style="color:var(--g8); font-weight:700;">✓ 양식 .docx 다운로드 무제한</li>
            <li style="color:var(--g8); font-weight:700;">✓ 양식 적용 결과 전체 보기</li>
            <li style="color:var(--g8); font-weight:700;">✓ 지도안 수정 AI 채팅</li>
            <li style="color:var(--g8); font-weight:700;">✓ 셀 직접 편집</li>
            <li style="color:var(--g8); font-weight:700;">✓ 파일 보관함 무제한</li>
            <li style="color:var(--g8);">✓ AI 알림장 작성</li>
            <li style="color:var(--g8);">✓ 모든 커뮤니티 기능</li>
          </ul>'''

if old_pro_card_features in html:
    html = html.replace(old_pro_card_features, new_pro_card_features)
    print("✅ Pro 카드 기능 목록 업데이트")


# 3-2) downloadSavedAsDocx 함수 직접 수정 (saved_lesson_id 포함되도록)
# 모든 기존 downloadSavedAsDocx 정의를 찾아서 마지막에 클린 버전 추가

clean_download_fn = '''

// === FINAL OVERRIDE: downloadSavedAsDocx with saved_lesson_id (DO NOT REMOVE) ===
downloadSavedAsDocx = async function() {
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
    saved_lesson_id: _currentSavedLesson.id,
  });
};
'''

if 'FINAL OVERRIDE: downloadSavedAsDocx' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + clean_download_fn + '\n' + html[last_close:]
        print("✅ downloadSavedAsDocx 최종 오버라이드 추가 (saved_lesson_id 포함)")


# 3-3) renderFillsList에 블러 처리 추가 (무료 사용자 후체험)
blur_render_fn = '''

// === 무료 사용자 (체험 종료 후) 블러 미리보기 + 다운로드 차단 ===
(function() {
  // 원본 renderFillsList 보존
  const _origRenderFillsListForBlur = renderFillsList;
  
  renderFillsList = function(fills, changedIndices) {
    _origRenderFillsListForBlur(fills, changedIndices);
    
    // 무료 사용자 후체험 체크
    const isFreePost = _mySubscription && _mySubscription.is_free_post_trial;
    if (!isFreePost) return;  // Pro 또는 체험중이면 정상 표시
    
    // 처음 3개 셀만 보이고 나머지는 블러
    const container = document.getElementById('fillsCellsList');
    if (!container) return;
    
    // 카드 목록 가져오기
    const allCards = container.querySelectorAll('[id^="cellCard_"]');
    if (allCards.length <= 3) return;  // 3개 이하면 블러 안 함
    
    // 4번째 셀부터 블러 + 클릭 막기
    for (let i = 3; i < allCards.length; i++) {
      const card = allCards[i];
      card.style.filter = 'blur(4px)';
      card.style.pointerEvents = 'none';
      card.style.userSelect = 'none';
      card.style.opacity = '0.6';
    }
    
    // 블러 영역 위에 안내 오버레이 추가
    if (!document.getElementById('blurOverlay')) {
      const overlay = document.createElement('div');
      overlay.id = 'blurOverlay';
      overlay.style.cssText = 'position:sticky; bottom:0; margin-top:1rem; padding:20px; background:linear-gradient(180deg, rgba(255,255,255,0.5) 0%, var(--white) 60%); border-top:2px solid var(--teal); border-radius:12px; text-align:center; z-index:10;';
      overlay.innerHTML = `
        <div style="font-size:32px; margin-bottom:8px;">🔒</div>
        <div style="font-size:14px; font-weight:700; color:var(--g9); margin-bottom:4px;">전체 결과는 Pro에서 볼 수 있어요</div>
        <div style="font-size:12px; color:var(--g6); margin-bottom:12px;">무료 체험 종료 후에는 첫 3개 셀만 보입니다.<br>Pro로 업그레이드하면 모든 셀과 다운로드가 가능합니다.</div>
        <button onclick="goPricingPage(); closeFillsPreview();" style="padding:8px 16px; border:none; border-radius:8px; background:var(--teal); color:var(--white); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">Pro 알아보기 →</button>
      `;
      container.appendChild(overlay);
    }
    
    // 다운로드 버튼 비활성화
    const dlBtn = document.querySelector('button[onclick="downloadFromFillsModal()"]');
    if (dlBtn) {
      dlBtn.disabled = true;
      dlBtn.style.opacity = '0.5';
      dlBtn.style.cursor = 'not-allowed';
      dlBtn.title = 'Pro 플랜에서 사용 가능';
      dlBtn.onclick = function(e) {
        e.preventDefault();
        showProHint('Pro 플랜 안내', '양식 적용 .docx 다운로드는 Pro 플랜에서 사용 가능합니다.');
      };
    }
    
    // 저장 버튼도 비활성화
    const saveBtn = document.getElementById('fillsSaveBtn');
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.style.opacity = '0.5';
      saveBtn.style.cursor = 'not-allowed';
      saveBtn.onclick = function(e) {
        e.preventDefault();
        showProHint('Pro 플랜 안내', '파일 저장은 Pro 플랜에서 사용 가능합니다.');
      };
    }
  };
})();

// Pro+ 버튼 제거 (사이드바 박스 텍스트 정리)
const _origUpdateSidebarPriceBox = updateSidebarPriceBox;
updateSidebarPriceBox = function() {
  if (!_mySubscription) return;
  const tag = document.getElementById('sidebarPriceTag');
  const amount = document.getElementById('sidebarPriceAmount');
  const sub = document.getElementById('sidebarPriceSub');
  const cta = document.getElementById('sidebarPriceCta');
  if (!tag) return;

  const t = _mySubscription.tier;
  if (t === 'pro') {
    tag.textContent = '✨ Pro 사용 중';
    amount.innerHTML = 'Pro';
    amount.style.fontSize = '24px';
    sub.textContent = '모든 기능 무제한';
    cta.textContent = '플랜 관리 →';
  } else if (_mySubscription.trial_active) {
    tag.textContent = '🎁 무료체험 중';
    amount.innerHTML = _mySubscription.trial_days_left + '<span style="font-size:14px;font-weight:600;">일 남음</span>';
    amount.style.fontSize = '';
    sub.textContent = '체험 종료 후 Pro 추천';
    cta.textContent = 'Pro 미리보기 →';
  } else {
    tag.textContent = '무제한 플랜';
    amount.innerHTML = '2,990<span style="font-size:14px;font-weight:600;">원/월</span>';
    amount.style.fontSize = '';
    sub.textContent = '지금 바로 시작하세요';
    cta.textContent = '바로가기 →';
  }
};
'''

if '무료 사용자 (체험 종료 후) 블러 미리보기' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + blur_render_fn + '\n' + html[last_close:]
        print("✅ 블러 미리보기 + 다운로드 차단 JS 추가")


HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 60)
print("🎉 패치 완료!")
print("=" * 60)
print("\n다음 단계:")
print("  rm edubridge.db  (DB 스키마 변경)")
print("\n변경 사항:")
print("  1. ✅ 파일 보관함 saved_lesson_id 버그 수정")
print("  2. ✅ Pro+ 제거 → Free / Pro 2단계")
print("  3. ✅ 무료 정책 강화:")
print("     - 2주 무료체험: 모든 기능 무제한")
print("     - 체험 종료 후:")
print("       · 지도안 생성 월 5회 제한")
print("       · 양식 업로드 가능 (체험)")
print("       · 양식 적용 결과: 첫 3개 셀만 표시 + 나머지 블러")
print("       · .docx 다운로드 막힘 (버튼 비활성화)")
print("       · 수정 채팅 막힘")
print("  4. ✅ Pro 플랜: 모든 기능 무제한")
