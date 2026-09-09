# LLM 모델 사용 정리

## 📊 한눈에 보는 모델 배치

| 단계 | 파일 | 사용 모델 | 모델 ID | 호출 방식 | 비용 |
|------|------|----------|---------|----------|------|
| **STAGE A** 키워드 추출 | `prompt_keyword_extractor.py` | **Gemini 2.0 Flash** | `gemini-2.0-flash-exp` | 멀티모달(이미지+텍스트) | 무료 tier |
| **STAGE D** 카드 생성 | `prompt_card_generator.py` | **Claude Haiku 4.5** | `claude-haiku-4-5-20251001` | 텍스트만 | 유료 (저렴) |
| **STAGE F** 지도안 생성 | `prompt_lesson_planner.py` | **Claude Haiku 4.5** | `claude-haiku-4-5-20251001` | 텍스트만 | 유료 (저렴) |

## 🎯 모델 선택 근거

### STAGE A: Gemini 2.0 Flash (키워드 추출)

**왜 이 모델?**
- ✅ **멀티모달 강함**: 교구 사진 + 텍스트를 동시에 처리. Claude/GPT보다 이미지 인식 정확도 우수.
- ✅ **무료 tier 충분**: 분당 15 req, 일 1,500 req. 학부 프로젝트엔 충분.
- ✅ **빠름**: 평균 1~2초 응답. 사용자 대기 시간 짧음.
- ✅ **JSON 출력 안정적**: structured output 기능으로 형식 깨질 일 적음.

**언제 다른 모델로 바꿀까?**
- 무료 tier 한도 초과 → Gemini 2.0 Flash 유료 또는 GPT-4o-mini로 변경
- 멀티모달 필요 없으면 (텍스트만) → Claude Haiku 4.5로 통일 가능

### STAGE D, F: Claude Haiku 4.5 (카드 + 지도안)

**왜 이 모델?**
- ✅ **한국어 자연스러움**: GPT-4o-mini보다 한국어 톤이 자연스러움. 유아교육 도메인 표현도 적절.
- ✅ **긴 한국어 문서 안정적**: 지도안 A4 2장 분량 출력해도 흐름 유지.
- ✅ **청크 활용 능력 우수**: 여러 청크를 종합해서 새로운 콘텐츠 생성하는 능력 강함.
- ✅ **JSON 출력 안정적**: 카드 생성 시 형식 안정.
- ✅ **빠름**: Claude Haiku는 Sonnet보다 2~3배 빠르고 가격은 1/5.

**왜 카드와 지도안을 같은 모델로?**
- 톤·스타일 일관성. 사용자가 카드 보고 선택했는데 지도안 톤이 다르면 위화감.
- API 키 1개로 관리 (4명 팀에서 환경변수 관리 단순).

**언제 다른 모델로 바꿀까?**
- 지도안 품질이 부족하면 → Claude Sonnet 4.5로 업그레이드 (3배 비싸지만 더 정교).
- API 비용 0원이 필수면 → Gemini 2.0 Flash로 변경 가능.

## 💰 예상 비용 (4명 팀, 3일 테스트 기준)

### 가정
- 사용자 테스트 100회 진행
- 1회당: 키워드 추출 1회 + 카드 생성 1회 + 지도안 생성 1회

### Gemini 2.0 Flash (STAGE A)
- 무료 tier 내에서 100회 모두 처리 가능
- **비용: $0**

### Claude Haiku 4.5 (STAGE D, F)
- 카드 생성: 입력 ~3000 토큰, 출력 ~1500 토큰 → 회당 약 $0.003
- 지도안 생성: 입력 ~5000 토큰, 출력 ~3000 토큰 → 회당 약 $0.006
- 100회 × ($0.003 + $0.006) = **약 $0.90 (약 1,200원)**

### 총 예상 비용
- 학부 프로젝트 전체: **약 1,200원** (충분히 감당 가능)

## 🔑 API 키 발급 가이드

### 1. Gemini API 키 (무료)
```
1. https://aistudio.google.com/apikey 접속
2. Google 계정 로그인
3. "Create API key" 클릭
4. 프로젝트 선택 또는 새로 만들기
5. 발급된 키 복사
```

### 2. Anthropic API 키 (Claude)
```
1. https://console.anthropic.com 접속
2. 회원가입 (신용카드 등록 필요, $5 무료 크레딧 제공)
3. Settings → API Keys → "Create Key"
4. 발급된 키 복사
```

## ⚙️ 환경 변수 설정

`backend/` 폴더에 `.env` 파일을 만들고:

```bash
GEMINI_API_KEY=AIza...your_gemini_key
ANTHROPIC_API_KEY=sk-ant-...your_claude_key
```

`.gitignore`에 `.env` 반드시 추가:
```
.env
venv/
__pycache__/
db/chroma_db/
```

Python에서 사용:
```python
import os
from dotenv import load_dotenv

load_dotenv()  # backend/ 디렉토리에서 실행

api_key = os.environ["GEMINI_API_KEY"]
```

`requirements.txt`에 추가 필요:
```
python-dotenv>=1.0.0
google-generativeai>=0.8.0
anthropic>=0.40.0
```

## 📁 LLM 관련 파일 구조

```
backend/
├── prompts/                            ← 프롬프트 정의 (이번에 만든 것)
│   ├── prompt_keyword_extractor.py     # STAGE A 프롬프트
│   ├── prompt_card_generator.py        # STAGE D 프롬프트
│   └── prompt_lesson_planner.py        # STAGE F 프롬프트
│
├── services/                           ← LLM 호출 함수 (다음 단계 F에서 만들 것)
│   ├── retriever.py                    # ✅ 완료
│   ├── keyword_extractor.py            # ⏳ 다음
│   ├── card_generator.py               # ⏳ 다음
│   └── lesson_planner.py               # ⏳ 다음
│
└── data/
    └── lesson_plan_template.md         # ✅ 완료 (지도안 템플릿)
```

## 🧪 프롬프트 테스트 방법

각 프롬프트 파일은 **프롬프트 정의만** 포함하고 실제 API 호출은 다음 단계(F)의 `services/` 파일에서 합니다.

이렇게 분리하는 이유:
- ✅ 프롬프트만 수정하면 모델 변경/튜닝 가능
- ✅ 테스트 시 mock 데이터로 프롬프트만 따로 검증 가능
- ✅ 4명 팀 분업 시 프롬프트 담당과 호출 담당 분리

## 📝 모델 변경이 필요할 때

### Claude Haiku → 다른 모델로 바꾸는 법

`services/card_generator.py` 또는 `services/lesson_planner.py`에서:

```python
# 기존
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    ...
)

# Claude Sonnet으로 (더 정교)
response = client.messages.create(
    model="claude-sonnet-4-5",
    ...
)

# OpenAI GPT-4o-mini로 (다른 SDK 필요)
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": prompt["user"]}
    ],
)
```

### Gemini → 다른 모델로 바꾸는 법

이미지 처리가 필요하면 GPT-4o (vision 지원) 또는 Claude Haiku 4.5 (vision 지원) 사용 가능.

## 🚨 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| `RateLimitError` (Gemini) | 무료 tier 한도 초과 (분당 15회) | 1분 대기 후 재시도 또는 유료 전환 |
| `AuthenticationError` | API 키 오류 | `.env` 파일 확인, 키 재발급 |
| Claude 응답이 코드블록(```)으로 감싸져 있음 | Claude 기본 동작 | 프롬프트 파일의 파싱 코드가 자동 제거 |
| 한국어 톤이 어색함 | 모델 한계 | Claude Haiku → Sonnet으로 업그레이드 검토 |
| JSON 파싱 실패 | LLM이 자유 텍스트로 답변 | 프롬프트의 "JSON으로만 답하세요" 강조 추가 |

## 📋 다음 단계 (F: LLM 호출 함수)

이 프롬프트 정의들을 실제로 호출하는 Python 함수 3개를 만들어야 합니다:

1. `services/keyword_extractor.py` - Gemini API 호출 + 이미지 처리 + JSON 파싱
2. `services/card_generator.py` - Claude API 호출 + 후보국 정보 조립 + JSON 파싱
3. `services/lesson_planner.py` - Claude API 호출 + 청크 정보 조립 + Markdown 출력

각 파일은 **단순한 함수 1~2개만 노출**해서 main.py(FastAPI)에서 쉽게 호출하도록 합니다.
