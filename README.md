# Edu-Bridge 초코소라빵 RAG 백엔드
10개국 유아교육과정 RAG 시스템의 백엔드.

폴더 구조
**backend/
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
└── main.py                    # (다음 단계) FastAPI 진입점**
셋업 (최초 1회)

1. 가상환경 생성 + 패키지 설치
cd backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
⚠ 주의: torch 설치에 5분 정도 걸릴 수 있어요. CPU만 쓸 거라 굳이 CUDA 버전 받지 않아도 됩니다.
2. 데이터 파일 배치
data/ 폴더에 다음 두 파일을 넣으세요:

all_chunks.json (163개 청크)
all_countries.json (10개국 메타+철학)

3. ChromaDB 적재
cd db
python load_data.py
예상 소요 시간:

첫 실행: 5~10분 (bge-m3 모델 약 2.3GB 다운로드 + 임베딩)
두 번째 실행부터: 1분 이내 (모델 캐싱됨)
성공하면 db/chroma_db/ 폴더에 벡터 DB가 생성돼요.

4. 검색 sanity check
