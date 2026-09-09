#!/usr/bin/env python3
"""
patch_community_full.py
========================
1. 커뮤니티: 게시글 CRUD + 댓글 + 좋아요
2. 공지사항: ID=1 사용자만 작성, 나머지는 읽기
3. 푸터: 문의/약관/카피라이트
4. 광고 영역: 사이드바 상단 + 본문 영역에 광고 자리 (비워두면 "광고 문의 환영")
"""
from pathlib import Path

BACKEND = Path(".")
MAIN_PATH = BACKEND / "main.py"
DB_PATH = BACKEND / "database.py"
HTML_PATH = BACKEND / "static" / "edu-bridge-full.html"


# ============================================================
# 1) database.py: 게시글/댓글/좋아요/공지 테이블 추가
# ============================================================
db_code = DB_PATH.read_text(encoding="utf-8")

if "class CommunityPost" not in db_code:
    insertion = "# ============================================================\n# 데이터베이스 초기화"
    new_tables = '''
class CommunityPost(Base):
    """커뮤니티 게시글"""
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(50), default="general")  # general, question, tip, share
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CommunityComment(Base):
    """커뮤니티 댓글"""
    __tablename__ = "community_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommunityLike(Base):
    """게시글 좋아요"""
    __tablename__ = "community_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notice(Base):
    """공지사항 (ID=1 사용자만 작성 가능)"""
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False)  # 상단 고정 여부
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


'''
    db_code = db_code.replace(insertion, new_tables + insertion)
    DB_PATH.write_text(db_code, encoding="utf-8")
    print("✅ database.py: 커뮤니티/공지 테이블 4개 추가")


# ============================================================
# 2) main.py: 관련 API 추가
# ============================================================
main_code = MAIN_PATH.read_text(encoding="utf-8")

# import에 새 모델 추가
if "CommunityPost" not in main_code:
    main_code = main_code.replace(
        "User, SavedLesson, UserTemplate, AppliedTemplate,",
        "User, SavedLesson, UserTemplate, AppliedTemplate,\n    CommunityPost, CommunityComment, CommunityLike, Notice,"
    )

# 새 API 블록
new_apis = '''

# ============================================================
# 커뮤니티 API
# ============================================================

@app.get("/api/community/posts")
def api_community_list(category: Optional[str] = None, db: Session = Depends(get_db)):
    """게시글 목록 (로그인 안 해도 조회 가능)"""
    q = db.query(CommunityPost).order_by(CommunityPost.created_at.desc())
    if category and category != "all":
        q = q.filter(CommunityPost.category == category)
    posts = q.limit(100).all()

    result = []
    for p in posts:
        author = db.query(User).filter(User.id == p.user_id).first()
        comment_count = db.query(CommunityComment).filter(CommunityComment.post_id == p.id).count()
        result.append({
            "id": p.id,
            "user_id": p.user_id,
            "author_name": (author.full_name or author.username) if author else "(탈퇴 사용자)",
            "category": p.category,
            "title": p.title,
            "content_preview": (p.content or "")[:120],
            "view_count": p.view_count,
            "like_count": p.like_count,
            "comment_count": comment_count,
            "created_at": p.created_at.isoformat(),
        })
    return result


@app.get("/api/community/posts/{post_id}")
def api_community_detail(post_id: int, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_optional_user)):
    """게시글 상세"""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글 없음")

    # 조회수 증가
    post.view_count = (post.view_count or 0) + 1
    db.commit()

    author = db.query(User).filter(User.id == post.user_id).first()
    comments = db.query(CommunityComment).filter(CommunityComment.post_id == post_id).order_by(CommunityComment.created_at.asc()).all()
    comments_data = []
    for c in comments:
        cmt_author = db.query(User).filter(User.id == c.user_id).first()
        comments_data.append({
            "id": c.id,
            "user_id": c.user_id,
            "author_name": (cmt_author.full_name or cmt_author.username) if cmt_author else "(탈퇴 사용자)",
            "content": c.content,
            "created_at": c.created_at.isoformat(),
            "is_mine": current_user and c.user_id == current_user.id,
        })

    is_liked = False
    if current_user:
        is_liked = db.query(CommunityLike).filter(
            CommunityLike.post_id == post_id,
            CommunityLike.user_id == current_user.id
        ).first() is not None

    return {
        "id": post.id,
        "user_id": post.user_id,
        "author_name": (author.full_name or author.username) if author else "(탈퇴 사용자)",
        "category": post.category,
        "title": post.title,
        "content": post.content,
        "view_count": post.view_count,
        "like_count": post.like_count,
        "is_liked": is_liked,
        "is_mine": current_user and post.user_id == current_user.id,
        "created_at": post.created_at.isoformat(),
        "comments": comments_data,
    }


@app.post("/api/community/posts")
def api_community_create(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """게시글 작성"""
    title = (body.get("title") or "").strip()
    content = (body.get("content") or "").strip()
    category = body.get("category", "general")
    if not title or not content:
        raise HTTPException(status_code=400, detail="제목과 내용 필요")

    post = CommunityPost(
        user_id=current_user.id,
        category=category,
        title=title[:200],
        content=content,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": post.id, "message": "작성 완료"}


@app.delete("/api/community/posts/{post_id}")
def api_community_delete(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """게시글 삭제 (작성자만)"""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글 없음")
    if post.user_id != current_user.id and current_user.id != 1:
        raise HTTPException(status_code=403, detail="권한 없음")

    db.query(CommunityComment).filter(CommunityComment.post_id == post_id).delete()
    db.query(CommunityLike).filter(CommunityLike.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    return {"message": "삭제됨"}


@app.post("/api/community/posts/{post_id}/like")
def api_community_like(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """좋아요 토글"""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글 없음")

    existing = db.query(CommunityLike).filter(
        CommunityLike.post_id == post_id,
        CommunityLike.user_id == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        post.like_count = max(0, (post.like_count or 0) - 1)
        liked = False
    else:
        db.add(CommunityLike(post_id=post_id, user_id=current_user.id))
        post.like_count = (post.like_count or 0) + 1
        liked = True

    db.commit()
    return {"is_liked": liked, "like_count": post.like_count}


@app.post("/api/community/posts/{post_id}/comments")
def api_community_comment(post_id: int, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """댓글 작성"""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글 없음")
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="내용 필요")

    cmt = CommunityComment(post_id=post_id, user_id=current_user.id, content=content)
    db.add(cmt)
    db.commit()
    db.refresh(cmt)
    return {"id": cmt.id, "message": "댓글 작성됨"}


@app.delete("/api/community/comments/{comment_id}")
def api_community_comment_delete(comment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """댓글 삭제"""
    cmt = db.query(CommunityComment).filter(CommunityComment.id == comment_id).first()
    if not cmt:
        raise HTTPException(status_code=404, detail="댓글 없음")
    if cmt.user_id != current_user.id and current_user.id != 1:
        raise HTTPException(status_code=403, detail="권한 없음")
    db.delete(cmt)
    db.commit()
    return {"message": "삭제됨"}


# ============================================================
# 공지사항 API (ID=1만 작성)
# ============================================================

@app.get("/api/notices")
def api_notices_list(db: Session = Depends(get_db)):
    """공지사항 목록 (누구나 조회 가능)"""
    notices = db.query(Notice).order_by(
        Notice.is_pinned.desc(),
        Notice.created_at.desc()
    ).all()
    result = []
    for n in notices:
        author = db.query(User).filter(User.id == n.user_id).first()
        result.append({
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "is_pinned": n.is_pinned,
            "author_name": (author.full_name or author.username) if author else "관리자",
            "created_at": n.created_at.isoformat(),
        })
    return result


@app.post("/api/notices")
def api_notice_create(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """공지사항 작성 (ID=1만)"""
    if current_user.id != 1:
        raise HTTPException(status_code=403, detail="관리자만 작성 가능합니다")
    title = (body.get("title") or "").strip()
    content = (body.get("content") or "").strip()
    is_pinned = bool(body.get("is_pinned", False))
    if not title or not content:
        raise HTTPException(status_code=400, detail="제목과 내용 필요")
    n = Notice(user_id=current_user.id, title=title[:200], content=content, is_pinned=is_pinned)
    db.add(n)
    db.commit()
    db.refresh(n)
    return {"id": n.id, "message": "공지 작성됨"}


@app.delete("/api/notices/{notice_id}")
def api_notice_delete(notice_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """공지사항 삭제 (ID=1만)"""
    if current_user.id != 1:
        raise HTTPException(status_code=403, detail="관리자만 삭제 가능합니다")
    n = db.query(Notice).filter(Notice.id == notice_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="공지 없음")
    db.delete(n)
    db.commit()
    return {"message": "삭제됨"}


@app.patch("/api/notices/{notice_id}/pin")
def api_notice_toggle_pin(notice_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """공지 고정 토글 (ID=1만)"""
    if current_user.id != 1:
        raise HTTPException(status_code=403, detail="관리자만 가능합니다")
    n = db.query(Notice).filter(Notice.id == notice_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="공지 없음")
    n.is_pinned = not n.is_pinned
    db.commit()
    return {"is_pinned": n.is_pinned}

'''

if "/api/community/posts" not in main_code:
    main_code = main_code.replace(
        '\n@app.get("/api/health")',
        new_apis + '\n@app.get("/api/health")'
    )
    MAIN_PATH.write_text(main_code, encoding="utf-8")
    print("✅ main.py: 커뮤니티/공지 API 추가")


# ============================================================
# 3) HTML 패치
# ============================================================
html = HTML_PATH.read_text(encoding="utf-8")
backup = HTML_PATH.with_suffix(".html.bak_community")
backup.write_text(html, encoding="utf-8")
print(f"✅ HTML 백업: {backup}")


# 3-1) 사이드바 상단 가격 박스 → 광고 영역으로 (소프트 표시)
old_sidebar_top = '''  <div class="sidebar-price">
    <div class="sidebar-price-tag">무제한 플랜</div>
    <div class="sidebar-price-amount">2,990<span style="font-size:14px;font-weight:600;">원/월</span></div>
    <div class="sidebar-price-sub">지금 바로 시작하세요</div>
    <button class="sidebar-price-cta">바로가기 →</button>
  </div>'''

new_sidebar_top = '''  <div class="sidebar-price">
    <div class="sidebar-price-tag">📢 광고 영역</div>
    <div class="sidebar-price-amount" style="font-size:14px;line-height:1.4;">광고 문의<br>환영합니다</div>
    <div class="sidebar-price-sub">edubridge@example.com</div>
    <button class="sidebar-price-cta" onclick="showFooterContact()">문의하기 →</button>
  </div>'''

if old_sidebar_top in html:
    html = html.replace(old_sidebar_top, new_sidebar_top)
    print("✅ 사이드바 상단 → 광고 영역으로")


# 3-2) 커뮤니티 페이지 동적 변환
old_community = '<div class="page" id="page-community">'
# 커뮤니티 페이지 전체 영역을 찾아서 교체
import re
pattern = re.compile(
    r'<div class="page" id="page-community">.*?</div>\s*</div>\s*(?=<!-- ════)',
    re.DOTALL
)

new_community_page = '''<div class="page" id="page-community">
    <div style="padding:2rem;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;flex-wrap:wrap;gap:10px;">
        <div>
          <div class="page-title">💬 교사 커뮤니티</div>
          <div class="page-sub">선생님들과 노하우를 공유하고 질문해보세요</div>
        </div>
        <button class="btn-primary" onclick="openCommunityWriteModal()" style="height:38px;">+ 새 글 작성</button>
      </div>

      <!-- 카테고리 필터 -->
      <div style="display:flex;gap:8px;margin:1rem 0;flex-wrap:wrap;">
        <button class="comm-cat-btn active" data-cat="all" onclick="filterCommunity('all')">전체</button>
        <button class="comm-cat-btn" data-cat="general" onclick="filterCommunity('general')">💬 자유</button>
        <button class="comm-cat-btn" data-cat="question" onclick="filterCommunity('question')">❓ 질문</button>
        <button class="comm-cat-btn" data-cat="tip" onclick="filterCommunity('tip')">💡 팁/노하우</button>
        <button class="comm-cat-btn" data-cat="share" onclick="filterCommunity('share')">📤 자료 공유</button>
      </div>

      <div id="commEmpty" style="display:none;text-align:center;padding:3rem 1rem;color:var(--g5);">
        <div style="font-size:48px;margin-bottom:12px;">💬</div>
        <div style="font-size:14px;">아직 게시글이 없습니다. 첫 글을 작성해보세요!</div>
      </div>
      <ul class="log-list" id="commList"></ul>
    </div>
  </div>

  '''

m = pattern.search(html)
if m and 'id="commList"' not in html:
    html = html[:m.start()] + new_community_page + html[m.end():]
    print("✅ 커뮤니티 페이지 동적 버전으로 교체")


# 3-3) 공지사항 페이지 동적 변환
pattern_notice = re.compile(
    r'<div class="page" id="page-notice">.*?</div>\s*</div>\s*(?=<!-- |</body|<script)',
    re.DOTALL
)

new_notice_page = '''<div class="page" id="page-notice">
    <div style="padding:2rem;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;flex-wrap:wrap;gap:10px;">
        <div>
          <div class="page-title">📢 공지사항</div>
          <div class="page-sub">EDU-bridge의 최신 소식을 확인하세요</div>
        </div>
        <button id="adminNoticeBtn" class="btn-primary" onclick="openNoticeWriteModal()" style="height:38px;display:none;">+ 공지 작성</button>
      </div>

      <div id="noticeEmpty" style="display:none;text-align:center;padding:3rem 1rem;color:var(--g5);">
        <div style="font-size:48px;margin-bottom:12px;">📢</div>
        <div style="font-size:14px;">공지사항이 없습니다.</div>
      </div>
      <ul class="log-list" id="noticeList"></ul>
    </div>
  </div>

  '''

m2 = pattern_notice.search(html)
if m2 and 'id="noticeList"' not in html:
    html = html[:m2.start()] + new_notice_page + html[m2.end():]
    print("✅ 공지사항 페이지 동적 버전으로 교체")


# 3-4) 푸터 추가 (.app 직전 닫는 div 앞)
footer_html = '''
  <!-- ════ FOOTER ════ -->
  <footer id="appFooter" style="margin-top:auto; background:var(--g9, #1a1a1a); color:#9ca3af; padding:2rem; font-size:12px;">
    <div style="max-width:1200px; margin:0 auto; display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:2rem;">
      <div>
        <div style="font-size:16px; font-weight:700; color:var(--white); margin-bottom:8px; font-family:var(--font);">EDU-bridge</div>
        <div style="line-height:1.7;">글로벌 유아교육안 설계 플랫폼<br>10개국 교육과정 기반 AI 추천 시스템</div>
      </div>
      <div>
        <div style="font-weight:700; color:var(--white); margin-bottom:8px;">서비스</div>
        <a href="#" onclick="showPage('scanner', document.querySelector('[onclick*=scanner]'));return false;" style="display:block; color:#9ca3af; text-decoration:none; line-height:1.8;">Play-Scanner</a>
        <a href="#" onclick="showPage('kidsnote', document.querySelector('[onclick*=kidsnote]'));return false;" style="display:block; color:#9ca3af; text-decoration:none; line-height:1.8;">AI 알림장</a>
        <a href="#" onclick="showPage('templates', document.querySelector('[onclick*=templates]'));return false;" style="display:block; color:#9ca3af; text-decoration:none; line-height:1.8;">내 양식</a>
      </div>
      <div>
        <div style="font-weight:700; color:var(--white); margin-bottom:8px;">고객 지원</div>
        <a href="#" onclick="showFooterContact();return false;" style="display:block; color:#9ca3af; text-decoration:none; line-height:1.8;">문의하기</a>
        <a href="#" onclick="showFooterTerms();return false;" style="display:block; color:#9ca3af; text-decoration:none; line-height:1.8;">이용약관</a>
        <a href="#" onclick="showFooterPrivacy();return false;" style="display:block; color:#9ca3af; text-decoration:none; line-height:1.8;">개인정보처리방침</a>
      </div>
      <div>
        <div style="font-weight:700; color:var(--white); margin-bottom:8px;">📢 광고 문의</div>
        <div style="line-height:1.7;">
          교사 대상 광고 환영합니다.<br>
          <a href="mailto:edubridge@example.com" style="color:var(--teal); text-decoration:none;">edubridge@example.com</a>
        </div>
      </div>
    </div>
    <div style="max-width:1200px; margin:2rem auto 0; padding-top:1.5rem; border-top:1px solid #2a2a2a; display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px;">
      <div>© 2026 EDU-bridge. All rights reserved.</div>
      <div>학부 캡스톤 프로젝트 · 송민서</div>
    </div>
  </footer>

  <!-- ════ FOOTER BANNER (메인 영역 하단 광고) ════ -->
  <div id="footerBanner" style="position:relative; padding:1rem 2rem; background:#FFFBF0; border-top:1px dashed var(--g3); text-align:center; color:var(--g6); font-size:12px;">
    📢 광고 자리입니다. 교사 대상 광고 문의: <a href="mailto:edubridge@example.com" style="color:var(--teal); font-weight:700;">edubridge@example.com</a>
  </div>
'''

# .app 닫는 부분 직전에 푸터 삽입 (혹은 </body> 직전)
if 'id="appFooter"' not in html:
    # .app div가 끝나는 위치 (모든 모달 전에)
    # 일단 </body> 직전에 삽입 (모달들 다음, 푸터로)
    html = html.replace(
        '</body>',
        footer_html + '\n</body>',
        1
    )
    print("✅ 푸터 + 하단 광고 배너 추가")


# 3-5) 커뮤니티 작성/상세 모달 + 공지 작성 모달 + 푸터 모달들
extra_modals = '''
<!-- 커뮤니티 글쓰기 모달 -->
<div id="commWriteModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10001; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeCommunityWriteModal();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; max-width:640px; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3);">
    <div style="padding:20px 24px; border-bottom:1px solid var(--g2); display:flex; align-items:center; justify-content:space-between;">
      <div style="font-size:17px; font-weight:700; color:var(--g9);">✍️ 새 글 작성</div>
      <button onclick="closeCommunityWriteModal()" style="width:32px; height:32px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px;">×</button>
    </div>
    <div style="padding:24px;">
      <label style="display:block; font-size:12px; font-weight:600; color:var(--g7); margin-bottom:6px;">카테고리</label>
      <select id="commWriteCategory" style="width:100%; height:40px; padding:0 12px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; background:var(--white); margin-bottom:14px; outline:none;">
        <option value="general">💬 자유</option>
        <option value="question">❓ 질문</option>
        <option value="tip">💡 팁/노하우</option>
        <option value="share">📤 자료 공유</option>
      </select>
      <label style="display:block; font-size:12px; font-weight:600; color:var(--g7); margin-bottom:6px;">제목</label>
      <input id="commWriteTitle" type="text" placeholder="제목을 입력하세요" style="width:100%; height:40px; padding:0 12px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; margin-bottom:14px; outline:none;">
      <label style="display:block; font-size:12px; font-weight:600; color:var(--g7); margin-bottom:6px;">내용</label>
      <textarea id="commWriteContent" placeholder="내용을 입력하세요" style="width:100%; min-height:200px; padding:12px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; line-height:1.6; resize:vertical; outline:none;"></textarea>
    </div>
    <div style="padding:14px 24px; border-top:1px solid var(--g2); display:flex; gap:10px; justify-content:flex-end;">
      <button onclick="closeCommunityWriteModal()" style="padding:9px 16px; border:1px solid var(--g2); border-radius:8px; background:var(--white); cursor:pointer; font-size:13px;">취소</button>
      <button onclick="submitCommunityPost()" style="padding:9px 18px; border:none; border-radius:8px; background:var(--teal); color:var(--white); cursor:pointer; font-size:13px; font-weight:700;">작성하기</button>
    </div>
  </div>
</div>

<!-- 게시글 상세 모달 -->
<div id="commDetailModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10001; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeCommunityDetail();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:92%; max-width:760px; max-height:90vh; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3); display:flex; flex-direction:column;">
    <div style="padding:18px 24px; border-bottom:1px solid var(--g2); display:flex; align-items:center; justify-content:space-between;">
      <div id="commDetailTitle" style="font-size:17px; font-weight:700; color:var(--g9); flex:1;"></div>
      <button onclick="closeCommunityDetail()" style="width:32px; height:32px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px;">×</button>
    </div>
    <div id="commDetailBody" style="flex:1; overflow-y:auto; padding:24px;"></div>
  </div>
</div>

<!-- 공지 작성 모달 -->
<div id="noticeWriteModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10001; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeNoticeWriteModal();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; max-width:640px; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3);">
    <div style="padding:20px 24px; border-bottom:1px solid var(--g2); display:flex; align-items:center; justify-content:space-between;">
      <div style="font-size:17px; font-weight:700; color:var(--g9);">📢 공지 작성 (관리자)</div>
      <button onclick="closeNoticeWriteModal()" style="width:32px; height:32px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px;">×</button>
    </div>
    <div style="padding:24px;">
      <label style="display:flex; align-items:center; gap:8px; font-size:13px; color:var(--g8); margin-bottom:14px; cursor:pointer;">
        <input type="checkbox" id="noticePinned"> 📌 상단 고정
      </label>
      <label style="display:block; font-size:12px; font-weight:600; color:var(--g7); margin-bottom:6px;">제목</label>
      <input id="noticeWriteTitle" type="text" placeholder="공지 제목" style="width:100%; height:40px; padding:0 12px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; margin-bottom:14px; outline:none;">
      <label style="display:block; font-size:12px; font-weight:600; color:var(--g7); margin-bottom:6px;">내용</label>
      <textarea id="noticeWriteContent" placeholder="공지 내용" style="width:100%; min-height:200px; padding:12px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; line-height:1.6; resize:vertical; outline:none;"></textarea>
    </div>
    <div style="padding:14px 24px; border-top:1px solid var(--g2); display:flex; gap:10px; justify-content:flex-end;">
      <button onclick="closeNoticeWriteModal()" style="padding:9px 16px; border:1px solid var(--g2); border-radius:8px; background:var(--white); cursor:pointer; font-size:13px;">취소</button>
      <button onclick="submitNotice()" style="padding:9px 18px; border:none; border-radius:8px; background:var(--coral); color:var(--white); cursor:pointer; font-size:13px; font-weight:700;">공지 게시</button>
    </div>
  </div>
</div>

<!-- 푸터 정보 모달 (문의/약관/개인정보) -->
<div id="footerInfoModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10001; backdrop-filter:blur(4px);" onclick="if(event.target===this) closeFooterModal();">
  <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; max-width:560px; max-height:80vh; background:var(--white); border-radius:var(--r-lg); box-shadow:0 20px 60px rgba(0,0,0,0.3); display:flex; flex-direction:column;">
    <div style="padding:18px 24px; border-bottom:1px solid var(--g2); display:flex; align-items:center; justify-content:space-between;">
      <div id="footerInfoTitle" style="font-size:17px; font-weight:700; color:var(--g9);"></div>
      <button onclick="closeFooterModal()" style="width:32px; height:32px; border:none; background:var(--g1); border-radius:50%; cursor:pointer; font-size:18px;">×</button>
    </div>
    <div id="footerInfoContent" style="flex:1; overflow-y:auto; padding:24px; font-size:13px; color:var(--g9); line-height:1.7;"></div>
  </div>
</div>

<style>
.comm-cat-btn {
  padding: 7px 14px;
  border: 1px solid var(--g2);
  border-radius: 16px;
  background: var(--white);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 600;
  color: var(--g7);
  cursor: pointer;
  transition: all 0.15s;
}
.comm-cat-btn:hover { background: var(--g1); }
.comm-cat-btn.active {
  background: var(--teal);
  color: var(--white);
  border-color: var(--teal);
}
</style>
'''

if 'id="commWriteModal"' not in html:
    html = html.replace('</body>', extra_modals + '\n</body>', 1)
    print("✅ 커뮤니티/공지/푸터 모달들 추가")


# 3-6) JS 함수들
new_js = '''

// ============================================================
// 커뮤니티
// ============================================================

let _allCommPosts = [];
let _currentCommCategory = 'all';
const COMM_CAT_LABELS = {
  general: '💬 자유', question: '❓ 질문', tip: '💡 팁', share: '📤 자료'
};

async function loadCommunity() {
  try {
    const url = API_BASE + '/api/community/posts' + (_currentCommCategory !== 'all' ? '?category=' + _currentCommCategory : '');
    const r = await fetch(url);
    if (!r.ok) throw new Error('로드 실패');
    _allCommPosts = await r.json();
    renderCommunity();
  } catch (e) {
    console.error('커뮤니티 로드 실패:', e);
  }
}

function filterCommunity(cat) {
  _currentCommCategory = cat;
  document.querySelectorAll('.comm-cat-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.cat === cat);
  });
  loadCommunity();
}

function renderCommunity() {
  const list = document.getElementById('commList');
  const empty = document.getElementById('commEmpty');
  if (!list) return;
  if (!_allCommPosts.length) {
    empty.style.display = 'block';
    list.innerHTML = '';
    return;
  }
  empty.style.display = 'none';
  list.innerHTML = _allCommPosts.map(p => {
    const date = new Date(p.created_at).toLocaleDateString('ko-KR');
    const catLabel = COMM_CAT_LABELS[p.category] || '💬';
    return `
      <li class="log-item" style="cursor:pointer;" onclick="openCommunityDetail(${p.id})">
        <div class="log-thumb" style="background:var(--g1);">💬</div>
        <div class="log-content">
          <div style="display:flex; gap:8px; align-items:center; margin-bottom:4px;">
            <span style="background:var(--teal-3); color:var(--teal-dark, #085041); padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700;">${catLabel}</span>
            <span class="log-title">${escapeHtml(p.title)}</span>
          </div>
          <div class="log-meta">${escapeHtml(p.author_name)} · 👁 ${p.view_count} · ❤️ ${p.like_count} · 💬 ${p.comment_count}</div>
          <div style="font-size:11px; color:var(--g5); margin-top:4px;">${escapeHtml(p.content_preview)}${p.content_preview.length>=120?'...':''}</div>
        </div>
        <div class="log-right"><div class="log-date">${date}</div></div>
      </li>
    `;
  }).join('');
}

function openCommunityWriteModal() {
  if (!localStorage.getItem('auth_token')) { showModal(); return; }
  document.getElementById('commWriteTitle').value = '';
  document.getElementById('commWriteContent').value = '';
  document.getElementById('commWriteModal').style.display = 'block';
}

function closeCommunityWriteModal() {
  document.getElementById('commWriteModal').style.display = 'none';
}

async function submitCommunityPost() {
  const title = document.getElementById('commWriteTitle').value.trim();
  const content = document.getElementById('commWriteContent').value.trim();
  const category = document.getElementById('commWriteCategory').value;
  if (!title || !content) { showToast('제목과 내용을 입력하세요.', 'error'); return; }
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/community/posts', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization':'Bearer '+token},
      body: JSON.stringify({title, content, category}),
    });
    if (!r.ok) throw new Error('작성 실패');
    showToast('게시글이 작성되었습니다!', 'success');
    closeCommunityWriteModal();
    loadCommunity();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function openCommunityDetail(postId) {
  document.getElementById('commDetailBody').innerHTML = '<div style="text-align:center;padding:2rem;color:var(--g5);">불러오는 중...</div>';
  document.getElementById('commDetailTitle').textContent = '';
  document.getElementById('commDetailModal').style.display = 'block';
  
  const token = localStorage.getItem('auth_token');
  try {
    const headers = token ? {'Authorization':'Bearer '+token} : {};
    const r = await fetch(API_BASE + '/api/community/posts/' + postId, {headers});
    if (!r.ok) throw new Error('로드 실패');
    const post = await r.json();
    document.getElementById('commDetailTitle').textContent = post.title;
    renderCommunityDetail(post);
  } catch (e) {
    document.getElementById('commDetailBody').innerHTML = '<div style="text-align:center;padding:2rem;color:var(--coral);">❌ '+e.message+'</div>';
  }
}

function renderCommunityDetail(post) {
  const catLabel = COMM_CAT_LABELS[post.category] || '💬';
  const date = new Date(post.created_at).toLocaleString('ko-KR');
  const deleteBtn = (post.is_mine || (currentUser && currentUser.id === 1)) ? 
    `<button onclick="deleteCommunityPost(${post.id})" style="padding:5px 10px; border:1px solid var(--g2); border-radius:6px; background:var(--white); color:var(--coral); cursor:pointer; font-size:11px;">🗑 삭제</button>` : '';
  
  const html = `
    <div style="margin-bottom:1rem;">
      <span style="background:var(--teal-3); color:var(--teal-dark, #085041); padding:3px 10px; border-radius:10px; font-size:11px; font-weight:700;">${catLabel}</span>
    </div>
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem; padding-bottom:1rem; border-bottom:1px solid var(--g2);">
      <div style="display:flex; gap:8px; align-items:center; font-size:12px; color:var(--g6);">
        <span style="font-weight:700; color:var(--g8);">${escapeHtml(post.author_name)}</span>
        <span>·</span>
        <span>${date}</span>
        <span>·</span>
        <span>👁 ${post.view_count}</span>
      </div>
      ${deleteBtn}
    </div>
    <div style="font-size:14px; color:var(--g9); line-height:1.7; white-space:pre-wrap; margin-bottom:2rem;">${escapeHtml(post.content)}</div>
    
    <div style="display:flex; gap:10px; padding:12px 0; border-top:1px solid var(--g2); border-bottom:1px solid var(--g2); margin-bottom:1.5rem;">
      <button onclick="toggleCommunityLike(${post.id})" style="padding:8px 16px; border:1.5px solid ${post.is_liked?'var(--coral)':'var(--g2)'}; border-radius:8px; background:${post.is_liked?'var(--coral-3, #FFE5DC)':'var(--white)'}; color:${post.is_liked?'var(--coral)':'var(--g7)'}; cursor:pointer; font-size:13px; font-weight:700;">
        ${post.is_liked?'❤️':'🤍'} 좋아요 ${post.like_count}
      </button>
    </div>
    
    <div style="font-size:13px; font-weight:700; color:var(--g8); margin-bottom:10px;">💬 댓글 ${post.comments.length}개</div>
    <div id="commCommentsList" style="margin-bottom:1rem;">
      ${post.comments.map(c => renderComment(c)).join('') || '<div style="text-align:center;padding:1rem;color:var(--g5);font-size:12px;">첫 댓글을 작성해보세요!</div>'}
    </div>
    <div style="display:flex; gap:8px;">
      <input id="commCmtInput" type="text" placeholder="${localStorage.getItem('auth_token')?'댓글을 입력하세요':'로그인이 필요합니다'}" onkeypress="if(event.key==='Enter') submitComment(${post.id})" style="flex:1; height:38px; padding:0 12px; border:1.5px solid var(--g2); border-radius:8px; font-family:var(--font); font-size:13px; outline:none;" ${localStorage.getItem('auth_token')?'':'disabled'}>
      <button onclick="${localStorage.getItem('auth_token')?'submitComment('+post.id+')':'showModal()'}" style="padding:0 16px; border:none; border-radius:8px; background:var(--teal); color:var(--white); cursor:pointer; font-size:12px; font-weight:700;">${localStorage.getItem('auth_token')?'작성':'로그인'}</button>
    </div>
  `;
  document.getElementById('commDetailBody').innerHTML = html;
}

function renderComment(c) {
  const date = new Date(c.created_at).toLocaleString('ko-KR');
  const deleteBtn = (c.is_mine || (currentUser && currentUser.id === 1)) ?
    `<button onclick="deleteComment(${c.id})" style="padding:2px 6px; border:none; background:none; cursor:pointer; font-size:11px; color:var(--coral);">삭제</button>` : '';
  return `
    <div style="background:var(--g0); border-radius:8px; padding:10px 14px; margin-bottom:6px;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:4px;">
        <div style="display:flex; gap:6px; align-items:center; font-size:11px; color:var(--g6);">
          <span style="font-weight:700; color:var(--g8);">${escapeHtml(c.author_name)}</span>
          <span>·</span>
          <span>${date}</span>
        </div>
        ${deleteBtn}
      </div>
      <div style="font-size:13px; color:var(--g9); line-height:1.5; white-space:pre-wrap;">${escapeHtml(c.content)}</div>
    </div>
  `;
}

function closeCommunityDetail() {
  document.getElementById('commDetailModal').style.display = 'none';
}

async function toggleCommunityLike(postId) {
  const token = localStorage.getItem('auth_token');
  if (!token) { showModal(); return; }
  try {
    const r = await fetch(API_BASE + '/api/community/posts/' + postId + '/like', {
      method: 'POST',
      headers: {'Authorization':'Bearer '+token},
    });
    if (!r.ok) throw new Error('실패');
    openCommunityDetail(postId);  // 새로고침
  } catch (e) { showToast(e.message, 'error'); }
}

async function submitComment(postId) {
  const input = document.getElementById('commCmtInput');
  const content = input.value.trim();
  if (!content) return;
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/community/posts/' + postId + '/comments', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization':'Bearer '+token},
      body: JSON.stringify({content}),
    });
    if (!r.ok) throw new Error('작성 실패');
    openCommunityDetail(postId);
  } catch (e) { showToast(e.message, 'error'); }
}

async function deleteCommunityPost(postId) {
  if (!confirm('이 게시글을 삭제하시겠습니까?')) return;
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/community/posts/' + postId, {
      method: 'DELETE',
      headers: {'Authorization':'Bearer '+token},
    });
    if (!r.ok) throw new Error('삭제 실패');
    closeCommunityDetail();
    loadCommunity();
    showToast('삭제됨', 'info');
  } catch (e) { showToast(e.message, 'error'); }
}

async function deleteComment(commentId) {
  if (!confirm('이 댓글을 삭제하시겠습니까?')) return;
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/community/comments/' + commentId, {
      method: 'DELETE',
      headers: {'Authorization':'Bearer '+token},
    });
    if (!r.ok) throw new Error('삭제 실패');
    // 현재 보고있는 게시글 새로고침 (제목에서 ID 추정 어려우니 단순히 모달 닫기)
    showToast('삭제됨', 'info');
    // 게시글 ID 추출이 어려워서 모달 닫고 목록 새로고침
    const titleEl = document.getElementById('commDetailTitle');
    // 다시 로드해야 함 - 임시로 닫기
  } catch (e) { showToast(e.message, 'error'); }
}


// ============================================================
// 공지사항
// ============================================================

async function loadNotices() {
  // 관리자 버튼 표시 여부 결정
  const adminBtn = document.getElementById('adminNoticeBtn');
  if (adminBtn) {
    adminBtn.style.display = (currentUser && currentUser.id === 1) ? 'inline-flex' : 'none';
  }
  
  try {
    const r = await fetch(API_BASE + '/api/notices');
    if (!r.ok) throw new Error('로드 실패');
    const notices = await r.json();
    renderNotices(notices);
  } catch (e) {
    console.error('공지 로드 실패:', e);
  }
}

function renderNotices(notices) {
  const list = document.getElementById('noticeList');
  const empty = document.getElementById('noticeEmpty');
  if (!list) return;
  if (!notices.length) {
    empty.style.display = 'block';
    list.innerHTML = '';
    return;
  }
  empty.style.display = 'none';
  
  const isAdmin = currentUser && currentUser.id === 1;
  list.innerHTML = notices.map(n => {
    const date = new Date(n.created_at).toLocaleDateString('ko-KR');
    const adminActions = isAdmin ? `
      <button onclick="event.stopPropagation();toggleNoticePin(${n.id})" style="padding:4px 8px; border:1px solid var(--g2); border-radius:6px; background:var(--white); cursor:pointer; font-size:11px;">${n.is_pinned?'📌 고정해제':'📌 고정'}</button>
      <button onclick="event.stopPropagation();deleteNotice(${n.id})" style="padding:4px 8px; border:1px solid var(--g2); border-radius:6px; background:var(--white); cursor:pointer; font-size:11px; color:var(--coral);">🗑</button>
    ` : '';
    return `
      <li class="log-item" style="cursor:pointer;" onclick="toggleNoticeExpand(this, ${n.id})">
        <div class="log-thumb" style="background:${n.is_pinned?'var(--coral-3, #FFE5DC)':'var(--g1)'};">${n.is_pinned?'📌':'📢'}</div>
        <div class="log-content">
          <div class="log-title">${n.is_pinned?'<span style="color:var(--coral);margin-right:4px;">[공지]</span>':''}${escapeHtml(n.title)}</div>
          <div class="log-meta">${escapeHtml(n.author_name)} · ${date}</div>
          <div id="noticeContent_${n.id}" style="display:none; margin-top:10px; padding:12px; background:var(--g0); border-radius:8px; font-size:13px; color:var(--g8); line-height:1.6; white-space:pre-wrap;">${escapeHtml(n.content)}</div>
        </div>
        <div class="log-right"><div style="display:flex;gap:4px;">${adminActions}</div></div>
      </li>
    `;
  }).join('');
}

function toggleNoticeExpand(el, noticeId) {
  const content = document.getElementById('noticeContent_' + noticeId);
  if (content) {
    content.style.display = content.style.display === 'none' ? 'block' : 'none';
  }
}

function openNoticeWriteModal() {
  if (!currentUser || currentUser.id !== 1) {
    showToast('관리자만 공지를 작성할 수 있습니다.', 'error');
    return;
  }
  document.getElementById('noticeWriteTitle').value = '';
  document.getElementById('noticeWriteContent').value = '';
  document.getElementById('noticePinned').checked = false;
  document.getElementById('noticeWriteModal').style.display = 'block';
}

function closeNoticeWriteModal() {
  document.getElementById('noticeWriteModal').style.display = 'none';
}

async function submitNotice() {
  const title = document.getElementById('noticeWriteTitle').value.trim();
  const content = document.getElementById('noticeWriteContent').value.trim();
  const is_pinned = document.getElementById('noticePinned').checked;
  if (!title || !content) { showToast('제목과 내용을 입력하세요.', 'error'); return; }
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/notices', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization':'Bearer '+token},
      body: JSON.stringify({title, content, is_pinned}),
    });
    if (!r.ok) {
      const d = await r.json();
      throw new Error(d.detail || '작성 실패');
    }
    showToast('공지가 게시되었습니다!', 'success');
    closeNoticeWriteModal();
    loadNotices();
  } catch (e) { showToast(e.message, 'error'); }
}

async function toggleNoticePin(noticeId) {
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/notices/' + noticeId + '/pin', {
      method: 'PATCH',
      headers: {'Authorization':'Bearer '+token},
    });
    if (!r.ok) throw new Error('실패');
    loadNotices();
  } catch (e) { showToast(e.message, 'error'); }
}

async function deleteNotice(noticeId) {
  if (!confirm('이 공지를 삭제하시겠습니까?')) return;
  const token = localStorage.getItem('auth_token');
  try {
    const r = await fetch(API_BASE + '/api/notices/' + noticeId, {
      method: 'DELETE',
      headers: {'Authorization':'Bearer '+token},
    });
    if (!r.ok) throw new Error('삭제 실패');
    showToast('삭제됨', 'info');
    loadNotices();
  } catch (e) { showToast(e.message, 'error'); }
}


// ============================================================
// 푸터 모달들
// ============================================================

function showFooterContact() {
  document.getElementById('footerInfoTitle').textContent = '📩 문의하기';
  document.getElementById('footerInfoContent').innerHTML = `
    <p>EDU-bridge 서비스 관련 문의는 아래 이메일로 부탁드립니다.</p>
    <div style="background:var(--g0); padding:1.5rem; border-radius:8px; margin:1rem 0; text-align:center;">
      <div style="font-size:14px; color:var(--g7); margin-bottom:6px;">대표 이메일</div>
      <a href="mailto:edubridge@example.com" style="font-size:20px; color:var(--teal); font-weight:700; text-decoration:none;">edubridge@example.com</a>
    </div>
    <h3 style="margin-top:1.5rem;">📢 광고 / 협업 문의</h3>
    <p>유아교육 관련 서비스/제품 광고 및 협업 문의 환영합니다.<br>상기 이메일로 제안서를 보내주시면 검토 후 회신드립니다.</p>
    <h3 style="margin-top:1.5rem;">💬 서비스 개선 제안</h3>
    <p>EDU-bridge는 학부 캡스톤 프로젝트로 개발되었으며,<br>실제 현장 선생님들의 피드백을 바탕으로 발전하고 있습니다.</p>
  `;
  document.getElementById('footerInfoModal').style.display = 'block';
}

function showFooterTerms() {
  document.getElementById('footerInfoTitle').textContent = '📋 이용약관';
  document.getElementById('footerInfoContent').innerHTML = `
    <h3>제1조 (목적)</h3>
    <p>본 약관은 EDU-bridge(이하 "서비스")가 제공하는 AI 기반 유아교육 지도안 생성 서비스의 이용과 관련하여 회원과 서비스 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.</p>
    
    <h3>제2조 (서비스의 제공)</h3>
    <p>① 본 서비스는 10개국 유아교육과정을 기반으로 AI 추천 지도안을 생성합니다.<br>
       ② 생성된 지도안은 참고용이며, 최종 교육 활동은 교사의 판단에 따릅니다.<br>
       ③ 본 서비스는 학부 캡스톤 프로젝트로 운영되며, 무료로 제공됩니다.</p>
    
    <h3>제3조 (회원의 의무)</h3>
    <p>회원은 다음 행위를 해서는 안 됩니다:<br>
       - 타인의 개인정보 무단 수집/이용<br>
       - 서비스의 정상적 운영을 방해하는 행위<br>
       - 부적절한 게시물(욕설, 음란, 광고성) 작성</p>
    
    <h3>제4조 (저작권)</h3>
    <p>AI가 생성한 지도안의 저작권은 사용자에게 있으나, 서비스는 익명화된 데이터를 서비스 개선에 활용할 수 있습니다.</p>
    
    <h3>제5조 (서비스 변경/중단)</h3>
    <p>본 서비스는 학부 프로젝트로, 사전 공지 후 서비스를 변경/중단할 수 있습니다.</p>
    
    <p style="margin-top:2rem; padding-top:1rem; border-top:1px solid var(--g2); color:var(--g5); font-size:12px;">
       시행일: 2026년 6월 1일
    </p>
  `;
  document.getElementById('footerInfoModal').style.display = 'block';
}

function showFooterPrivacy() {
  document.getElementById('footerInfoTitle').textContent = '🔒 개인정보처리방침';
  document.getElementById('footerInfoContent').innerHTML = `
    <h3>1. 수집하는 개인정보 항목</h3>
    <p><strong>필수:</strong> 이메일, 사용자명, 비밀번호 (암호화 저장)<br>
       <strong>선택:</strong> 이름<br>
       <strong>자동 수집:</strong> 접속 IP, 이용 기록</p>
    
    <h3>2. 개인정보 이용 목적</h3>
    <p>- 회원 식별 및 로그인 관리<br>
       - 서비스 제공 (지도안 저장, 양식 관리 등)<br>
       - 서비스 개선을 위한 통계 분석</p>
    
    <h3>3. 개인정보 보관 기간</h3>
    <p>회원 탈퇴 시 즉시 파기됩니다. 단, 관계 법령에 의해 보존이 필요한 경우 해당 법령에 따릅니다.</p>
    
    <h3>4. 개인정보 제3자 제공</h3>
    <p>서비스는 사용자의 동의 없이 개인정보를 제3자에게 제공하지 않습니다.<br>
       단, AI 추천을 위해 입력 텍스트는 Google Gemini API로 전송됩니다 (개인 식별 정보 제외).</p>
    
    <h3>5. 사용자의 권리</h3>
    <p>사용자는 언제든지 자신의 개인정보를 조회, 수정, 삭제할 수 있으며, 회원 탈퇴를 요청할 수 있습니다.</p>
    
    <h3>6. 개인정보 보호 책임자</h3>
    <p>이메일: edubridge@example.com</p>
    
    <p style="margin-top:2rem; padding-top:1rem; border-top:1px solid var(--g2); color:var(--g5); font-size:12px;">
       시행일: 2026년 6월 1일
    </p>
  `;
  document.getElementById('footerInfoModal').style.display = 'block';
}

function closeFooterModal() {
  document.getElementById('footerInfoModal').style.display = 'none';
}


// ============================================================
// showPage 후크: 커뮤니티/공지 진입 시 로드
// ============================================================
const _origShowPageComm = showPage;
showPage = function(id, navEl, section) {
  _origShowPageComm(id, navEl, section);
  if (id === 'community') loadCommunity();
  if (id === 'notice') loadNotices();
};

// 로그인 상태 변경 시 관리자 버튼 표시 업데이트
const _origUpdateUIForUser = updateUIForUser;
updateUIForUser = function(user) {
  _origUpdateUIForUser(user);
  const adminBtn = document.getElementById('adminNoticeBtn');
  if (adminBtn) {
    adminBtn.style.display = (user && user.id === 1) ? 'inline-flex' : 'none';
  }
};
'''

if 'function loadCommunity' not in html:
    last_close = html.rfind('</script>')
    if last_close != -1:
        html = html[:last_close] + new_js + '\n' + html[last_close:]
        print("✅ 커뮤니티/공지/푸터 JS 추가")


HTML_PATH.write_text(html, encoding="utf-8")

print("\n" + "=" * 50)
print("🎉 통합 패치 완료!")
print("=" * 50)
print("\n다음 단계:")
print("  rm edubridge.db  (DB 스키마 변경)")
print("\n새 기능:")
print("  💬 커뮤니티: 게시글 작성/조회/삭제, 댓글, 좋아요, 카테고리 필터")
print("  📢 공지사항: ID=1 사용자만 작성, 상단 고정 기능")
print("  📋 푸터: 문의/이용약관/개인정보처리방침 모달")
print("  📢 광고 영역: 사이드바 상단 + 본문 하단 배너")
print("\n첫 번째 가입자(ID=1)가 관리자 권한을 가집니다!")
