"""
backend/database.py
====================
SQLAlchemy 데이터베이스 모델 및 세션 관리
 
실배포 시 PostgreSQL로 교체 예정 (현재는 SQLite)
"""
 
import hashlib
import base64
import bcrypt
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
 
# ============================================================
# 데이터베이스 설정
# ============================================================
 
# 개발용: SQLite (backend/edubridge.db)
DATABASE_URL = "sqlite:///./edubridge.db"
 
# 실배포용 (나중에 활성화):
# DATABASE_URL = "postgresql://user:password@localhost/edubridge"
 
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # True로 설정하면 SQL 쿼리 출력
)
 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
 
 
# ============================================================
# 모델
# ============================================================
 
class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"
 
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # 추가 정보
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 구독 관련
    subscription_tier = Column(String(20), default='free')
    subscription_started_at = Column(DateTime, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    template_download_count = Column(Integer, default=0)
    last_download_reset_at = Column(DateTime, default=datetime.utcnow)
    lesson_generation_count = Column(Integer, default=0)
    
    # 관계
    saved_lessons = relationship("SavedLesson", back_populates="user", cascade="all, delete-orphan")
    
    def verify_password(self, plain_password: str) -> bool:
        """비밀번호 검증 (SHA256 pre-hash + bcrypt)"""
        pre_hashed = base64.b64encode(
            hashlib.sha256(plain_password.encode("utf-8")).digest()
        )  # bytes, 항상 44바이트 → 72 미만
        return bcrypt.checkpw(pre_hashed, self.hashed_password.encode("utf-8"))
    
    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호 해싱 (SHA256 pre-hash + bcrypt)"""
        pre_hashed = base64.b64encode(
            hashlib.sha256(password.encode("utf-8")).digest()
        )  # bytes, 항상 44바이트 → 72 미만
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pre_hashed, salt)
        return hashed.decode("utf-8")
 
 
class SavedLesson(Base):
    """저장된 지도안 (즐겨찾기 기능)"""
    __tablename__ = "saved_lessons"
 
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 지도안 정보
    title = Column(String(200), nullable=False)
    search_query = Column(String(500), nullable=False)
    country_code = Column(String(10), nullable=False)
    age = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    
    # 카드 데이터 (JSON 문자열로 저장)
    card_data = Column(Text, nullable=True)
    
    # 지도안 전체 Markdown
    lesson_markdown = Column(Text, nullable=False)
    
    # 즐겨찾기 여부
    is_favorite = Column(Boolean, default=False)
    
    # 메모
    notes = Column(Text, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    user = relationship("User", back_populates="saved_lessons")


class UserTemplate(Base):
    """사용자가 업로드한 지도안 양식"""
    __tablename__ = "user_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    template_name = Column(String(200), nullable=False)
    original_filename = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)

    # 파싱된 섹션 정보 (JSON 문자열)
    sections_json = Column(Text, nullable=True)
    structure_type = Column(String(50), nullable=True)  # "table" or "paragraph"
    analysis_json = Column(Text, nullable=True)  # Gemini 심층 분석 결과 (셀 위치별 의미)

    created_at = Column(DateTime, default=datetime.utcnow)



class AppliedTemplate(Base):
    """저장된 지도안에 양식을 적용한 이력 (스크랩)"""
    __tablename__ = "applied_templates"

    id = Column(Integer, primary_key=True, index=True)
    saved_lesson_id = Column(Integer, ForeignKey("saved_lessons.id"), nullable=False)
    user_template_id = Column(Integer, ForeignKey("user_templates.id"), nullable=True)
    template_name = Column(String(200), nullable=False)
    # fills_json: [{"table_idx":0, "row":0, "col":1, "content":"...", "label":"단원"}, ...]
    fills_json = Column(Text, nullable=False)
    personal_info_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)



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


# ============================================================
# 데이터베이스 초기화
# ============================================================
 
def init_db():
    """데이터베이스 테이블 생성 + 기존 DB 컬럼 마이그레이션"""
    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 테이블 생성 완료")

    # 기존 DB에 새 컬럼이 없으면 ALTER TABLE로 추가 (SQLite 호환)
    from sqlalchemy import text
    migrations = [
        ("users", "subscription_tier",        "ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'free'"),
        ("users", "subscription_started_at",  "ALTER TABLE users ADD COLUMN subscription_started_at DATETIME"),
        ("users", "subscription_expires_at",  "ALTER TABLE users ADD COLUMN subscription_expires_at DATETIME"),
        ("users", "template_download_count",  "ALTER TABLE users ADD COLUMN template_download_count INTEGER DEFAULT 0"),
        ("users", "last_download_reset_at",   "ALTER TABLE users ADD COLUMN last_download_reset_at DATETIME"),
        ("users", "lesson_generation_count",  "ALTER TABLE users ADD COLUMN lesson_generation_count INTEGER DEFAULT 0"),
        ("users", "full_name",                "ALTER TABLE users ADD COLUMN full_name TEXT"),
    ]
    with engine.connect() as conn:
        for table, col, sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  ✅ 마이그레이션: {table}.{col} 추가됨")
            except Exception:
                pass  # 이미 존재하면 무시
 
 
def get_db():
    """FastAPI 의존성 주입용 DB 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
 
 
# ============================================================
# 유틸리티 함수
# ============================================================
 
def create_user(
    db,
    email: str,
    username: str,
    password: str,
    full_name: Optional[str] = None
) -> User:
    """새 사용자 생성"""
    hashed_password = User.hash_password(password)
    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
 
 
def get_user_by_email(db, email: str) -> Optional[User]:
    """이메일로 사용자 조회"""
    return db.query(User).filter(User.email == email).first()
 
 
def get_user_by_username(db, username: str) -> Optional[User]:
    """사용자명으로 사용자 조회"""
    return db.query(User).filter(User.username == username).first()
 
 
def authenticate_user(db, email: str, password: str) -> Optional[User]:
    """사용자 인증"""
    user = get_user_by_email(db, email)
    if not user or not user.verify_password(password):
        return None
    return user

