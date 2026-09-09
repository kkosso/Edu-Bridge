"""
backend/auth.py
====================
JWT 토큰 기반 인증 시스템

- 토큰 생성 (로그인 성공 시)
- 토큰 검증 (보호된 API 접근 시)
- 현재 사용자 추출
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db, User

# ============================================================
# 설정
# ============================================================

# ⚠️ 실배포 시 .env 파일로 이동 필요!
SECRET_KEY = "your-secret-key-change-this-in-production-2026"  # 실배포 시 변경 필수
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7일

security = HTTPBearer()


# ============================================================
# 토큰 생성
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ============================================================
# 토큰 검증 및 사용자 추출
# ============================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    보호된 API에서 현재 로그인된 사용자 추출
    
    사용법:
        @app.get("/api/me")
        def get_me(current_user: User = Depends(get_current_user)):
            return {"email": current_user.email}
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 올바르지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    선택적 인증 (로그인 안 해도 됨)
    
    사용법:
        @app.get("/api/public-but-personalized")
        def endpoint(current_user: Optional[User] = Depends(get_optional_user)):
            if current_user:
                return f"안녕하세요 {current_user.username}님!"
            else:
                return "안녕하세요 게스트님!"
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    except JWTError:
        return None
