"""
load_data.py
====================
ChromaDB에 all_chunks.json의 163개 청크를 적재하는 스크립트.

실행 순서:
1. requirements.txt 설치: pip install -r requirements.txt
2. data/ 폴더에 all_chunks.json 배치
3. python load_data.py 실행
4. ./chroma_db/ 폴더에 벡터 DB가 생성됨 (재실행 시 기존 DB 덮어쓰기)

가중치 메커니즘:
- 일반 청크: philosophy_weight = 1.0
- 핵심철학 청크 (is_core_philosophy=true): philosophy_weight = 1.5
- 검색 후 점수에 이 가중치를 곱해서 핵심철학 청크를 부스트
"""

import json
import os
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions


# ============================================================
# 설정
# ============================================================
SCRIPT_DIR = Path(__file__).parent          # backend/db/
BACKEND_ROOT = SCRIPT_DIR.parent            # backend/
DATA_PATH = BACKEND_ROOT / "data" / "all_chunks.json"
CHROMA_PATH = SCRIPT_DIR / "chroma_db"      # backend/db/chroma_db/
COLLECTION_NAME = "ecec_chunks"
EMBEDDING_MODEL = "BAAI/bge-m3"  # 다국어 강력, 한국어/영어 모두 우수


def load_chunks(json_path: Path) -> list[dict]:
    """all_chunks.json 파일에서 청크 배열을 로드한다."""
    if not json_path.exists():
        raise FileNotFoundError(
            f"❌ 파일을 찾을 수 없습니다: {json_path}\n"
            f"   data/ 폴더에 all_chunks.json을 배치하세요."
        )

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    print(f"✓ JSON 파일 로드 완료: {len(chunks)}개 청크")
    return chunks


def init_chromadb(persist_dir: Path) -> chromadb.PersistentClient:
    """ChromaDB 클라이언트를 초기화하고 영속 디렉토리에 저장한다."""
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    print(f"✓ ChromaDB 초기화 완료: {persist_dir}")
    return client


def create_embedding_function():
    """bge-m3 임베딩 함수 생성. 첫 실행 시 모델이 다운로드된다 (약 2.3GB)."""
    print(f"⏳ 임베딩 모델 로딩 중: {EMBEDDING_MODEL}")
    print(f"   (첫 실행 시 모델 다운로드로 1-3분 소요)")

    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
        device="cpu",  # GPU 사용 가능 시 "cuda"로 변경
    )

    print(f"✓ 임베딩 모델 로딩 완료")
    return embed_fn


def reset_collection(client, collection_name: str, embed_fn):
    """기존 컬렉션이 있으면 삭제하고 새로 생성한다."""
    try:
        client.delete_collection(name=collection_name)
        print(f"  기존 컬렉션 '{collection_name}' 삭제")
    except Exception:
        pass  # 컬렉션이 없으면 무시

    collection = client.create_collection(
        name=collection_name,
        embedding_function=embed_fn,
        metadata={"description": "10개국 유아교육과정 청크 (RAG용)"},
    )
    print(f"✓ 컬렉션 '{collection_name}' 생성 완료")
    return collection


def insert_chunks(collection, chunks: list[dict]):
    """청크를 ChromaDB에 적재한다.

    ChromaDB metadata는 list/dict를 지원하지 않으므로,
    pedagogical_keywords는 콤마 구분 문자열로 변환한다.
    """
    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk["id"])
        documents.append(chunk["chunk_text"])

        metadata = {
            "country": chunk["country"],
            "country_code": chunk["country_code"],
            "framework_name": chunk["framework_name"],
            "category": chunk["category"],
            "pedagogical_keywords": ", ".join(chunk["pedagogical_keywords"]),
            "is_core_philosophy": chunk["is_core_philosophy"],
            "philosophy_weight": float(chunk["philosophy_weight"]),
            "source_location": chunk["source_location"],
        }
        metadatas.append(metadata)

    print(f"⏳ 청크 임베딩 및 적재 중... (CPU 기준 약 30초~1분 소요)")
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"✓ {len(ids)}개 청크 적재 완료")


def verify_insertion(collection):
    """적재 결과를 간단히 검증한다."""
    count = collection.count()
    print(f"\n=== 적재 검증 ===")
    print(f"총 청크 수: {count}")

    if count == 0:
        print("⚠ 적재된 청크가 없습니다!")
        return

    # 샘플 1개 가져와서 메타데이터 확인
    sample = collection.peek(limit=1)
    sample_meta = sample["metadatas"][0]
    print(f"\n샘플 청크:")
    print(f"  ID: {sample['ids'][0]}")
    print(f"  국가: {sample_meta['country']} ({sample_meta['country_code']})")
    print(f"  카테고리: {sample_meta['category']}")
    print(f"  핵심철학: {sample_meta['is_core_philosophy']}")
    print(f"  가중치: {sample_meta['philosophy_weight']}")
    print(f"  출처: {sample_meta['source_location']}")

    # 국가별 분포 확인 (where 필터로 카운트)
    print(f"\n국가별 청크 분포:")
    country_codes = ["FIN", "KOR", "AUS", "GER", "ITA", "JPN", "NZL", "SGP", "SWE", "GBR"]
    for code in country_codes:
        results = collection.get(where={"country_code": code})
        cp_count = sum(1 for m in results["metadatas"] if m["is_core_philosophy"])
        print(f"  {code}: {len(results['ids']):2}개 (핵심철학 {cp_count}개)")


def main():
    print("=" * 60)
    print("ChromaDB 적재 시작")
    print("=" * 60)

    # 1. 청크 로드
    chunks = load_chunks(DATA_PATH)

    # 2. ChromaDB 초기화
    client = init_chromadb(CHROMA_PATH)

    # 3. 임베딩 함수 준비
    embed_fn = create_embedding_function()

    # 4. 컬렉션 리셋 + 생성
    collection = reset_collection(client, COLLECTION_NAME, embed_fn)

    # 5. 청크 적재
    insert_chunks(collection, chunks)

    # 6. 검증
    verify_insertion(collection)

    print("\n" + "=" * 60)
    print("✅ 적재 완료! 다음 단계: retriever.py로 검색 테스트")
    print("=" * 60)


if __name__ == "__main__":
    main()
