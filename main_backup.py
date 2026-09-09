"""
backend/main.py
====================
EDU-bridge FastAPI 백엔드 (v2 - rotation 지원)

【v2 변경점】
- /api/cards에 offset 파라미터 추가 (0/3/6 → 1~3등 / 4~6등 / 7~9등)
- "다른 국가 추천 보기" 기능 지원

실행:
    cd backend

    # 본인 컴퓨터에서만 (개발):
    uvicorn main:app --reload --port 8000

    # 같은 와이파이의 다른 사람도 접근 (발표 시):
    uvicorn main:app --host 0.0.0.0 --port 8000
    # → 본인 IP 확인: ifconfig | grep "inet " | grep -v 127.0.0.1
    # → 같은 와이파이 사용자: http://본인IP:8000

브라우저:
    http://localhost:8000        → edu-bridge-full.html
    http://localhost:8000/docs   → Swagger UI

API:
    POST /api/extract             이미지+텍스트 → 키워드 추출
    POST /api/cards               search_query (+offset) → 카드 3장
    POST /api/lesson              선택된 카드 → 지도안 (Markdown)
"""

import sys
import tempfile
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BACKEND_ROOT = Path(__file__).parent
sys.path.insert(0, str(BACKEND_ROOT))
STATIC_DIR = BACKEND_ROOT / "static"

from services.keyword_extractor import extract_keywords
from services.retriever import Retriever
from services.card_generator import generate_cards, load_countries_metadata
from services.lesson_planner import generate_lesson_plan


# ============================================================
# 앱 + 캐시
# ============================================================
app = FastAPI(title="EDU-bridge API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class State:
    retriever: Optional[Retriever] = None
    metadata: Optional[dict] = None

state = State()


@app.on_event("startup")
def warmup():
    print("=" * 60)
    print("⚙️  EDU-bridge 백엔드 워밍업 중...")
    state.retriever = Retriever()
    state.metadata = load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")
    print("✅ 백엔드 준비 완료. 서버 가동.")
    print("=" * 60)


# ============================================================
# 스키마
# ============================================================
class ExtractResponse(BaseModel):
    detected_objects: List[str] = []
    activity_type: str = ""
    keywords: List[str] = []
    search_query: str = ""
    suggested_areas: List[str] = []


class CardsRequest(BaseModel):
    search_query: str
    age: int
    duration: int
    offset: int = 0           # 0/3/6 — 어디서부터 3개 보여줄지
    total_pool_size: int = 10 # retriever가 가져올 총 국가 수 (정렬 풀)


class CardsResponse(BaseModel):
    selected_countries: List[str]
    cards: List[dict]
    retrieval_chunks: dict
    offset: int               # 현재 offset (다음 페이지 계산용)
    pool_size: int            # 총 사용 가능 국가 수
    has_more: bool            # offset+3 < pool_size 면 True


class LessonRequest(BaseModel):
    search_query: str
    age: int
    duration: int
    selected_card: dict
    retrieval_chunks: List[dict]


class LessonResponse(BaseModel):
    markdown: str
    country_code: str


# ============================================================
# API
# ============================================================

@app.post("/api/extract", response_model=ExtractResponse)
async def api_extract(
    text: str = Form(""),
    age: int = Form(4),
    duration: int = Form(40),
    image: Optional[UploadFile] = File(None),
):
    if not text.strip() and image is None:
        raise HTTPException(status_code=400, detail="텍스트 또는 이미지 중 하나는 필요합니다.")

    image_path = None
    tmp_file = None
    try:
        if image is not None:
            suffix = Path(image.filename or "img.png").suffix
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            content = await image.read()
            tmp_file.write(content)
            tmp_file.close()
            image_path = tmp_file.name

        result = extract_keywords(
            text=text or "유아 교육 활동",
            age=age,
            duration=duration,
            image_path=image_path,
        )
        return ExtractResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    finally:
        if tmp_file:
            Path(tmp_file.name).unlink(missing_ok=True)


@app.post("/api/cards", response_model=CardsResponse)
async def api_cards(req: CardsRequest):
    """
    Stage B-D + E: 검색 + 카드 3장 생성.

    offset:
        0 → 1~3등 국가
        3 → 4~6등 국가
        6 → 7~9등 국가
    pool_size 가 모자라면 처음부터 다시 (rotation).
    """
    if state.retriever is None or state.metadata is None:
        raise HTTPException(status_code=503, detail="서버 워밍업 미완료. 잠시 후 재시도.")

    try:
        # 큰 풀(예: 10개)로 retriever 호출
        pool_size = max(req.total_pool_size, req.offset + 3)
        retrieval = state.retriever.search(req.search_query, top_k_countries=pool_size)
        all_top = retrieval["top_countries"]
        actual_pool = len(all_top)

        # offset 처리 (rotation)
        if actual_pool == 0:
            raise HTTPException(status_code=500, detail="추천된 국가가 없습니다.")

        # offset이 풀 크기를 넘으면 0으로 reset (rotation)
        effective_offset = req.offset % max(actual_pool, 1)

        # 3개 슬라이스 (끝에서 모자라면 앞에서 채움)
        end = effective_offset + 3
        if end <= actual_pool:
            sliced = all_top[effective_offset:end]
        else:
            # 끝에 닿으면 남은 거 + 처음부터 채움
            sliced = all_top[effective_offset:] + all_top[: end - actual_pool]

        # 카드 생성
        cards_result = generate_cards(
            user_query=req.search_query,
            age=req.age,
            duration=req.duration,
            top_countries=sliced,
            countries_metadata=state.metadata,
        )

        retrieval_chunks = {
            c["country_code"]: c["matched_chunks"]
            for c in sliced
        }

        return CardsResponse(
            selected_countries=cards_result.get("selected_countries", []),
            cards=cards_result.get("cards", []),
            retrieval_chunks=retrieval_chunks,
            offset=effective_offset,
            pool_size=actual_pool,
            has_more=actual_pool > 3,   # 3개 초과면 다른 추천 가능
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/api/lesson", response_model=LessonResponse)
async def api_lesson(req: LessonRequest):
    if state.metadata is None:
        raise HTTPException(status_code=503, detail="서버 워밍업 미완료.")

    selected_code = req.selected_card.get("country_code")
    if not selected_code or selected_code not in state.metadata:
        raise HTTPException(status_code=400, detail=f"올바르지 않은 country_code: {selected_code}")

    try:
        md = generate_lesson_plan(
            user_query=req.search_query,
            age=req.age,
            duration=req.duration,
            selected_country_code=selected_code,
            selected_card=req.selected_card,
            country_chunks=req.retrieval_chunks,
            country_metadata=state.metadata[selected_code],
        )
        return LessonResponse(markdown=md, country_code=selected_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "retriever_ready": state.retriever is not None,
        "metadata_ready": state.metadata is not None,
    }


# ============================================================
# 정적 파일 서빙
# ============================================================
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    html_path = STATIC_DIR / "edu-bridge-full.html"
    if not html_path.exists():
        return JSONResponse(
            status_code=404,
            content={
                "error": "edu-bridge-full.html을 찾을 수 없습니다.",
                "expected_path": str(html_path),
            },
        )
    return FileResponse(html_path, media_type="text/html")
