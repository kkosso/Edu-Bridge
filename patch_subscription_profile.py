#!/usr/bin/env python3
"""
patch_subscription_profile.py
==============================
1. .hwp 양식 업로드 제거 (.docx만 허용)
2. 요금제 시스템 (Free 2주 체험 / Pro 2,990원 / Pro+ 4,990원)
3. 요금제 안내 페이지 (사이드바 광고 박스 '바로가기'로 진입)
4. 프로필 메뉴 (사이드바 좌하단 프로필 클릭 → 마이페이지 모달)
"""
from pathlib import Path
import re

BACKEND = Path(".")
MAIN_PATH = BACKEND / "main.py"
DB_PATH = BACKEND / "database.py"
HTML_PATH = BACKEND / "static" / "edu-bridge-full.html"


# ============================================================
# 1) database.py: User에 subscription_tier 컬럼 추가
# ============================================================
db_code = DB_PATH.read_text(encoding="utf-8")

if "subscription_tier" not in db_code:
    # User 클래스에 새 필드 추가 (created_at 다음에)
    old_user_end = "    created_at = Column(DateTime, default=datetime.utcnow)\n\n\nclass SavedLesson"
    new_user_end = """    created_at = Column(DateTime, default=datetime.utcnow)

    # 구독 관련
    subscription_tier = Column(String(20), default='free')  # 'free' / 'pro' / 'pro_plus'
    subscription_started_at = Column(DateTime, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    template_download_count = Column(Integer, default=0)  # 양식 적용 다운로드 횟수 (월별 리셋용)
    last_download_reset_at = Column(DateTime, default=datetime.utcnow)


class SavedLesson"""

    if old_user_end in db_code:
        db_code = db_code.replace(old_user_end, new_user_end)
        DB_PATH.write_text(db_code, encoding="utf-8")
        print("✅ database.py: User에 구독 컬럼 추가")
    else:
        print("⚠️  User 클래스 패턴 못 찾음")


# ============================================================
# 2) main.py: 구독 API + /api/me 응답 업데이트
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

# /api/me 응답에 subscription 정보 포함
old_me = '''    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
    }'''
new_me = '''    # 신규 가입자의 2주 무료체험 기간 계산
    from datetime import timedelta as _td
    trial_active = False
    days_left = 0
    if current_user.subscription_tier == 'free' and current_user.created_at:
        trial_end = current_user.created_at + _td(days=14)
        if datetime.utcnow() < trial_end:
            trial_active = True
            days_left = (trial_end - datetime.utcnow()).days + 1

    return {
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

if old_me in main_code:
    main_code = main_code.replace(old_me, new_me)
    print("✅ main.py: /api/me 응답에 구독 정보 추가")

# 구독 관련 API 추가
new_apis = '''

# ============================================================
# 구독 및 프로필 API
# ============================================================

@app.get("/api/me/subscription")
def api_my_subscription(current_user: User = Depends(get_current_user)):
    """현재 사용자의 구독 상태 + 무료 체험 정보"""
    from datetime import timedelta as _td
    trial_active = False
    days_left = 0
    if current_user.subscription_tier == 'free' and current_user.created_at:
        trial_end = current_user.created_at + _td(days=14)
        if datetime.utcnow() < trial_end:
            trial_active = True
            days_left = (trial_end - datetime.utcnow()).days + 1

    return {
        "tier": current_user.subscription_tier or 'free',
        "trial_active": trial_active,
        "trial_days_left": days_left,
        "started_at": current_user.subscription_started_at.isoformat() if current_user.subscription_started_at else None,
        "expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None,
        "template_download_count": current_user.template_download_count or 0,
        "template_download_limit": 5 if (current_user.subscription_tier == 'free' and not trial_active) else None,
    }


@app.post("/api/me/subscribe")
def api_subscribe(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """구독 시작 (Mock - 즉시 활성화)"""
    from datetime import timedelta as _td
    tier = body.get("tier", "pro")
    if tier not in ("pro", "pro_plus"):
        raise HTTPException(status_code=400, detail="잘못된 요금제")

    current_user.subscription_tier = tier
    current_user.subscription_started_at = datetime.utcnow()
    current_user.subscription_expires_at = datetime.utcnow() + _td(days=30)
    db.commit()
    return {
        "tier": tier,
        "message": f"{('Pro' if tier == 'pro' else 'Pro+')} 구독이 활성화되었습니다!"
    }


@app.post("/api/me/cancel-subscription")
def api_cancel(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """구독 해지"""
    current_user.subscription_tier = 'free'
    current_user.subscription_started_at = None
    current_user.subscription_expires_at = None
    db.commit()
    return {"tier": "free", "message": "구독이 해지되었습니다."}


@app.put("/api/me/profile")
def api_update_profile(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """프로필 수정 (이름)"""
    full_name = (body.get("full_name") or "").strip()
    if full_name:
        current_user.full_name = full_name[:50]
        db.commit()
    return {"message": "프로필이 업데이트되었습니다.", "full_name": current_user.full_name}


def check_pro_access(current_user: User, feature: str = "premium") -> dict:
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
    return {"allowed": False, "reason": "pro_required"}

'''

if "/api/me/subscription" not in main_code:
    main_code = main_code.replace(
        '\n@app.get("/api/health")',
        new_apis + '\n@app.get("/api/health")'
    )
    print("✅ main.py: 구독/프로필 API 추가")

# export-from-fills와 refine-fills, refine API에 권한 체크 추가
old_refine = '''@app.post("/api/lesson/refine")
async def api_refine_lesson(body: dict):
    """'''
new_refine = '''@app.post("/api/lesson/refine")
async def api_refine_lesson(body: dict, current_user: User = Depends(get_current_user)):
    """'''
if old_refine in main_code:
    main_code = main_code.replace(old_refine, new_refine)
    # refine 함수 시작 부분에 권한 체크 추가
    refine_check = '''    """
    지도안 수정 요청 (대화형)'''
    new_refine_check = '''    """
    지도안 수정 요청 (대화형) - Pro 전용'''
    main_code = main_code.replace(refine_check, new_refine_check, 1)

    # 함수 내부 첫 부분에 권한 체크 삽입
    old_check_point = '''    markdown = body.get("lesson_markdown", "")
    request_text = body.get("refinement_request", "")
    history = body.get("conversation_history", []) or []

    if not markdown or not request_text:
        raise HTTPException(status_code=400, detail="지도안과 수정 요청이 모두 필요합니다.")'''
    new_check_point = '''    markdown = body.get("lesson_markdown", "")
    request_text = body.get("refinement_request", "")
    history = body.get("conversation_history", []) or []

    if not markdown or not request_text:
        raise HTTPException(status_code=400, detail="지도안과 수정 요청이 모두 필요합니다.")

    # Pro 전용 기능
    access = check_pro_access(current_user, feature="refine")
    if not access["allowed"]:
        raise HTTPException(status_code=403, detail="PRO_REQUIRED:수정 기능은 Pro 플랜에서 사용 가능합니다.")'''
    main_code = main_code.replace(old_check_point, new_check_point)

# refine-fills API도 동일하게
old_rf = '''@app.post("/api/lesson/refine-fills")
async def api_refine_fills(body: dict, current_user: User = Depends(get_current_user)):
    """양식 채워진 결과를 채팅으로 수정"""'''
new_rf = '''@app.post("/api/lesson/refine-fills")
async def api_refine_fills(body: dict, current_user: User = Depends(get_current_user)):
    """양식 채워진 결과를 채팅으로 수정 - Pro 전용"""
    access = check_pro_access(current_user, feature="refine")
    if not access["allowed"]:
        raise HTTPException(status_code=403, detail="PRO_REQUIRED:수정 기능은 Pro 플랜에서 사용 가능합니다.")
'''
if old_rf in main_code:
    main_code = main_code.replace(old_rf, new_rf)

# export-from-fills에 다운로드 횟수 체크 + 증가
old_export_from = '''@app.post("/api/lesson/export-from-fills")
async def api_export_from_fills(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    이미 계산된 fills로 .docx 생성 (수정 후 다운로드용)

    body: {title, template_id, fills}
    """'''
new_export_from = '''@app.post("/api/lesson/export-from-fills")
async def api_export_from_fills(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    이미 계산된 fills로 .docx 생성 (수정 후 다운로드용) - 무료 5회 제한
    """
    # 다운로드 횟수 체크
    access = check_pro_access(current_user, feature="template_download")
    if not access["allowed"]:
        raise HTTPException(status_code=403, detail="LIMIT_EXCEEDED:이번 달 양식 적용 다운로드 5회를 모두 사용했습니다. Pro 플랜으로 무제한 이용하세요.")
    
    # 무료 사용자의 경우 카운트 증가 (Pro/체험중은 카운트 안 함)
    from datetime import timedelta as _td
    trial_active = current_user.created_at and (datetime.utcnow() < current_user.created_at + _td(days=14))
    if current_user.subscription_tier == 'free' and not trial_active:
        current_user.template_download_count = (current_user.template_download_count or 0) + 1
        db.commit()
'''
if old_export_from in main_code:
    main_code = main_code.replace(old_export_from, new_export_from)

MAIN_PATH.write_text(main_code, encoding="utf-8")
print("✅ main.py: 기존 API에 권한 체크 추가")


# ============================================================
# 3) HTML 패치
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_subscription")
backup.write_text(html, encoding="utf-8")
print(f"✅ HTML 백업: {backup}")


# 3-1) HWP 제거 - 내 양식 페이지 안내문 수정
old_hwp_notice = '''<div class="page-sub">우리 유치원 양식(.docx 또는 .hwp)을 업로드하면 그 양식에 맞춰 지도안을 생성합니다</div>
      <div style="margin-bottom:1rem;padding:12px 14px;background:var(--amber-3);border-left:3px solid var(--amber);border-radius:6px;font-size:12px;color:var(--g7);line-height:1.6;">
        💡 <b>.hwp 파일 안내:</b> .hwp는 텍스트만 추출되며, 출력은 .docx로만 가능합니다. 한컴오피스에서 .docx로 열어서 .hwp로 저장하세요.
      </div>'''
new_hwp_notice = '''<div class="page-sub">우리 유치원 양식(.docx)을 업로드하면 그 양식에 맞춰 지도안을 생성합니다</div>
      <div style="margin-bottom:1rem;padding:12px 14px;background:var(--teal-3);border-left:3px solid var(--teal);border-radius:6px;font-size:12px;color:var(--g7);line-height:1.6;">
        💡 <b>.docx 파일만 지원:</b> 한컴오피스(.hwp)를 사용 중이시면 한컴오피스에서 "다른 이름으로 저장" → ".docx" 형식으로 저장한 후 업로드해주세요.
      </div>'''
if old_hwp_notice in html:
    html = html.replace(old_hwp_notice, new_hwp_notice)
    print("✅ HWP 안내문구를 .docx 전용 안내로 변경")

# 파일 입력 accept 변경
html = html.replace('accept=".docx,.hwp"', 'accept=".docx"')
html = html.replace(
    '파일 (.docx 또는 .hwp)',
    '파일 (.docx만 지원)'
)
html = html.replace(
    ".docx 또는 .hwp 파일만 가능합니다.",
    ".docx 파일만 가능합니다. (.hwp는 한컴오피스에서 .docx로 변환 후 업로드)"
)
html = html.replace(
    "if (!file.name.toLowerCase().match(/\\.(docx|hwp)$/))",
    "if (!file.name.toLowerCase().endsWith('.docx'))"
)
print("✅ 파일 입력에서 .hwp 제거")


# 3-2) 사이드바 광고 박스를 다시 요금제 박스로 (with 바로가기 동작 변경)
old_ad_box_pattern = re.compile(
    r'<div class="sidebar-price">.*?</div>',
    re.DOTALL
)

new_price_box = '''<div class="sidebar-price">
    <div class="sidebar-price-tag" id="sidebarPriceTag">무제한 플랜</div>
    <div class="sidebar-price-amount" id="sidebarPriceAmount">2,990<span style="font-size:14px;font-weight:600;">원/월</span></div>
    <div class="sidebar-price-sub" id="sidebarPriceSub">지금 바로 시작하세요</div>
    <button class="sidebar-price-cta" id="sidebarPriceCta" onclick="goPricingPage()">바로가기 →</button>
  </div>'''

m = old_ad_box_pattern.search(html)
if m and 'id="sidebarPriceCta"' not in html:
    html = html[:m.start()] + new_price_box + html[m.end():]
    print("✅ 사이드바 요금제 박스 (바로가기 → 요금제 페이지)")


# 3-3) 요금제 페이지 추가 (사이드바 네비에는 없고, 바로가기 버튼으로만 진입)
pricing_page = '''
  <!-- ════ PRICING PAGE (히든, 바로가기로만 진입) ════ -->
  <div class="page" id="page-pricing">
    <div style="padding:3rem 2rem; max-width:1100px; margin:0 auto;">
      <div style="text-align:center; margin-bottom:3rem;">
        <div style="font-size:14px; font-weight:700; color:var(--teal); margin-bottom:8px;">💎 EDU-bridge Pro</div>
        <div style="font-size:32px; font-weight:900; color:var(--g9); margin-bottom:12px;">선생님을 위한 똑똑한 선택</div>
        <div style="font-size:15px; color:var(--g6); line-height:1.7;">행정 부담은 줄이고, 더 좋은 수업에 집중하세요.<br>지금 회원가입하면 <b style="color:var(--teal);">2주 무료체험</b>으로 모든 기능을 사용할 수 있어요.</div>
      </div>

      <!-- 요금제 카드 3개 -->
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:1.5rem; margin-bottom:3rem;">

        <!-- Free -->
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
        </div>

        <!-- Pro -->
        <div style="background:linear-gradient(135deg, #f0fdf9 0%, #ffffff 100%); border:2.5px solid var(--teal); border-radius:16px; padding:2rem 1.5rem; position:relative; box-shadow:0 8px 24px rgba(29,158,117,0.15);">
          <div style="position:absolute; top:-12px; left:50%; transform:translateX(-50%); background:var(--teal); color:var(--white); padding:4px 12px; border-radius:12px; font-size:11px; font-weight:700;">🔥 인기</div>
          <div style="font-size:14px; font-weight:700; color:var(--teal); margin-bottom:6px;">Pro</div>
          <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:6px;">
            <span style="font-size:32px; font-weight:900; color:var(--g9);">₩2,990</span>
            <span style="font-size:13px; color:var(--g5);">/월</span>
          </div>
          <div style="font-size:12px; color:var(--g5); margin-bottom:20px;">실무에 필요한 모든 기능</div>
          <ul style="list-style:none; padding:0; margin:0 0 24px; font-size:13px; line-height:2;">
            <li style="color:var(--g8);">✓ Free 플랜의 모든 기능</li>
            <li style="color:var(--g8); font-weight:700;">✓ 양식 적용 다운로드 무제한</li>
            <li style="color:var(--g8); font-weight:700;">✓ 지도안 수정 AI 채팅</li>
            <li style="color:var(--g8); font-weight:700;">✓ 양식 적용 결과 셀 편집</li>
            <li style="color:var(--g8);">✓ 파일 보관함 무제한</li>
          </ul>
          <button id="proSubBtn" onclick="subscribePlan('pro')" style="width:100%; height:42px; border:none; border-radius:8px; background:var(--teal); color:var(--white); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">Pro 시작하기</button>
        </div>

        <!-- Pro+ -->
        <div style="background:linear-gradient(135deg, #fffbf0 0%, #ffffff 100%); border:2px solid #FFA500; border-radius:16px; padding:2rem 1.5rem;">
          <div style="font-size:14px; font-weight:700; color:#FF8C00; margin-bottom:6px;">Pro+</div>
          <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:6px;">
            <span style="font-size:32px; font-weight:900; color:var(--g9);">₩4,990</span>
            <span style="font-size:13px; color:var(--g5);">/월</span>
          </div>
          <div style="font-size:12px; color:var(--g5); margin-bottom:20px;">전문가급 기능 + 우선 지원</div>
          <ul style="list-style:none; padding:0; margin:0 0 24px; font-size:13px; line-height:2;">
            <li style="color:var(--g8);">✓ Pro 플랜의 모든 기능</li>
            <li style="color:var(--g8); font-weight:700;">✓ AI 응답 우선 처리</li>
            <li style="color:var(--g8); font-weight:700;">✓ 고급 양식 분석</li>
            <li style="color:var(--g8); font-weight:700;">✓ 1:1 이메일 지원</li>
            <li style="color:var(--g8);">✓ 신규 기능 우선 체험</li>
          </ul>
          <button id="proPlusSubBtn" onclick="subscribePlan('pro_plus')" style="width:100%; height:42px; border:none; border-radius:8px; background:linear-gradient(135deg, #FFA500, #FF8C00); color:var(--white); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">Pro+ 시작하기</button>
        </div>
      </div>

      <!-- FAQ -->
      <div style="background:var(--g0); padding:2rem; border-radius:16px;">
        <div style="font-size:18px; font-weight:900; color:var(--g9); margin-bottom:1.5rem;">자주 묻는 질문</div>
        <div style="font-size:13px; color:var(--g8); line-height:1.7;">
          <div style="margin-bottom:1rem;"><b style="color:var(--g9);">Q. 무료 체험은 어떻게 되나요?</b><br>회원가입 후 2주 동안 모든 Pro 기능을 무료로 사용할 수 있습니다. 2주 후에는 자동으로 Free 플랜으로 전환됩니다.</div>
          <div style="margin-bottom:1rem;"><b style="color:var(--g9);">Q. 결제는 어떻게 하나요?</b><br>현재는 학부 캡스톤 프로젝트로 운영 중이며, 실제 결제 시스템은 도입 예정입니다. 데모용으로 즉시 활성화됩니다.</div>
          <div style="margin-bottom:1rem;"><b style="color:var(--g9);">Q. 언제든 해지 가능한가요?</b><br>네, 마이페이지에서 언제든 해지하실 수 있습니다.</div>
          <div><b style="color:var(--g9);">Q. Free 플랜의 양식 적용 다운로드 5회 제한은?</b><br>매월 1일에 초기화됩니다. Pro 플랜은 무제한입니다.</div>
        </div>
      </div>
    </div>
  </div>
'''

# 다른 페이지들 뒤에 삽입
if 'id="page-pricing"' not in html:
    # </main> 직전 또는 페이지 끝
    if '</main>' in html:
        html = html.replace('</main>', pricing_page + '\n</main>', 1)
        print("✅ 요금제 페이지 추가")
    else:
        # main 태그가 없으면 다른 page 다음에
        html = html.replace(
            '<!-- ════ COMMUNITY PAGE ════ -->',
            pricing_page + '\n  <!-- ════ COMMUNITY PAGE ════ -->'
        )
        print("✅ 요금제 페이지 추가 (community 앞)")


# 3-4) 프로필 메뉴 (마이페이지 모달)
profile_modal = '''
<!-- 마이페이지 모달 -->
<div id="myPageModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10002; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeMyPage();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; max-width:520px; max-height:85vh; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3); display:flex; flex-direction:column;">
    <div style="padding:20px 24px; border-bottom:1px solid var(--g2); display:flex; align-items:center; justify-content:space-between;">
      <div style="font-size:17px; font-weight:700; color:var(--g9);">👤 마이페이지</div>
      <button onclick="closeMyPage()" style="width:32px; height:32px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px;">×</button>
    </div>
    <div style="flex:1; overflow-y:auto; padding:24px;">

      <!-- 프로필 정보 -->
      <div style="background:var(--g0); border-radius:12px; padding:20px; margin-bottom:1.5rem;">
        <div style="display:flex; gap:14px; align-items:center;">
          <div id="myPageAvatar" style="width:60px; height:60px; border-radius:50%; background:linear-gradient(135deg, var(--teal), var(--teal-dark, #085041)); color:var(--white); display:flex; align-items:center; justify-content:center; font-size:24px; font-weight:900; flex-shrink:0;">U</div>
          <div style="flex:1;">
            <div id="myPageName" style="font-size:16px; font-weight:700; color:var(--g9);"></div>
            <div id="myPageEmail" style="font-size:12px; color:var(--g6); margin-top:2px;"></div>
            <div id="myPageBadge" style="display:inline-block; margin-top:6px; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;"></div>
          </div>
        </div>
      </div>

      <!-- 구독 정보 -->
      <div style="margin-bottom:1.5rem;">
        <div style="font-size:13px; font-weight:700; color:var(--g7); margin-bottom:10px;">💎 구독 상태</div>
        <div id="myPageSubscription" style="background:var(--white); border:1px solid var(--g2); border-radius:10px; padding:14px;">
          <div style="font-size:13px; color:var(--g8);">불러오는 중...</div>
        </div>
      </div>

      <!-- 프로필 수정 -->
      <div style="margin-bottom:1.5rem;">
        <div style="font-size:13px; font-weight:700; color:var(--g7); margin-bottom:10px;">✏️ 프로필 수정</div>
        <input id="myPageNameInput" type="text" placeholder="이름" style="width:100%; height:38px; padding:0 12px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; outline:none; margin-bottom:8px;">
        <button onclick="updateMyProfile()" style="width:100%; height:38px; border:none; border-radius:8px; background:var(--teal); color:var(--white); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">저장</button>
      </div>

      <!-- 로그아웃 -->
      <button onclick="logoutFromMyPage()" style="width:100%; height:40px; border:1.5px solid var(--g2); border-radius:8px; background:var(--white); color:var(--coral); font-family:var(--font); font-size:13px; font-weight:700; cursor:pointer;">로그아웃</button>
    </div>
  </div>
</div>

<!-- Pro 전용 안내 토스트 (조용히) -->
<div id="proHintToast" style="display:none; position:fixed; bottom:30px; right:30px; max-width:340px; background:var(--white); border:1.5px solid var(--teal); border-radius:12px; padding:14px 18px; box-shadow:0 10px 40px rgba(0,0,0,0.15); z-index:10003; cursor:pointer;" onclick="goPricingPage(); document.getElementById('proHintToast').style.display='none';">
  <div style="display:flex; gap:10px; align-items:flex-start;">
    <div style="font-size:24px;">💎</div>
    <div style="flex:1;">
      <div style="font-size:13px; font-weight:700; color:var(--g9); margin-bottom:4px;" id="proHintTitle">Pro 플랜 안내</div>
      <div style="font-size:12px; color:var(--g7); line-height:1.5;" id="proHintMsg"></div>
      <div style="font-size:11px; color:var(--teal); font-weight:700; margin-top:6px;">자세히 보기 →</div>
    </div>
    <button onclick="event.stopPropagation(); document.getElementById('proHintToast').style.display='none';" style="width:24px; height:24px; border:none; background:none; cursor:pointer; font-size:14px; color:var(--g5); padding:0;">×</button>
  </div>
</div>
'''

if 'id="myPageModal"' not in html:
    html = html.replace('</body>', profile_modal + '\n</body>', 1)
    print("✅ 마이페이지 모달 + Pro 안내 토스트 추가")


# 3-5) 사이드바 좌하단 프로필 영역에 클릭 핸들러 추가
# 일반적으로 .sidebar-user 또는 비슷한 클래스가 있을 것으로 예상
# 안전하게 패턴 검색
sidebar_user_patterns = [
    (r'<div class="sidebar-user"', '<div class="sidebar-user" style="cursor:pointer;" onclick="openMyPage()"'),
    (r'<div class="user-profile"', '<div class="user-profile" style="cursor:pointer;" onclick="openMyPage()"'),
]
for pat, replacement in sidebar_user_patterns:
    if re.search(pat, html) and 'openMyPage()' not in html[:html.find(pat)+200] if pat in html else False:
        html = re.sub(pat, replacement, html, count=1)
        print(f"✅ 사이드바 프로필 영역에 onclick 추가")
        break

# 만약 위 패턴을 못 찾으면, 다른 식으로 찾기
if 'openMyPage()' not in html:
    # 로그인된 사용자 표시 영역 찾기 (보통 currentUser 관련 영역)
    # showUserInfo 같은 함수가 채우는 영역이 있을 것
    # 일단 메뉴 마지막에 프로필 메뉴 버튼 추가하는 식으로
    nav_end_marker = '''  <!-- ════ MAIN ════ -->'''
    profile_menu_btn = '''    <button id="profileMenuBtn" class="nav-item" onclick="openMyPage()" style="display:none; margin-top:auto; border-top:1px solid var(--g2); padding-top:14px;">
      <span class="nav-icon">👤</span><span id="profileMenuName">마이페이지</span>
    </button>

  '''
    if nav_end_marker in html and 'id="profileMenuBtn"' not in html:
        html = html.replace(nav_end_marker, profile_menu_btn + nav_end_marker)
        print("✅ 사이드바에 마이페이지 메뉴 추가")


# 3-6) JS 함수들
new_js = '''

// ============================================================
// 요금제 + 프로필
// ============================================================

let _mySubscription = null;

async function loadMySubscription() {
  const token = localStorage.getItem('auth_token');
  if (!token) return null;
  try {
    const r = await fetch(API_BASE + '/api/me/subscription', {
      headers: {'Authorization': 'Bearer ' + token},
    });
    if (!r.ok) return null;
    _mySubscription = await r.json();
    updateSidebarPriceBox();
    updateProfileMenuVisibility();
    return _mySubscription;
  } catch (e) {
    return null;
  }
}

function updateSidebarPriceBox() {
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
  } else if (t === 'pro_plus') {
    tag.textContent = '💎 Pro+ 사용 중';
    amount.innerHTML = 'Pro+';
    amount.style.fontSize = '24px';
    sub.textContent = '전문가급 + 우선 지원';
    cta.textContent = '플랜 관리 →';
  } else if (_mySubscription.trial_active) {
    tag.textContent = '🎁 무료체험 중';
    amount.innerHTML = _mySubscription.trial_days_left + '<span style="font-size:14px;font-weight:600;">일 남음</span>';
    sub.textContent = '체험 종료 후 Pro 추천';
    cta.textContent = 'Pro 미리보기 →';
  } else {
    tag.textContent = '무제한 플랜';
    amount.innerHTML = '2,990<span style="font-size:14px;font-weight:600;">원/월</span>';
    sub.textContent = '지금 바로 시작하세요';
    cta.textContent = '바로가기 →';
  }
}

function updateProfileMenuVisibility() {
  const btn = document.getElementById('profileMenuBtn');
  if (btn) {
    btn.style.display = currentUser ? 'flex' : 'none';
    const nameEl = document.getElementById('profileMenuName');
    if (nameEl && currentUser) {
      nameEl.textContent = (currentUser.full_name || currentUser.username || '내 정보');
    }
  }
}

function goPricingPage() {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    showToast('먼저 로그인해주세요!', 'info');
    showModal();
    return;
  }
  showPage('pricing', null);
}

async function subscribePlan(tier) {
  const token = localStorage.getItem('auth_token');
  if (!token) { showModal(); return; }
  
  const planName = tier === 'pro' ? 'Pro' : 'Pro+';
  if (!confirm(`${planName} 플랜을 구독하시겠습니까?\\n(데모용이므로 즉시 활성화됩니다)`)) return;
  
  try {
    const r = await fetch(API_BASE + '/api/me/subscribe', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify({tier}),
    });
    if (!r.ok) throw new Error('구독 실패');
    const data = await r.json();
    showToast(data.message || '구독 완료!', 'success');
    await loadMySubscription();
    await refreshCurrentUser();
  } catch (e) {
    showToast('실패: ' + e.message, 'error');
  }
}

async function cancelSubscription() {
  if (!confirm('정말 구독을 해지하시겠습니까?')) return;
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/me/cancel-subscription', {
      method: 'POST',
      headers: {'Authorization': 'Bearer ' + token},
    });
    if (!r.ok) throw new Error('해지 실패');
    showToast('구독이 해지되었습니다.', 'info');
    await loadMySubscription();
    await refreshCurrentUser();
    renderMyPageSubscription();
  } catch (e) {
    showToast('실패: ' + e.message, 'error');
  }
}

async function refreshCurrentUser() {
  const token = localStorage.getItem('auth_token');
  if (!token) return;
  try {
    const r = await fetch(API_BASE + '/api/me', {headers: {'Authorization': 'Bearer ' + token}});
    if (r.ok) {
      currentUser = await r.json();
      updateUIForUser(currentUser);
    }
  } catch (e) { /* ignore */ }
}

function openMyPage() {
  if (!currentUser) { showModal(); return; }
  
  const initial = (currentUser.full_name || currentUser.username || 'U').charAt(0).toUpperCase();
  document.getElementById('myPageAvatar').textContent = initial;
  document.getElementById('myPageName').textContent = currentUser.full_name || currentUser.username;
  document.getElementById('myPageEmail').textContent = currentUser.email || '';
  document.getElementById('myPageNameInput').value = currentUser.full_name || '';
  
  const badge = document.getElementById('myPageBadge');
  const tier = currentUser.subscription_tier || 'free';
  if (tier === 'pro') {
    badge.textContent = '✨ Pro';
    badge.style.background = 'var(--teal-3)';
    badge.style.color = 'var(--teal-dark, #085041)';
  } else if (tier === 'pro_plus') {
    badge.textContent = '💎 Pro+';
    badge.style.background = '#FFF3E0';
    badge.style.color = '#FF8C00';
  } else if (currentUser.trial_active) {
    badge.textContent = `🎁 무료체험 ${currentUser.trial_days_left}일`;
    badge.style.background = 'var(--coral-3, #FFE5DC)';
    badge.style.color = 'var(--coral)';
  } else {
    badge.textContent = 'Free';
    badge.style.background = 'var(--g1)';
    badge.style.color = 'var(--g7)';
  }
  
  renderMyPageSubscription();
  document.getElementById('myPageModal').style.display = 'block';
}

function closeMyPage() {
  document.getElementById('myPageModal').style.display = 'none';
}

async function renderMyPageSubscription() {
  const sub = await loadMySubscription();
  const container = document.getElementById('myPageSubscription');
  if (!container) return;
  if (!sub) {
    container.innerHTML = '<div style="font-size:12px; color:var(--coral);">정보를 불러올 수 없습니다.</div>';
    return;
  }
  
  let html = '';
  const tier = sub.tier;
  
  if (tier === 'pro' || tier === 'pro_plus') {
    const planName = tier === 'pro' ? 'Pro' : 'Pro+';
    const expiresStr = sub.expires_at ? new Date(sub.expires_at).toLocaleDateString('ko-KR') : '-';
    html = `
      <div style="font-size:14px; font-weight:700; color:var(--teal); margin-bottom:4px;">현재 플랜: ${planName}</div>
      <div style="font-size:12px; color:var(--g6); margin-bottom:10px;">만료일: ${expiresStr}</div>
      <button onclick="cancelSubscription()" style="padding:6px 12px; border:1px solid var(--coral); border-radius:6px; background:var(--white); color:var(--coral); font-family:var(--font); font-size:12px; cursor:pointer;">구독 해지</button>
    `;
  } else if (sub.trial_active) {
    html = `
      <div style="font-size:14px; font-weight:700; color:var(--coral); margin-bottom:4px;">🎁 무료 체험 중</div>
      <div style="font-size:12px; color:var(--g7); margin-bottom:10px;">남은 기간: <b>${sub.trial_days_left}일</b> · 모든 기능 사용 가능</div>
      <button onclick="goPricingPage(); closeMyPage();" style="padding:6px 12px; border:none; border-radius:6px; background:var(--teal); color:var(--white); font-family:var(--font); font-size:12px; font-weight:700; cursor:pointer;">요금제 보기 →</button>
    `;
  } else {
    const used = sub.template_download_count || 0;
    const limit = 5;
    html = `
      <div style="font-size:14px; font-weight:700; color:var(--g7); margin-bottom:4px;">현재 플랜: Free</div>
      <div style="font-size:12px; color:var(--g6); margin-bottom:6px;">이번 달 양식 적용 다운로드: <b>${used}/${limit}</b></div>
      <div style="width:100%; height:6px; background:var(--g1); border-radius:3px; overflow:hidden; margin-bottom:10px;">
        <div style="width:${Math.min(100, (used/limit)*100)}%; height:100%; background:var(--teal);"></div>
      </div>
      <button onclick="goPricingPage(); closeMyPage();" style="padding:6px 12px; border:none; border-radius:6px; background:var(--teal); color:var(--white); font-family:var(--font); font-size:12px; font-weight:700; cursor:pointer;">Pro 업그레이드 →</button>
    `;
  }
  container.innerHTML = html;
}

async function updateMyProfile() {
  const name = document.getElementById('myPageNameInput').value.trim();
  if (!name) { showToast('이름을 입력하세요.', 'error'); return; }
  
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/me/profile', {
      method: 'PUT',
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify({full_name: name}),
    });
    if (!r.ok) throw new Error('수정 실패');
    showToast('프로필이 업데이트되었습니다!', 'success');
    await refreshCurrentUser();
    document.getElementById('myPageName').textContent = currentUser.full_name || currentUser.username;
  } catch (e) {
    showToast('실패: ' + e.message, 'error');
  }
}

function logoutFromMyPage() {
  closeMyPage();
  if (typeof logout === 'function') logout();
  else {
    localStorage.removeItem('auth_token');
    currentUser = null;
    if (typeof updateUIForUser === 'function') updateUIForUser(null);
    showToast('로그아웃되었습니다.', 'info');
  }
}

// Pro 안내 토스트 (조용한 표시)
function showProHint(title, message) {
  document.getElementById('proHintTitle').textContent = title || 'Pro 플랜 안내';
  document.getElementById('proHintMsg').textContent = message;
  const toast = document.getElementById('proHintToast');
  toast.style.display = 'block';
  // 7초 후 자동 닫기
  setTimeout(() => { toast.style.display = 'none'; }, 7000);
}

// API 호출 시 403 PRO_REQUIRED 응답을 가로채서 안내
const _origFetchForPro = window.fetch;
window.fetch = async function(...args) {
  const response = await _origFetchForPro.apply(this, args);
  // POST 요청이 403이고 detail이 PRO_REQUIRED인 경우만 처리
  if (response.status === 403) {
    try {
      const cloned = response.clone();
      const data = await cloned.json();
      if (data.detail && typeof data.detail === 'string') {
        if (data.detail.startsWith('PRO_REQUIRED:')) {
          showProHint('Pro 플랜 안내', data.detail.replace('PRO_REQUIRED:', '').trim());
        } else if (data.detail.startsWith('LIMIT_EXCEEDED:')) {
          showProHint('월 한도 초과', data.detail.replace('LIMIT_EXCEEDED:', '').trim());
        }
      }
    } catch (e) { /* not json, ignore */ }
  }
  return response;
};

// 로그인 후 구독 정보 자동 로드
const _origUpdateUIForUserSub = updateUIForUser;
updateUIForUser = function(user) {
  _origUpdateUIForUserSub(user);
  if (user) {
    loadMySubscription();
    updateProfileMenuVisibility();
  } else {
    _mySubscription = null;
    updateSidebarPriceBox();
    updateProfileMenuVisibility();
  }
};
'''

if 'function goPricingPage' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + new_js + '\n' + html[last_close:]
        print("✅ 요금제/프로필 JS 추가")


HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 60)
print("🎉 패치 완료!")
print("=" * 60)
print("\n다음 단계:")
print("  rm edubridge.db  (DB 스키마 변경됨)")
print("\n새 기능:")
print("  1. .hwp 양식 업로드 제거 → .docx만 지원")
print("  2. 요금제: Free (2주 체험) / Pro 2,990원 / Pro+ 4,990원")
print("  3. 사이드바 '바로가기' → 로그인 체크 후 요금제 페이지")
print("  4. 사이드바 좌하단 '마이페이지' 메뉴")
print("     - 프로필 수정 (이름)")
print("     - 구독 상태 + 사용량")
print("     - Pro 업그레이드 / 해지")
print("     - 로그아웃")
print("  5. 무료 사용자가 Pro 기능 시도 시 → 조용한 토스트 안내")
print("\n무료 5회 다운로드 제한 + 수정 채팅 Pro 전용 적용됨!")
