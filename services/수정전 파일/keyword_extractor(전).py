"""
services/keyword_extractor.py
====================
STAGE A: 사용자 입력 → search_query 추출

사용 모델: Gemini 2.0 Flash (멀티모달)

사용 예:
    from services.keyword_extractor import extract_keywords

    result = extract_keywords(
        text="솔방울이랑 나뭇잎으로 미술 활동 하고 싶어요",
        age=4,
        duration=40,
        image_path="/path/to/image.jpg",  # 선택
    )
    print(result["search_query"])  # → retriever.search()에 넣을 쿼리
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# prompts 폴더를 import 경로에 추가
SERVICES_DIR = Path(__file__).parent
BACKEND_ROOT = SERVICES_DIR.parent
sys.path.insert(0, str(BACKEND_ROOT))

from prompts.prompt_keyword_extractor import build_prompt


# ============================================================
# 설정
# ============================================================
load_dotenv(BACKEND_ROOT / ".env")
GEMINI_MODEL = "gemini-2.0-flash-exp"

_model = None  # lazy init


def _get_model():
    """Gemini 모델 lazy 초기화 (재호출 시 같은 인스턴스 재사용)"""
    global _model
    if _model is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 환경변수가 없습니다. "
                "backend/.env 파일에 GEMINI_API_KEY=... 를 추가하세요."
            )
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(GEMINI_MODEL)
    return _model


# ============================================================
# JSON 파싱 헬퍼
# ============================================================
def _strip_code_fence(text: str) -> str:
    """LLM이 ```json ... ``` 으로 감쌌을 때 제거"""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ============================================================
# 메인 함수
# ============================================================
def extract_keywords(
    text: str,
    age: int,
    duration: int,
    image_path: Optional[str] = None,
) -> dict:
    """
    사용자 입력에서 RAG 검색용 키워드/쿼리 추출.

    Args:
        text: 사용자가 입력한 활동 설명
        age: 만 나이 (예: 4)
        duration: 활동 시간 분 (예: 40)
        image_path: 교구 사진 경로 (선택)

    Returns:
        {
            "detected_objects": [...],
            "activity_type": "...",
            "keywords": [...],
            "search_query": "...",       ← retriever.search()의 입력
            "suggested_areas": [...],
        }

    Raises:
        RuntimeError: API 키 누락
        json.JSONDecodeError: LLM 응답이 JSON 형식이 아님
        FileNotFoundError: image_path가 존재하지 않음
    """
    has_image = bool(image_path)
    if has_image and not Path(image_path).exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    prompt = build_prompt(text=text, age=age, duration=duration, has_image=has_image)

    # Gemini는 system/user를 따로 받지 않으므로 합쳐서 보냄
    contents = [prompt["system"] + "\n\n" + prompt["user"]]
    if has_image:
        contents.append(Image.open(image_path))

    model = _get_model()
    response = model.generate_content(
        contents,
        generation_config={
            "temperature": 0.3,           # 키워드 추출은 일관성 우선
            "response_mime_type": "application/json",  # JSON 강제
        },
    )

    result_text = _strip_code_fence(response.text)
    return json.loads(result_text)


# ============================================================
# 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    test_cases = [
        {
            "text": "솔방울이랑 나뭇잎 모아왔는데 아이들이 만지고 그림 그리는 활동 하고 싶어요",
            "age": 4,
            "duration": 40,
        },
        {
            "text": "큰 박스를 가져왔는데 아이들이 자유롭게 가지고 놀게 해주고 싶어요",
            "age": 5,
            "duration": 60,
        },
        {
            "text": "텃밭에서 채소 키우기 활동을 통해 자연을 사랑하는 마음 기르고 싶어요",
            "age": 5,
            "duration": 50,
        },
    ]

    print("=" * 70)
    print("keyword_extractor.py 단독 테스트")
    print("=" * 70)

    for i, tc in enumerate(test_cases, 1):
        print(f"\n[{i}] 입력: {tc['text']}")
        print(f"    연령={tc['age']}세, 시간={tc['duration']}분")
        try:
            result = extract_keywords(**tc)
            print(f"    ✓ 활동 유형: {result.get('activity_type')}")
            print(f"    ✓ 키워드: {', '.join(result.get('keywords', [])[:6])}")
            print(f"    ✓ search_query: {result.get('search_query')}")
            print(f"    ✓ 누리과정 영역: {', '.join(result.get('suggested_areas', []))}")
        except Exception as e:
            print(f"    ✗ 실패: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("✅ 테스트 완료")
    print("=" * 70)
