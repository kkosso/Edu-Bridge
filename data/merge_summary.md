# 10개국 통합 병합 검증 리포트

## 1. 작업 개요

- **작업 일자**: 2026-05-02
- **팀**: 초코소라빵 (AI학과 3학년 4명)
- **작업 내용**: 10개국 개별 JSON 파일을 RAG 시스템에서 사용할 수 있는 통합 데이터로 병합
- **결과 파일**: `all_countries.json`, `all_chunks.json`

## 2. 통합 통계

| 항목 | 수치 |
|------|------|
| 총 국가 수 | 10 |
| 총 청크 수 | 163 |
| 핵심철학(`is_core_philosophy=true`) 청크 수 | 88 |
| 일반 청크 수 | 75 |
| 총 differentiators 수 | 60 (10개국 × 6개) |
| 가중치 부스트 (모든 나라 동일) | 1.5 |

## 3. 국가별 청크 분포

| 국가 | 코드 | 총 청크 | 핵심철학 청크 | 비율 |
|------|------|---------|--------------|------|
| 핀란드 | FIN | 27 | 11 | 41% |
| 대한민국 | KOR | 20 | 10 | 50% |
| 싱가포르 | SGP | 20 | 11 | 55% |
| 스웨덴 | SWE | 20 | 8 | 40% |
| 이탈리아 | ITA | 14 | 10 | 71% |
| 뉴질랜드 | NZL | 14 | 9 | 64% |
| 호주 | AUS | 12 | 7 | 58% |
| 독일 | GER | 12 | 8 | 67% |
| 일본 | JPN | 12 | 6 | 50% |
| 영국 | GBR | 12 | 8 | 67% |

**분포 균형 평가**: 청크 수 12~27개 범위로 다소 차이가 있으나, RAG 검색 시 가중치 정규화로 보완 가능. 한 나라가 청크 수만으로 독식하지 않도록 주의 필요.

## 4. 생성된 두 파일의 역할

### 4.1. `all_countries.json` (RAG 1차 가중치 검색용)

**구조**:
```
{
  "metadata": { 프로젝트 메타정보 },
  "countries": [
    {
      "country": "핀란드",
      "country_code": "FIN",
      "framework_name": "...",
      "framework_metadata": { 발행기관, 규정ID, PDF출처 등 },
      "core_philosophy": {
        "philosophy_summary": "...",        ← ★ 임베딩되어 1차 검색에 사용됨
        "identity_keywords": [...],          ← LLM 프롬프트에 주입
        "differentiators": [
          {
            "name": "...",
            "description": "...",
            "source_quote": "...",            ← 발표 방어용 원문 인용
            "source_location": "..."
          }
        ],
        "weight_boost": 1.5
      },
      "chunk_count": 27,
      "core_philosophy_chunk_count": 11
    },
    ...
  ]
}
```

**용도**:
- RAG 검색 STAGE C (국가별 점수 집계) 단계에서 활용
- 각 나라의 `philosophy_summary`를 별도로 임베딩하여, 사용자 쿼리와의 유사도를 국가별 점수에 가산
- LLM이 카드/지도안 생성 시 `differentiators`와 `identity_keywords`를 프롬프트에 주입

**용도 코드 예시**:
```python
import json

with open('all_countries.json') as f:
    countries_data = json.load(f)

# 1차 가중치 검색: philosophy_summary 임베딩
for country in countries_data['countries']:
    summary = country['core_philosophy']['philosophy_summary']
    similarity = compute_similarity(query, summary)
    country_score = base_score + beta * similarity

# 카드 생성 시 LLM 프롬프트에 차별점 주입
prompt = f"이 나라의 핵심 차별점은: {country['core_philosophy']['differentiators']}"
```

### 4.2. `all_chunks.json` (ChromaDB 적재용)

**구조**:
```
{
  "metadata": { 메타정보 },
  "chunks": [
    {
      "id": "FIN_001",
      "country": "핀란드",                    ← 국가 정보가 각 청크에 포함됨
      "country_code": "FIN",
      "framework_name": "...",
      "category": "...",
      "chunk_text": "...",                    ← ★ 임베딩될 본문
      "pedagogical_keywords": [...],
      "is_core_philosophy": true,             ← ★ 가중치 적용 플래그
      "philosophy_weight": 1.5,               ← ★ 점수에 곱할 가중치
      "source_location": "..."
    },
    ...
  ]
}
```

**용도**:
- RAG 검색 STAGE B (벡터 검색) 단계의 핵심 데이터
- 163개 청크 모두를 ChromaDB에 한 번에 적재
- 검색 결과에 `is_core_philosophy=true`인 청크는 점수 × `philosophy_weight` 적용

**적재 코드 예시**:
```python
import json
import chromadb

with open('all_chunks.json') as f:
    chunks_data = json.load(f)

client = chromadb.Client()
collection = client.create_collection("ecec_chunks")

for chunk in chunks_data['chunks']:
    collection.add(
        ids=[chunk['id']],
        documents=[chunk['chunk_text']],
        metadatas=[{
            'country': chunk['country'],
            'country_code': chunk['country_code'],
            'category': chunk['category'],
            'is_core_philosophy': chunk['is_core_philosophy'],
            'philosophy_weight': chunk['philosophy_weight'],
            'source_location': chunk['source_location']
        }]
    )
# 끝. 163개 청크 적재 완료
```

## 5. 두 파일의 관계 (가중치 메커니즘)

검색 시 두 가지 가중치가 동시에 작동합니다.

```
사용자 쿼리 → 임베딩
        ↓
  ┌─────────────────────────────────┐
  │  1차: all_countries.json 사용     │
  │  각 나라 philosophy_summary와     │
  │  유사도 계산 → 국가별 가산점      │
  └─────────────────────────────────┘
        ↓
  ┌─────────────────────────────────┐
  │  2차: all_chunks.json 사용        │
  │  ChromaDB에서 청크별 검색,        │
  │  is_core_philosophy=true 청크는   │
  │  score × 1.5 부스트              │
  └─────────────────────────────────┘
        ↓
  국가별 점수 합산 → 상위 5개국 → LLM 재선별 → 3개국
```

## 6. 데이터 품질 검증 결과

| 검증 항목 | 결과 |
|-----------|------|
| 모든 파일 표준 스키마 정합성 | ✓ 10개국 모두 통과 |
| 청크 ID 중복 검사 | ✓ 163개 모두 고유 |
| 모든 청크에 `source_location` 존재 | ✓ 통과 |
| 모든 differentiators에 `source_quote` 존재 | ✓ 60개 모두 통과 |
| 가중치 일관성 (`weight_boost=1.5`) | ✓ 10개국 동일 |
| JSON 파싱 가능 여부 | ✓ 두 파일 모두 통과 |

## 7. 알려진 한계 및 모니터링 포인트

1. **`is_core_philosophy` 비율 차이**: 40~71% 범위. 비율이 높은 나라(이탈리아 71%, 영국·독일 67%)가 검색에서 우위를 점할 가능성이 있어 사용자 테스트 시 모니터링 필요. 한 나라가 결과를 독식하면 weight_boost를 1.3~1.4로 낮추거나, 비율 높은 나라의 일부 청크를 false로 재분류 검토.

2. **청크 수 차이 (12~27개)**: 핀란드(27개)와 한국(20개)이 다른 나라보다 많음. 검색 시 점수 정규화(평균 또는 max 기반)를 적용하여 청크 수 차이로 인한 편향 방지 필요.

3. **`philosophy_summary` 길이 일관성**: 나라별로 요약문 길이가 다를 수 있음. 임베딩 결과에 영향 줄 수 있어 향후 점검 필요.

## 8. 다음 단계 (이번주 ~ 다음주 수요일)

### 즉시 진행
1. ChromaDB 적재 스크립트 작성 (`load_data.py`)
   - `all_chunks.json` 읽어서 ChromaDB에 적재
   - 임베딩 모델: bge-m3 또는 text-embedding-3-small
2. 검색 함수 구현 (`retriever.py`)
   - 키워드 임베딩 → top-30 청크 검색
   - 국가별 점수 집계 + `philosophy_weight` 적용
   - `philosophy_summary` 별도 검색 추가 (1차 가중치)
3. LLM 프롬프트 작성
   - 키워드 추출용 (이미지+텍스트 → 교육 키워드)
   - 카드 생성용 (3개국 × 카드 1장씩)
   - 지도안 생성용 (선택 국가 청크 + 보편 템플릿)

### 다음주 화요일까지
4. FastAPI 백엔드 (3개 엔드포인트)
   - `/api/extract-keywords`
   - `/api/recommend-countries`
   - `/api/generate-lesson-plan`
5. Streamlit 프론트엔드 (간단한 데모용)
6. 테스트 쿼리 5~10개로 검색 결과 점검
7. weight_boost 튜닝 (필요시)

### 다음주 수요일
8. 사용자 테스트 (유아교육과 학생들)
9. 피드백 수집 및 개선

## 9. 파일 사용 가이드

| 파일 | 사용처 | 수정 빈도 |
|------|--------|-----------|
| 나라별 JSON (10개) | 팀원 개별 수정/검토용 | 자주 |
| `all_countries.json` | 1차 가중치 검색, LLM 프롬프트 | 나라별 파일 수정 후 재생성 |
| `all_chunks.json` | ChromaDB 적재 | 나라별 파일 수정 후 재생성 |

**중요**: 나라별 파일을 수정하면 두 통합 파일을 다시 생성해야 합니다. 향후 자동 재생성 스크립트(`merge.py`)를 작성하면 편할 거예요.
