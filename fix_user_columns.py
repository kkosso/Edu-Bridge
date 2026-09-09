#!/usr/bin/env python3
"""
fix_user_columns.py
====================
patch_subscription_profile.py에서 User 클래스 컬럼 추가가 실패한 것을 수동 보정
"""
from pathlib import Path
import re

DB_PATH = Path("database.py")
db_code = DB_PATH.read_text(encoding="utf-8")
backup = DB_PATH.with_suffix(".py.bak_fix_user")
backup.write_text(db_code, encoding="utf-8")
print(f"✅ 백업: {backup}")

# 추가해야 할 컬럼들
required_columns = [
    "subscription_tier",
    "subscription_started_at",
    "subscription_expires_at",
    "template_download_count",
    "last_download_reset_at",
    "lesson_generation_count",
]

# 어떤 컬럼이 누락됐는지 체크
missing = [c for c in required_columns if c not in db_code]
print(f"📋 누락된 컬럼: {missing}")

if not missing:
    print("✅ 모든 컬럼이 이미 존재합니다.")
    exit(0)

# User 클래스 찾기
user_class_pattern = re.compile(
    r'(class User\(Base\):.*?)(\n\nclass |\n# =)',
    re.DOTALL
)
m = user_class_pattern.search(db_code)

if not m:
    print("❌ User 클래스를 찾지 못했습니다.")
    exit(1)

user_class_content = m.group(1)
after_user = m.group(2)

# 새 컬럼들 정의
new_columns = """
    # 구독 관련 (자동 추가)
    subscription_tier = Column(String(20), default='free')
    subscription_started_at = Column(DateTime, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    template_download_count = Column(Integer, default=0)
    last_download_reset_at = Column(DateTime, default=datetime.utcnow)
    lesson_generation_count = Column(Integer, default=0)
"""

# 이미 일부 컬럼이 있을 수도 있으므로 누락된 것만 추가
columns_to_add = ""
column_defs = {
    "subscription_tier": "    subscription_tier = Column(String(20), default='free')",
    "subscription_started_at": "    subscription_started_at = Column(DateTime, nullable=True)",
    "subscription_expires_at": "    subscription_expires_at = Column(DateTime, nullable=True)",
    "template_download_count": "    template_download_count = Column(Integer, default=0)",
    "last_download_reset_at": "    last_download_reset_at = Column(DateTime, default=datetime.utcnow)",
    "lesson_generation_count": "    lesson_generation_count = Column(Integer, default=0)",
}

new_lines = []
for col in required_columns:
    if col in missing:
        new_lines.append(column_defs[col])

new_columns_text = "\n    # 구독 관련 (자동 추가)\n" + "\n".join(new_lines) + "\n"

# User 클래스 끝부분에 삽입
new_user_class = user_class_content.rstrip() + new_columns_text

db_code = db_code.replace(user_class_content, new_user_class)
DB_PATH.write_text(db_code, encoding="utf-8")

print(f"✅ User 클래스에 {len(new_lines)}개 컬럼 추가 완료")
print("\n다음 단계:")
print("  rm edubridge.db")
print("  서버 재시작 후 회원가입")
