"""
prompt_keyword_extractor.py
====================
STAGE A: 사용자 입력(교구 사진 + 텍스트 + 연령/시간)에서 RAG 검색용 키워드 추출.

사용 모델: Gemini 2.0 Flash (멀티모달, 이미지 입력 지원, 무료 tier)

입력:
    - image_path: 교구/활동 환경 사진 경로 (선택)
    - text: 사용자가 자유롭게 입력한 활동 설명
    - age: 만 N세 (예: 4)
    - duration: 활동 시간 분 (예: 40)

출력:
    {
        "keywords": ["자연물 탐색", "오감 활동", ...],  # RAG 검색용 키워드 5~10개
        "search_query": "유아가 자연물을 오감으로 탐색하는 미술 활동",  # retriever에 넣을 통합 쿼리
        "detected_objects": ["솔방울", "나뭇잎", "돌멩이"],  # 이미지에서 인식된 오브젝트
        "activity_type": "탐색·표현 활동",  # 활동 유형 분류
        "suggested_areas": ["자연탐구", "예술경험"]  # 누리과정 5개 영역 중
    }

이 출력의 search_query가 retriever.search()의 입력이 됨.
"""

# ============================================================
# 시스템 프롬프트 (Gemini에 주입)
# ============================================================
SYSTEM_PROMPT = """\
당신은 한국 유아교육 전문가입니다. 유치원 교사가 수업을 준비하기 위해 입력한 교구 사진과 활동 설명을 보고,
유아교육과정 데이터베이스(RAG)에서 검색할 키워드를 추출하는 역할을 합니다.

당신의 작업은 다음 4가지입니다:

1. **이미지 분석**: 교구 사진이 있다면 어떤 오브젝트(자연물, 도구, 자료 등)가 보이는지 식별
2. **활동 의도 파악**: 텍스트와 이미지를 종합해 교사가 하려는 활동의 핵심 의도 파악
3. **검색 키워드 추출**: 유아교육과정에서 검색하기 좋은 한국어 키워드 5~10개 생성
4. **통합 쿼리 작성**: 한 문장으로 활동의 핵심을 표현 (RAG 검색에 들어갈 쿼리)

### 키워드 추출 규칙

- 너무 추상적인 단어 X (예: "교육", "활동", "놀이")
- 너무 구체적인 단어 X (예: "솔방울 3개")
- 적정 추상도 ⭕ (예: "자연물 탐색", "오감 활동", "다양한 매체 표현")
- 누리과정 5개 영역(신체운동·건강, 의사소통, 사회관계, 예술경험, 자연탐구)을 의식하되 강제하지 않음
- 교육철학 키워드도 포함 (예: "유아 주도", "비구조화 자료", "협력 활동")

### 출력 형식 (JSON)

반드시 아래 JSON 형식으로만 답하세요. 다른 설명 추가 금지.

```json
{
  "detected_objects": ["오브젝트1", "오브젝트2"],
  "activity_type": "활동 유형 (예: 탐색·표현, 협동 놀이, 문제 해결)",
  "keywords": ["키워드1", "키워드2", "..."],
  "search_query": "한 문장으로 표현된 활동 의도",
  "suggested_areas": ["누리과정 영역1", "누리과정 영역2"]
}
```
"""

# ============================================================
# 사용자 메시지 템플릿
# ============================================================
USER_MESSAGE_TEMPLATE = """\
[교사 입력]

활동 설명: {text}
대상 연령: 만 {age}세
활동 시간: {duration}분
{image_note}

위 입력을 바탕으로 키워드를 추출해주세요.
"""

# ============================================================
# 호출 함수
# ============================================================
def build_prompt(text: str, age: int, duration: int, has_image: bool = False) -> dict:
    """
    Gemini API에 보낼 프롬프트 구조 반환.

    Args:
        text: 사용자가 입력한 활동 설명
        age: 만 나이
        duration: 활동 시간(분)
        has_image: 이미지 첨부 여부

    Returns:
        {"system": "...", "user": "..."} - API 호출 시 사용
    """
    image_note = "교구 사진: 첨부됨 (이미지 참고하여 오브젝트 식별)" if has_image \
        else "교구 사진: 없음 (텍스트 정보만으로 추론)"

    user_message = USER_MESSAGE_TEMPLATE.format(
        text=text,
        age=age,
        duration=duration,
        image_note=image_note,
    )

    return {
        "system": SYSTEM_PROMPT,
        "user": user_message,
    }


# ============================================================
# Gemini API 호출 예시 (실제 구현은 keyword_extractor.py에서)
# ============================================================
EXAMPLE_USAGE = """
# keyword_extractor.py에서 이렇게 사용:

import google.generativeai as genai
from PIL import Image
import json
from prompts.prompt_keyword_extractor import build_prompt

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash-exp")

def extract_keywords(text: str, age: int, duration: int, image_path: str = None):
    prompt = build_prompt(text, age, duration, has_image=bool(image_path))
    
    contents = [prompt["system"], prompt["user"]]
    if image_path:
        contents.append(Image.open(image_path))
    
    response = model.generate_content(contents)
    
    # JSON 파싱
    result_text = response.text.strip()
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    
    return json.loads(result_text.strip())
"""

# ============================================================
# 테스트용 예시 입력
# ============================================================
TEST_INPUTS = [
    {
        "text": "솔방울이랑 나뭇잎 모아왔는데 아이들이 만지고 그림 그리는 활동 하고 싶어요",
        "age": 4,
        "duration": 40,
        "image_path": None,
        "expected_keywords": ["자연물 탐색", "오감 활동", "다양한 매체 표현", "예술경험"],
    },
    {
        "text": "큰 박스를 가져왔는데 아이들이 자유롭게 가지고 놀게 해주고 싶어요",
        "age": 5,
        "duration": 60,
        "image_path": None,
        "expected_keywords": ["비구조화 자료", "유아 주도 놀이", "상상 놀이", "협동"],
    },
    {
        "text": "텃밭에서 채소 키우기 활동을 통해 자연을 사랑하는 마음 기르고 싶어요",
        "age": 5,
        "duration": 50,
        "image_path": None,
        "expected_keywords": ["텃밭 활동", "생명 존중", "지속가능성", "자연 탐구"],
    },
]
