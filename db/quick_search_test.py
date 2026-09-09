"""
quick_search_test.py
====================
적재가 정상 완료됐는지 빠르게 확인하는 sanity check 스크립트.
실제 RAG 로직(가중치 적용 등)은 retriever.py에서 구현하고,
이 파일은 단순히 "임베딩이 동작하고 검색이 되는지"만 확인한다.

실행: python quick_search_test.py
"""

from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

SCRIPT_DIR = Path(__file__).parent
CHROMA_PATH = SCRIPT_DIR / "chroma_db"
COLLECTION_NAME = "ecec_chunks"
EMBEDDING_MODEL = "BAAI/bge-m3"

# 테스트 쿼리 5개 (서로 다른 나라가 1등으로 나와야 정상)
TEST_QUERIES = [
    "유아 주도 자유놀이를 충분히 보장하는 활동",         # → 한국 누리과정 강할 듯
    "원주민 문화와 자연을 연결한 야외 활동",             # → 호주 EYLF 강할 듯
    "교육과 돌봄을 통합한 일상 속 학습",                 # → 핀란드 EduCare 강할 듯
    "100가지 언어로 자신의 생각을 표현하는 미술 활동",    # → 이탈리아 레지오 강할 듯
    "자연 속에서 위험을 감수하며 도전하는 모험놀이",      # → 스웨덴/노르딕 강할 듯
]


def main():
    print("=" * 60)
    print("ChromaDB 검색 sanity check")
    print("=" * 60)

    # ChromaDB 연결
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
        device="cpu",
    )
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embed_fn)

    print(f"\n총 청크 수: {collection.count()}\n")

    # 각 쿼리에 대해 top-5 결과 출력
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"[{i}] 쿼리: {query}")
        results = collection.query(
            query_texts=[query],
            n_results=5,
        )

        print(f"    Top 5 결과:")
        for rank, (chunk_id, metadata, distance) in enumerate(
            zip(results["ids"][0], results["metadatas"][0], results["distances"][0]), 1
        ):
            country = metadata["country"]
            category = metadata["category"]
            is_core = "★" if metadata["is_core_philosophy"] else " "
            similarity = 1 - distance  # distance가 작을수록 유사
            print(
                f"      {rank}. [{is_core}] {chunk_id} ({country}) "
                f"sim={similarity:.3f} | {category}"
            )
        print()

    print("=" * 60)
    print("✅ 검색 동작 확인 완료")
    print("   ★ = 핵심철학 청크 (philosophy_weight=1.5 적용 대상)")
    print("   다음 단계: retriever.py에서 가중치 적용 + 국가별 점수 집계")
    print("=" * 60)


if __name__ == "__main__":
    main()
