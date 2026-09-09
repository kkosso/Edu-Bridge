# 초코소라빵 RAG 백엔드

10개국 유아교육과정 RAG 시스템의 백엔드.

## 폴더 구조

```
backend/
├── requirements.txt           # Python 패키지 목록
├── README.md                   # 이 파일
├── data/
│   ├── all_chunks.json        # ChromaDB 적재용 (163개 청크)
│   ├── all_countries.json     # 1차 가중치용 (10개국 메타+철학)
│   └── countries/             # 나라별 원본 JSON (참고용)
├── db/
│   ├── load_data.py           # ✅ 1단계: ChromaDB 적재
│   ├── quick_search_test.py   # ✅ 2단계: 적재 검증 (sanity check)
│   └── chroma_db/             # (자동 생성) 영속 벡터 DB
├── services/                  # (다음 단계)
│   ├── retriever.py           # 가중치 적용 검색 로직
│   ├── reranker.py            # LLM 재선별
│   ├── card_generator.py      # 카드 3장 생성
│   └── lesson_planner.py      # 지도안 생성
├── prompts/                   # (다음 단계) LLM 프롬프트 템플릿
└── main.py                    # (다음 단계) FastAPI 진입점
```

## 셋업 (최초 1회)

### 1. 가상환경 생성 + 패키지 설치

```bash
cd backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> ⚠ **주의**: `torch` 설치에 5분 정도 걸릴 수 있어요. CPU만 쓸 거라
> 굳이 CUDA 버전 받지 않아도 됩니다.

### 2. 데이터 파일 배치

`data/` 폴더에 다음 두 파일을 넣으세요:
- `all_chunks.json` (163개 청크)
- `all_countries.json` (10개국 메타+철학)

### 3. ChromaDB 적재

```bash
cd db
python load_data.py
```

**예상 소요 시간:**
- 첫 실행: 5~10분 (bge-m3 모델 약 2.3GB 다운로드 + 임베딩)
- 두 번째 실행부터: 1분 이내 (모델 캐싱됨)

성공하면 `db/chroma_db/` 폴더에 벡터 DB가 생성돼요.

### 4. 검색 sanity check

```bash
python quick_search_test.py
```

5개 테스트 쿼리에 대해 top-5 결과가 출력돼요. 다음과 같은 결과가 정상이에요:

- "원주민 문화와 자연을 연결한 야외 활동" → AUS(호주)가 상위
- "교육과 돌봄을 통합한 일상 속 학습" → FIN(핀란드)가 상위
- "100가지 언어로 자신의 생각을 표현하는 미술 활동" → ITA(이탈리아)가 상위

만약 **모든 쿼리에서 한 나라만 1등**이면 `weight_boost`나 청크 분포에 문제가 있는 거예요.
이때는 `merge_summary.md`의 "모니터링 포인트" 섹션 참고.

## 다음 단계

**[A] 적재 + 검증 ← 여기까지 완료하면 ✅ 데이터 준비 끝**

[B] 검색 함수 (`services/retriever.py`)
- 키워드 임베딩 → top-30 청크 검색
- `philosophy_weight` 적용해서 국가별 점수 집계
- `all_countries.json`의 `philosophy_summary`로 1차 가중치 검색
- 상위 5개국 후보 반환

[C] 보편적 지도안 양식 (`data/lesson_plan_template.md`)

[D] LLM 프롬프트 작성 (키워드 추출, 카드 생성, 지도안 생성)

[E] FastAPI 백엔드 (`main.py` + 3개 엔드포인트)

[F] Streamlit 프론트엔드

## 문제 해결

**Q: `load_data.py` 실행 시 메모리 부족 오류**
- bge-m3 모델은 약 2GB RAM을 사용해요. 다른 무거운 프로그램을 끄세요.
- 그래도 안 되면 `model_name="BAAI/bge-small-en-v1.5"` 같은 작은 모델로 변경 (한국어 성능은 다소 떨어짐).

**Q: 다운로드가 너무 느려요**
- 한국에서 HuggingFace 다운로드가 느릴 때가 있어요. 첫 실행 시 30분까지 걸릴 수 있으니 인내심을 가지고 기다리세요.
- 한 번 받으면 `~/.cache/huggingface/` 에 캐시되어 재사용돼요.

**Q: 적재된 DB를 다시 만들고 싶어요**
- `db/chroma_db/` 폴더를 통째로 지우고 `load_data.py`를 재실행하세요.
- (스크립트가 기존 컬렉션을 자동으로 덮어쓰지만, 완전 초기화하려면 폴더 삭제가 안전.)
