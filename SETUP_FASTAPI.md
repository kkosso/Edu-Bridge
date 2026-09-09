# FastAPI + EDU-bridge HTML 셋업 가이드

## 📁 파일 배치

```
backend/
├── .env                            ← GEMINI_API_KEY (기존)
├── main.py                         ← 🆕 FastAPI 백엔드
├── data/
│   ├── all_chunks.json
│   ├── all_countries.json
│   └── lesson_plan_template.md
├── db/
│   ├── load_data.py
│   └── chroma_db/
├── prompts/                        ← 기존
├── services/                       ← 기존 (수정 없음)
│   ├── retriever.py
│   ├── keyword_extractor.py
│   ├── card_generator.py
│   └── lesson_planner.py
├── static/                         ← 🆕 새 폴더
│   └── edu-bridge-full.html        ← 🆕 수정된 HTML
└── venv/
```

## 🔧 1. 패키지 설치

```bash
cd backend
source venv/bin/activate

# Streamlit은 더 이상 필요 없음 (제거 가능)
pip uninstall streamlit -y

# FastAPI + Uvicorn 설치
pip install fastapi "uvicorn[standard]" python-multipart
```

`python-multipart`는 파일 업로드(이미지)를 받기 위해 필요합니다.

## 🔧 2. 파일 배치

1. `main.py` 를 `backend/` 바로 아래에 배치
2. `backend/static/` 폴더 생성:
   ```bash
   mkdir -p backend/static
   ```
3. `edu-bridge-full.html` 을 `backend/static/` 안에 배치

확인:
```bash
ls backend/main.py backend/static/edu-bridge-full.html
```
→ 두 파일 모두 보이면 OK.

## 🚀 3. 실행

```bash
cd backend
uvicorn main:app --reload --port 8000
```

서버 로그에 다음과 같이 나타나야 합니다:
```
============================================================
⚙️  EDU-bridge 백엔드 워밍업 중...
✅ 백엔드 준비 완료. 서버 가동.
============================================================
INFO:     Uvicorn running on http://127.0.0.1:8000
```

워밍업이 약 5~10초 걸립니다 (Retriever + 임베딩 모델 로드).

## 🌐 4. 브라우저에서 접속

```
http://localhost:8000
```

→ EDU-bridge 페이지가 뜹니다. **사이드바에서 "Play-Scanner" 메뉴 클릭** 하면 추천 시스템 사용 가능.

## 🧪 테스트 시나리오

### 첫 테스트 (텍스트만)
1. 좌측 사이드바에서 **"Play-Scanner"** 클릭
2. 텍스트 입력: `종이컵으로 쌓기 놀이`
3. 만 4세 / 40분
4. **"✨ 글로벌 교육 철학 매칭 시작"** 클릭
5. 약 25초 대기 → 카드 3장 표시
6. 카드 하나의 **"이 카드로 지도안 만들기 →"** 클릭
7. 약 25초 대기 → 지도안 표시
8. **"📥 다운로드"** 또는 **"📋 복사"** 동작 확인

### 두 번째 테스트 (이미지 + 텍스트)
1. 사진 업로드
2. 텍스트 추가
3. 동일하게 진행

## 🛠️ 주요 API 엔드포인트

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | `/` | EDU-bridge 메인 페이지 |
| POST | `/api/extract` | 키워드 추출 (Stage A) |
| POST | `/api/cards` | 카드 3장 생성 (Stage B-D + E) |
| POST | `/api/lesson` | 지도안 생성 (Stage F) |
| GET | `/api/health` | 서버 상태 확인 |
| GET | `/docs` | Swagger UI (API 테스트) |

## 🐛 트러블슈팅

### "ModuleNotFoundError: No module named 'fastapi'"
→ `pip install fastapi "uvicorn[standard]" python-multipart`

### "404 Not Found - edu-bridge-full.html"
→ `backend/static/edu-bridge-full.html` 위치 확인

### "Uvicorn 실행했는데 워밍업이 멈춤"
→ ChromaDB 적재 안 됐을 수도 있음. `cd db && python load_data.py` 한번 실행

### 카드 생성 시 "503 UNAVAILABLE"
→ Gemini 일시 과부하. card_generator는 자동 재시도 됨. 그래도 실패 시 "매칭 시작" 한번 더 클릭

### 첫 호출이 30초 이상
→ 정상. Retriever 캐싱 안 된 첫 호출은 임베딩까지 다 함. 두 번째부턴 빠름.

### "Failed to fetch" / CORS 에러
→ `main.py`에 CORS 미들웨어가 이미 있음. 같은 origin (localhost:8000)이면 문제 없어야 함

### 한국어가 깨져 보임
→ HTML의 `<meta charset="UTF-8">`이 있는지 확인 (있음, 정상)

## 📋 발표 데모 시 체크 포인트

- [ ] 백엔드 미리 실행해두기 (워밍업 끝난 상태)
- [ ] 첫 호출 캐시를 위해 데모 전 1번은 돌려두기
- [ ] 노트북 화면에 Chrome 띄워두고 시연
- [ ] 백업: 만약 중간에 503 에러 나면 침착하게 한 번 더 클릭

## 🎁 추가 팁

### 다른 페이지(Dashboard, Kids-note) 동작은?
→ 팀원의 Mock 그대로 살아있음. 백엔드 미연결 상태로 디자인만 보여주는 용도. 발표 시 "메인 기능 외에도 이런 확장 페이지를 계획 중" 이라고 언급 가능.

### API 테스트만 하고 싶을 때
브라우저에서 `http://localhost:8000/docs` 열면 Swagger UI에서 직접 API 호출 가능.

### 발표 직전 한 번 더 워밍업하기
서버 끄지 말고 그대로 두면 메모리 캐시가 살아있어서 첫 호출도 빠릅니다.
