#!/usr/bin/env python3
"""
patch_admin_seed.py
====================
서버 시작 시 ID=1 관리자 계정을 자동으로 생성하는 startup hook 추가

- 계정: minseosong5@gmail.com
- 비밀번호: sms040812
- DB가 비어있을 때만 자동 생성 (이미 사용자가 있으면 스킵)
"""
from pathlib import Path

MAIN_PATH = Path("main.py")
main_code = MAIN_PATH.read_text(encoding="utf-8")
backup = MAIN_PATH.with_suffix(".py.bak_admin_seed")
backup.write_text(main_code, encoding="utf-8")
print(f"✅ 백업: {backup}")

# startup hook 추가
seed_code = '''

@app.on_event("startup")
def seed_admin_account():
    """ID=1 관리자 계정 자동 시드 (DB가 비어있을 때만)"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        existing = db.query(User).first()
        if existing:
            # 이미 사용자가 있으면 건너뜀
            return

        import bcrypt
        import hashlib
        admin_password = "sms040812"
        # bcrypt 72바이트 제한 회피 (SHA256 pre-hash)
        pwd_bytes = hashlib.sha256(admin_password.encode()).digest()
        hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode()

        admin = User(
            email="minseosong5@gmail.com",
            username="minseo",
            full_name="송민서",
            password_hash=hashed,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✅ 관리자 계정 자동 생성됨 (ID={admin.id}): minseosong5@gmail.com")
    except Exception as e:
        print(f"⚠️ 관리자 계정 시드 실패: {e}")
    finally:
        db.close()
'''

# 이미 시드 함수가 있는지 확인
if "seed_admin_account" not in main_code:
    # @app.get("/api/health") 직전에 삽입
    if '\n@app.get("/api/health")' in main_code:
        main_code = main_code.replace(
            '\n@app.get("/api/health")',
            seed_code + '\n@app.get("/api/health")'
        )
        MAIN_PATH.write_text(main_code, encoding="utf-8")
        print("✅ main.py: 관리자 시드 함수 추가")
    else:
        # health check가 없으면 파일 끝에 추가
        main_code += seed_code
        MAIN_PATH.write_text(main_code, encoding="utf-8")
        print("✅ main.py: 관리자 시드 함수 추가 (파일 끝)")
else:
    print("ℹ️  관리자 시드 함수 이미 존재")

print("\n🎉 패치 완료!")
print("\n다음 단계:")
print("  1. rm edubridge.db  (DB 비우기)")
print("  2. 서버 자동 재시작 시 다음과 같이 출력됨:")
print("     ✅ 관리자 계정 자동 생성됨 (ID=1): minseosong5@gmail.com")
print("\n로그인 정보:")
print("  📧 Email: minseosong5@gmail.com")
print("  🔑 Password: sms040812")
print("  👑 권한: 관리자 (공지 작성 가능)")
print("  🎁 무료체험: 2주")
