"""
retriever.py
====================
RAG 검색 핵심 로직.

작동 흐름:
1. 사용자 쿼리를 임베딩
2. ChromaDB에서 top-30 청크 검색 (raw similarity)
3. 청크별 philosophy_weight 적용 (1.5 부스트)
4. 국가별 점수 집계 (max + avg 혼합)
5. all_countries.json의 philosophy_summary와 1차 가중치 검색
6. 최종 국가 점수에 1차 가중치 가산
7. 상위 5개국 + 매칭 청크 정보 반환

이 결과가 LLM 재선별(reranker.py)의 입력이 됨.

사용 예시:
    from retriever import Retriever
    retriever = Retriever()
    result = retriever.search("유아 주도 자유놀이를 충분히 보장하는 활동")
    for country in result['top_countries']:
        print(f"{country['country']}: {country['final_score']:.3f}")
"""

import json
from pathlib import Path
from collections import defaultdict
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import numpy as np


# ============================================================
# 설정
# ============================================================
SCRIPT_DIR = Path(__file__).parent          # backend/services/
BACKEND_ROOT = SCRIPT_DIR.parent            # backend/
DATA_PATH = BACKEND_ROOT / "data" / "all_countries.json"
CHROMA_PATH = BACKEND_ROOT / "db" / "chroma_db"
COLLECTION_NAME = "ecec_chunks"
EMBEDDING_MODEL = "BAAI/bge-m3"

# 가중치 하이퍼파라미터 (튜닝 대상)
TOP_K_CHUNKS = 30          # ChromaDB에서 가져올 청크 수
TOP_K_COUNTRIES = 3        # 최종 반환할 국가 수 (3개국 카드 정책)
ALPHA = 0.6                # 청크 점수 집계: max 가중치
BETA = 0.4                 # 청크 점수 집계: avg 가중치 (alpha + beta = 1)
GAMMA = 0.2                # philosophy_summary 1차 가중치 비중 (0.3 → 0.2 로 하향)
                           # summary만으로 1등이 되는 현상을 줄이기 위함.
                           # 국가 최종 점수 = (alpha*max + beta*avg) + gamma * summary_sim
CLIP_NEGATIVE = True       # raw_score(임베딩 유사도)가 음수면 0으로 클리핑
                           # 음수 청크가 평균을 깎아서 정상 매칭 나라 순위가 밀리는 현상 방지
EXCLUDE_ZERO_CHUNK_COUNTRIES = True
                           # top-K 안에 청크가 1개도 없는 나라는 후보 풀에서 제외
                           # (summary_sim만으로 1등 되는 버그 방지)


class Retriever:
    """가중치 적용 RAG 검색기"""

    def __init__(
        self,
        chroma_path: Path = CHROMA_PATH,
        countries_path: Path = DATA_PATH,
        collection_name: str = COLLECTION_NAME,
        embedding_model: str = EMBEDDING_MODEL,
    ):
        """검색기 초기화. ChromaDB 연결 + 임베딩 모델 로드 + 국가 메타 로드."""
        print(f"⏳ Retriever 초기화 중...")

        # 1. ChromaDB 연결
        self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model,
            device="cpu",
        )
        self.collection = self.chroma_client.get_collection(
            name=collection_name,
            embedding_function=self.embed_fn,
        )
        print(f"  ✓ ChromaDB 연결 ({self.collection.count()}개 청크)")

        # 2. 임베딩 모델 별도 로드 (philosophy_summary 직접 임베딩용)
        self.embed_model = SentenceTransformer(embedding_model, device="cpu")
        print(f"  ✓ 임베딩 모델 로드")

        # 3. all_countries.json 로드 + philosophy_summary 사전 임베딩
        with open(countries_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.countries = data["countries"]

        # 각 나라의 philosophy_summary를 미리 임베딩 (검색마다 재계산 방지)
        summaries = [c["core_philosophy"]["philosophy_summary"] for c in self.countries]
        self.summary_embeddings = self.embed_model.encode(
            summaries, normalize_embeddings=True
        )
        print(f"  ✓ 10개국 philosophy_summary 임베딩 완료")
        print(f"✅ Retriever 준비 완료\n")

    # ============================================================
    # STAGE 1-2. 청크 단위 검색 + 가중치 적용
    # ============================================================
    def _search_chunks(self, query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
        """
        ChromaDB에서 top-K 청크를 검색하고 가중치를 적용한다.

        Returns:
            [
                {
                    'chunk_id': 'FIN_006',
                    'country_code': 'FIN',
                    'country': '핀란드',
                    'category': '...',
                    'raw_score': 0.452,
                    'is_core_philosophy': True,
                    'weighted_score': 0.678,  # raw_score * philosophy_weight
                    ...
                },
                ...
            ]
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        chunks = []
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            document = results["documents"][0][i]

            # ChromaDB의 distance를 similarity로 변환 (cosine 거리 기준)
            raw_score = 1 - distance
            # 음수 클리핑 (선택): 의미적으로 무관/반대인 청크가 평균을 깎는 것 방지
            if CLIP_NEGATIVE and raw_score < 0:
                raw_score = 0.0

            # 가중치 적용
            weight = float(metadata["philosophy_weight"])
            weighted_score = raw_score * weight

            chunks.append({
                "chunk_id": chunk_id,
                "country_code": metadata["country_code"],
                "country": metadata["country"],
                "category": metadata["category"],
                "chunk_text": document,
                "is_core_philosophy": metadata["is_core_philosophy"],
                "philosophy_weight": weight,
                "raw_score": raw_score,
                "weighted_score": weighted_score,
                "source_location": metadata["source_location"],
                "pedagogical_keywords": metadata["pedagogical_keywords"],
            })

        return chunks

    # ============================================================
    # STAGE 3. 국가별 점수 집계
    # ============================================================
    def _aggregate_by_country(
        self, chunks: list[dict], alpha: float = ALPHA, beta: float = BETA
    ) -> dict:
        """
        청크 점수를 국가별로 집계한다.

        국가 점수 = alpha * max(청크 점수) + beta * avg(청크 점수)

        - max만 쓰면: 한 청크가 강하게 매칭되면 그 나라 1등 (다양성 부족)
        - avg만 쓰면: 청크가 많은 나라가 유리 (편향)
        - 혼합: 둘의 균형

        Returns:
            {
                'FIN': {
                    'country': '핀란드',
                    'chunk_score': 0.567,
                    'max_score': 0.678,
                    'avg_score': 0.456,
                    'matched_chunks': [...],
                    'chunk_count': 4,
                },
                ...
            }
        """
        country_chunks = defaultdict(list)
        for chunk in chunks:
            country_chunks[chunk["country_code"]].append(chunk)

        aggregated = {}
        for code, c_list in country_chunks.items():
            scores = [c["weighted_score"] for c in c_list]
            max_s = max(scores)
            avg_s = sum(scores) / len(scores)

            aggregated[code] = {
                "country": c_list[0]["country"],
                "country_code": code,
                "chunk_score": alpha * max_s + beta * avg_s,
                "max_score": max_s,
                "avg_score": avg_s,
                "matched_chunks": sorted(
                    c_list, key=lambda x: x["weighted_score"], reverse=True
                ),
                "chunk_count": len(c_list),
            }

        return aggregated

    # ============================================================
    # STAGE 4. philosophy_summary 1차 가중치
    # ============================================================
    def _summary_similarity(self, query: str) -> dict[str, float]:
        """
        쿼리와 각 나라의 philosophy_summary 간 유사도를 계산한다.

        Returns:
            {'FIN': 0.412, 'KOR': 0.234, ...}
        """
        # 쿼리 임베딩
        query_emb = self.embed_model.encode([query], normalize_embeddings=True)[0]

        # 코사인 유사도 (정규화된 벡터의 내적 = 코사인)
        similarities = self.summary_embeddings @ query_emb

        return {
            self.countries[i]["country_code"]: float(similarities[i])
            for i in range(len(self.countries))
        }

    # ============================================================
    # STAGE 5. 최종 점수 계산 + 상위 N개국 반환
    # ============================================================
    def search(
        self,
        query: str,
        top_k_countries: int = TOP_K_COUNTRIES,
        gamma: float = GAMMA,
    ) -> dict:
        """
        통합 검색: 쿼리 → top-N 국가 후보 + 매칭 청크 정보

        Args:
            query: 사용자 쿼리 (LLM이 추출한 키워드 합본)
            top_k_countries: 반환할 국가 수
            gamma: philosophy_summary 가중치 비중

        Returns:
            {
                'query': '...',
                'top_countries': [
                    {
                        'country': '핀란드',
                        'country_code': 'FIN',
                        'final_score': 0.567,
                        'chunk_score': 0.452,
                        'summary_score': 0.382,
                        'matched_chunks': [상위 청크들],
                        ...
                    },
                    ...
                ]
            }
        """
        # STAGE 1-2: 청크 검색 + 가중치
        chunks = self._search_chunks(query)

        # STAGE 3: 국가별 집계
        country_scores = self._aggregate_by_country(chunks)

        # STAGE 4: philosophy_summary 1차 가중치
        summary_sims = self._summary_similarity(query)

        # STAGE 5: 최종 점수 = chunk_score + gamma * summary_sim
        all_country_codes = {c["country_code"] for c in self.countries}
        for code in all_country_codes:
            if code not in country_scores:
                if EXCLUDE_ZERO_CHUNK_COUNTRIES:
                    # 청크 매칭이 0개인 나라는 후보 풀에서 완전히 제외
                    # (summary_sim만으로 1등이 되는 버그를 차단)
                    continue
                # 청크가 top-K에 없는 나라는 chunk_score=0 으로 채움 (옛 동작)
                country_info = next(c for c in self.countries if c["country_code"] == code)
                country_scores[code] = {
                    "country": country_info["country"],
                    "country_code": code,
                    "chunk_score": 0.0,
                    "max_score": 0.0,
                    "avg_score": 0.0,
                    "matched_chunks": [],
                    "chunk_count": 0,
                }

            country_scores[code]["summary_score"] = summary_sims.get(code, 0.0)
            country_scores[code]["final_score"] = (
                country_scores[code]["chunk_score"]
                + gamma * country_scores[code]["summary_score"]
            )

        # 상위 N개국 정렬
        sorted_countries = sorted(
            country_scores.values(),
            key=lambda x: x["final_score"],
            reverse=True,
        )[:top_k_countries]

        return {
            "query": query,
            "top_countries": sorted_countries,
            "all_countries_scored": country_scores,  # 디버깅용
        }


# ============================================================
# 테스트 실행
# ============================================================
def print_search_result(result: dict, top_chunks_per_country: int = 3):
    """검색 결과를 보기 좋게 출력한다."""
    print(f"\n{'=' * 70}")
    print(f"쿼리: {result['query']}")
    print(f"{'=' * 70}")

    for rank, country in enumerate(result["top_countries"], 1):
        print(
            f"\n[{rank}] {country['country']} ({country['country_code']})"
            f"  →  최종 점수: {country['final_score']:.3f}"
        )
        print(
            f"    청크 점수: {country['chunk_score']:.3f}  "
            f"(max={country['max_score']:.3f}, avg={country['avg_score']:.3f}, n={country['chunk_count']})"
        )
        print(f"    철학 요약 유사도: {country['summary_score']:.3f}")

        if country["matched_chunks"]:
            print(f"    매칭 청크 (상위 {top_chunks_per_country}개):")
            for c in country["matched_chunks"][:top_chunks_per_country]:
                marker = "★" if c["is_core_philosophy"] else " "
                print(
                    f"      [{marker}] {c['chunk_id']} "
                    f"(weighted={c['weighted_score']:.3f}, raw={c['raw_score']:.3f}) "
                    f"| {c['category']}"
                )


def main():
    """5개 테스트 쿼리로 검증"""
    retriever = Retriever()

    test_queries = [
        "유아 주도 자유놀이를 충분히 보장하는 활동",
        "원주민 문화와 자연을 연결한 야외 활동",
        "교육과 돌봄을 통합한 일상 속 학습",
        "100가지 언어로 자신의 생각을 표현하는 미술 활동",
        "자연 속에서 위험을 감수하며 도전하는 모험놀이",
    ]

    for query in test_queries:
        result = retriever.search(query, top_k_countries=3)
        print_search_result(result, top_chunks_per_country=3)

    print(f"\n{'=' * 70}")
    print("✅ retriever.py 테스트 완료")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
