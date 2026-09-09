"""
backend/main.py
====================
EDU-bridge FastAPI 백엔드

3개 API 엔드포인트 + 정적 HTML 서빙.
프론트엔드 (edu-bridge-full.html)는 static/ 폴더에서 서빙.

실행:
    cd backend
    uvicorn main:app --reload --port 8000

브라우저에서:
    http://localhost:8000/        → edu-bridge-full.html (메인 페이지)
    http://localhost:8000/docs    → FastAPI Swagger UI

API:
    POST /api/extract     이미지(선택) + 텍스트 → 키워드 추출
    POST /api/cards       search_query → 카드 3장
    POST /api/lesson      선택된 카드 → 지도안 (Markdown)
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import Optional, List, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ============================================================
# 경로 설정
# ============================================================
BACKEND_ROOT = Path(__file__).parent
sys.path.insert(0, str(BACKEND_ROOT))
STATIC_DIR = BACKEND_ROOT / "static"

from services.keyword_extractor import extract_keywords
from services.retriever import Retriever
from services.card_generator import generate_cards, load_countries_metadata
from services.lesson_planner import generate_lesson_plan


# ============================================================
# 앱 + 캐시된 리소스
# ============================================================
app = FastAPI(title="EDU-bridge API", version="0.1.0")

# CORS: 같은 origin이면 필요 없지만, 개발 시 다른 포트에서 띄울 수 있으니 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 무거운 리소스(Retriever, metadata)를 1회 로드 후 메모리 보관
class State:
    retriever: Optional[Retriever] = None
    metadata: Optional[dict] = None

state = State()


@app.on_event("startup")
def warmup():
    """서버 시작 시 retriever와 metadata 로드 (첫 요청을 빠르게)."""
    print("=" * 60)
    print("⚙️  EDU-bridge 백엔드 워밍업 중...")
    state.retriever = Retriever()
    state.metadata = load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")
    print("✅ 백엔드 준비 완료. 서버 가동.")
    print("=" * 60)


# ============================================================
# 응답/요청 스키마
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


class CardsResponse(BaseModel):
    selected_countries: List[str]
    cards: List[dict]
    # 추후 lesson_plan 호출 때 retriever 결과를 다시 안 만들도록 함께 반환
    retrieval_chunks: dict   # {country_code: [chunk, chunk, ...]}


class LessonRequest(BaseModel):
    search_query: str
    age: int
    duration: int
    selected_card: dict
    retrieval_chunks: List[dict]   # 해당 국가의 청크 리스트


class LessonResponse(BaseModel):
    markdown: str
    country_code: str


# ============================================================
# API 엔드포인트
# ============================================================

@app.post("/api/extract", response_model=ExtractResponse)
async def api_extract(
    text: str = Form(""),
    age: int = Form(4),
    duration: int = Form(40),
    image: Optional[UploadFile] = File(None),
):
    """
    Stage A: 사용자 입력에서 키워드/검색쿼리 추출.

    Form-data:
        text: 사용자 활동 설명 (선택)
        age: 만 나이
        duration: 활동 시간(분)
        image: 교구 사진 파일 (선택)
    """
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

    Body:
        search_query: 검색 쿼리
        age, duration
    """
    if state.retriever is None or state.metadata is None:
        raise HTTPException(status_code=503, detail="서버 워밍업 미완료. 잠시 후 재시도.")

    try:
        # Retriever
        retrieval = state.retriever.search(req.search_query, top_k_countries=3)
        # 카드 생성
        cards_result = generate_cards(
            user_query=req.search_query,
            age=req.age,
            duration=req.duration,
            top_countries=retrieval["top_countries"],
            countries_metadata=state.metadata,
        )

        # 다음 lesson 호출에서 재사용할 청크들을 국가별로 정리
        retrieval_chunks = {
            c["country_code"]: c["matched_chunks"]
            for c in retrieval["top_countries"]
        }

        return CardsResponse(
            selected_countries=cards_result.get("selected_countries", []),
            cards=cards_result.get("cards", []),
            retrieval_chunks=retrieval_chunks,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/api/lesson", response_model=LessonResponse)
async def api_lesson(req: LessonRequest):
    """
    Stage F: 선택된 카드로 완성된 지도안(Markdown) 생성.

    Body:
        search_query, age, duration
        selected_card: card_generator 결과의 카드 1개 (그대로)
        retrieval_chunks: 그 국가의 매칭 청크 리스트
    """
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
# 정적 파일 서빙 (HTML/CSS/JS)
# ============================================================
# /static/* 로 정적 파일 노출 (CSS, JS, 이미지 등)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    """루트 → static/edu-bridge-full.html 반환."""
    html_path = STATIC_DIR / "edu-bridge-full.html"
    if not html_path.exists():
        return JSONResponse(
            status_code=404,
            content={
                "error": "edu-bridge-full.html을 찾을 수 없습니다.",
                "expected_path": str(html_path),
                "hint": "backend/static/ 폴더에 HTML을 배치하세요.",
            },
        )
    return FileResponse(html_path, media_type="text/html")
