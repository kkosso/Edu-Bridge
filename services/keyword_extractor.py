"""
services/keyword_extractor.py
====================
STAGE A: 사용자 입력 → search_query 추출

사용 SDK: google-genai (구 google-generativeai는 deprecated)
사용 모델: gemini-2.5-flash (멀티모달, 빠름, 무료 tier)

사용 예:
    from services.keyword_extractor import extract_keywords

    result = extract_keywords(
        text="솔방울이랑 나뭇잎으로 미술 활동 하고 싶어요",
        age=4,
        duration=40,
        image_path="/path/to/image.jpg",  # 선택
    )
    print(result["search_query"])
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

SERVICES_DIR = Path(__file__).parent
BACKEND_ROOT = SERVICES_DIR.parent
sys.path.insert(0, str(BACKEND_ROOT))

from prompts.prompt_keyword_extractor import build_prompt


# ============================================================
# 설정
# ============================================================
load_dotenv(BACKEND_ROOT / ".env")
GEMINI_MODEL = "gemini-2.5-flash"

_client = None


def _get_client():
    """google-genai Client lazy 초기화."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 환경변수가 없습니다. "
                "backend/.env 파일에 GEMINI_API_KEY=... 를 추가하세요."
            )
        _client = genai.Client(api_key=api_key)
    return _client


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

    Returns:
        {
            "detected_objects": [...],
            "activity_type": "...",
            "keywords": [...],
            "search_query": "...",        ← retriever.search()의 입력
            "suggested_areas": [...],
        }
    """
    has_image = bool(image_path)
    if has_image and not Path(image_path).exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    prompt = build_prompt(text=text, age=age, duration=duration, has_image=has_image)

    # Gemini는 system을 따로 받을 수도 있고, 합쳐 보낼 수도 있음.
    # 새 SDK는 GenerateContentConfig.system_instruction 으로 system을 분리 지정 가능.
    contents = [prompt["user"]]
    if has_image:
        contents.append(Image.open(image_path))

    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=prompt["system"],
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )

    return json.loads(_strip_code_fence(response.text))


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
    print("keyword_extractor.py 단독 테스트 (google-genai SDK)")
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
