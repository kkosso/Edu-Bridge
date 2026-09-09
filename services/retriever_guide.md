# `retriever.py` 사용 가이드

## 1. 어떤 파일인가

RAG 시스템의 **STAGE B-C-D**를 담당하는 핵심 검색 함수.

```
사용자 쿼리
    ↓
STAGE B (청크 검색): top-30 청크 가져오기 + philosophy_weight 적용
    ↓
STAGE C (국가 집계): 같은 나라 청크 점수를 max + avg 혼합으로 합산
    ↓
STAGE D (1차 가중치): philosophy_summary와 쿼리 직접 비교 후 가산
    ↓
상위 5개국 + 매칭 청크 정보 반환
```

## 2. 실행 방법

### 2.1. 폴더 구조 확인

```
backend/
├── data/
│   ├── all_chunks.json
│   └── all_countries.json
├── db/
│   └── chroma_db/          ← load_data.py 실행 후 생성됨
└── services/
    └── retriever.py        ← 이 파일
```

### 2.2. 실행

```bash
cd backend/services
python retriever.py
```

5개 테스트 쿼리에 대해 상위 5개국 결과가 출력돼요.

## 3. 출력 해석 방법

### 출력 예시

```
======================================================================
쿼리: 유아 주도 자유놀이를 충분히 보장하는 활동
======================================================================

[1] 대한민국 (KOR)  →  최종 점수: 0.567
    청크 점수: 0.452  (max=0.617, avg=0.288, n=4)
    철학 요약 유사도: 0.382
    매칭 청크 (상위 3개):
      [★] KOR_004 (weighted=0.617, raw=0.411) | 놀이 중심 철학 / 놀이를 통한 배움
      [★] KOR_003 (weighted=0.583, raw=0.388) | 유아 중심 철학 / 주체적 존재로서의 유아
      [ ] KOR_010 (weighted=0.411, raw=0.411) | 신체운동·건강 영역 / 기본 역량
```

### 각 숫자의 의미

| 항목 | 의미 |
|------|------|
| **최종 점수** | `chunk_score + 0.3 × summary_score`. 이 값으로 국가 순위 결정 |
| **청크 점수** | `0.6 × max + 0.4 × avg`. 청크 단위 매칭의 강도 |
| **max** | 그 나라에서 가장 잘 매칭된 청크의 가중치 적용 점수 |
| **avg** | 그 나라 매칭 청크들의 평균 점수 |
| **n** | top-30 안에 들어간 그 나라 청크 수 |
| **철학 요약 유사도** | philosophy_summary와 쿼리의 직접 유사도 (1차 가중치) |
| **★** | 핵심철학 청크 (philosophy_weight=1.5 적용됨) |
| **weighted** | raw 점수에 가중치 적용한 최종 청크 점수 |
| **raw** | ChromaDB에서 나온 순수 임베딩 유사도 |

### 정상 작동 신호

- ✅ 상위 5개국에 **다양한 나라**가 나옴 (한 나라가 5위까지 독식 X)
- ✅ 쿼리에 따라 **다른 나라가 1등**으로 나옴
- ✅ `chunk_score`와 `summary_score`가 **둘 다 영향**을 미침
- ✅ 핵심철학 청크(★)가 `weighted` 점수에서 raw보다 1.5배 높음

### 비정상 신호

- ⚠️ 모든 쿼리에서 한 나라(예: 한국)만 1등 → 가중치 조정 필요
- ⚠️ summary_score는 높은데 chunk_score는 낮음 → 청크와 요약문 사이 일관성 문제
- ⚠️ 상위 5개국 점수가 거의 같음 → 변별력 부족, gamma 키울 필요

## 4. 가중치 튜닝 매뉴얼

### 튜닝 가능한 4개 파라미터

`retriever.py` 상단에 정의되어 있어요.

```python
TOP_K_CHUNKS = 30          # ChromaDB에서 가져올 청크 수
ALPHA = 0.6                # max 비중
BETA = 0.4                 # avg 비중 (alpha + beta = 1)
GAMMA = 0.3                # philosophy_summary 비중
```

### 각 파라미터의 효과

#### `ALPHA` vs `BETA` (청크 집계)

- **ALPHA 높이기 (0.7~0.8)**: 한 청크가 강하게 매칭되면 그 나라 우세. 강한 차별점 강조.
- **BETA 높이기 (0.5~0.6)**: 여러 청크가 골고루 매칭되어야 우세. 종합적 매칭.

**기본값 0.6/0.4** 추천. 학부 프로젝트에선 변별력 위해 ALPHA 높여도 OK.

#### `GAMMA` (1차 가중치 비중)

- **GAMMA = 0**: philosophy_summary 무시 (순수 청크 검색)
- **GAMMA = 0.3 (기본값)**: 적당히 영향
- **GAMMA = 0.5 이상**: summary가 결과를 좌우. 청크 수 적은 나라도 우세 가능
- **GAMMA = 1.0 이상**: summary만으로 결정. 청크 검색이 무의미해짐

**문제별 처방:**

| 증상 | 원인 | 처방 |
|------|------|------|
| 한 나라가 너무 자주 1등 | 청크 수 차이로 avg가 편향 | ALPHA ↑ 0.7~0.8 |
| 차별점 강한 나라가 안 잡힘 | 핵심철학 청크 부스트 부족 | (이건 weight_boost를 1.5→1.7로) |
| philosophy_summary 무시됨 | gamma 너무 작음 | GAMMA ↑ 0.4~0.5 |
| 결과가 너무 들쭉날쭉 | 검색 범위 좁음 | TOP_K_CHUNKS ↑ 50 |

#### `philosophy_weight` (코드 외부 - all_chunks.json)

`is_core_philosophy=true`인 청크의 가중치. 기본 1.5.

**언제 조정?**
- 1.5 → 1.7: 핵심철학 청크가 충분히 우세하지 않을 때
- 1.5 → 1.3: 핵심철학 청크가 너무 독식할 때

⚠️ 주의: 이걸 바꾸면 `all_chunks.json`을 수정하고 ChromaDB 재적재 필요. 보통 ALPHA/BETA/GAMMA로 먼저 조정.

## 5. 다음 단계: LLM 재선별 (reranker.py)

retriever.py가 5개국을 추천했지만, 실제 사용자에게 보여줄 건 **3개국**이에요.

### 왜 5→3으로 줄이나?

retriever.py는 **임베딩 기반**이라 의미적 유사도만 봐요. 하지만 실제로는 다음을 추가 고려해야 해요:

- **차별성**: 5개국 중 비슷한 나라끼리 묶이면 다양성 떨어짐
- **활동 적합성**: 단순 의미가 비슷해도 실제 수업에 못 쓰는 청크가 있을 수 있음
- **사용자 입력 맥락**: 연령, 시간, 교구 사진 등을 종합 고려

이걸 LLM이 한 번 더 판단해주는 게 reranker.py.

```
retriever.py → 5개국 추천
    ↓
reranker.py (LLM 판단) → 3개국 최종 선택 + 차별화 이유 생성
    ↓
card_generator.py → 카드 3장 생성
```

## 6. 트러블슈팅

**Q: `chromadb.errors.InvalidCollectionException: Collection ecec_chunks does not exist.`**
- `load_data.py`를 먼저 실행해서 ChromaDB를 적재해야 해요.

**Q: `ModuleNotFoundError: No module named 'sentence_transformers'`**
- `pip install sentence-transformers`로 설치.

**Q: 검색이 너무 느려요 (10초 이상)**
- bge-m3는 처음 임베딩할 때만 느려요. 두 번째 쿼리부터는 빠릅니다.
- 그래도 느리면 `device="cuda"` (GPU 있으면) 또는 `bge-small-en-v1.5` (작은 모델)로 변경.

**Q: ChromaDB가 telemetry 에러 메시지를 출력해요**
- 무시해도 돼요. ChromaDB의 알려진 버그이고 검색 결과에는 영향 없어요.
- 끄고 싶으면 `os.environ["ANONYMIZED_TELEMETRY"] = "False"` 추가.

## 7. 코드 구조 요약

```python
class Retriever:
    def __init__(self): ...                          # 초기화
    def _search_chunks(self, query): ...             # STAGE 1-2
    def _aggregate_by_country(self, chunks): ...     # STAGE 3
    def _summary_similarity(self, query): ...        # STAGE 4 (1차 가중치)
    def search(self, query): ...                     # 통합 진입점
```

`search()`가 외부에서 호출하는 유일한 메서드예요. 나머지는 내부용.
