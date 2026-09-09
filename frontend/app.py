"""
frontend/app.py
====================
유아교육 다국가 지도안 추천 시스템 — EDU-bridge 디자인 매칭

팀원이 작성한 edu-bridge-full.html 의 디자인 시스템을 Streamlit에 적용:
  - 컬러: Teal(#1D9E75) 메인, Coral(#D85A30) 서브
  - 폰트: Noto Sans KR (한국어), Instrument Serif (제목 강조)
  - 레이아웃: Step Bar → Upload → Topic input → Detection → Philosophy 3 cards → Output

실행:
    cd backend
    streamlit run ../frontend/app.py
"""

import sys
from pathlib import Path
import tempfile
import time

import streamlit as st

# ============================================================
# 경로 설정
# ============================================================
FRONTEND_DIR = Path(__file__).parent
_candidates = [
    FRONTEND_DIR.parent / "backend",
    FRONTEND_DIR.parent,
]
BACKEND_ROOT = next((p for p in _candidates if (p / "services").exists()), None)
if BACKEND_ROOT is None:
    st.error("backend/ 폴더를 찾을 수 없습니다.")
    st.stop()

sys.path.insert(0, str(BACKEND_ROOT))

from services.keyword_extractor import extract_keywords
from services.retriever import Retriever
from services.card_generator import generate_cards, load_countries_metadata
from services.lesson_planner import generate_lesson_plan


# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="EDU-bridge — 글로벌 교육안 설계 플랫폼",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# 글로벌 CSS — 팀 HTML 디자인 시스템 매칭
# ============================================================
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Instrument+Serif:ital@0;1&display=swap');

:root {
  --teal: #1D9E75;
  --teal-2: #9FE1CB;
  --teal-3: #E1F5EE;
  --teal-dark: #085041;
  --teal-mid: #0F6E56;
  --coral: #D85A30;
  --coral-2: #F0997B;
  --coral-3: #FAECE7;
  --amber: #BA7517;
  --amber-3: #FAEEDA;
  --blue: #185FA5;
  --blue-3: #E6F1FB;
  --g0: #FAFAF8;
  --g1: #F4F3EF;
  --g2: #E8E6DF;
  --g3: #C8C6BC;
  --g5: #888780;
  --g7: #3A3A38;
  --g9: #141412;
  --r: 12px;
  --r-lg: 18px;
}

/* 전역 폰트 강제 */
html, body, [class*="css"], .stApp, .stMarkdown, .stTextInput, .stTextArea {
    font-family: 'Noto Sans KR', sans-serif !important;
}

/* Streamlit 기본 헤더 숨김, 배경색 */
.stApp { background: var(--g1); }
header[data-testid="stHeader"] { background: transparent; }

/* 메인 컨테이너 padding */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* 페이지 타이틀 */
.page-title {
    font-size: 28px;
    font-weight: 900;
    color: var(--g9);
    margin-bottom: 4px;
}
.page-sub {
    font-size: 14px;
    color: var(--g5);
    margin-bottom: 1.5rem;
}

/* Brand 헤더 */
.brand-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 20px;
    background: var(--g9);
    border-radius: var(--r-lg);
    margin-bottom: 1.5rem;
}
.brand-header h1 {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 22px;
    color: white;
    letter-spacing: -0.3px;
    margin: 0;
}
.brand-header h1 span { color: var(--teal-2); font-style: italic; }
.brand-header p {
    font-size: 12px;
    color: var(--g5);
    margin: 2px 0 0 0;
}

/* Step Bar */
.step-bar {
    display: flex;
    align-items: center;
    gap: 0;
    margin: 0 0 2rem 0;
    padding: 1rem 1.25rem;
    background: white;
    border-radius: var(--r-lg);
    border: 1px solid var(--g2);
}
.step { display: flex; align-items: center; }
.step-dot {
    width: 32px; height: 32px;
    border-radius: 50%;
    border: 2px solid var(--g2);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; color: var(--g5);
    background: white;
    transition: all 0.2s;
}
.step.done .step-dot { background: var(--teal); border-color: var(--teal); color: white; }
.step.active .step-dot { background: var(--g9); border-color: var(--g9); color: white; }
.step-label {
    font-size: 12px;
    color: var(--g5);
    margin-left: 10px;
    margin-right: 10px;
    white-space: nowrap;
}
.step.active .step-label { color: var(--g9); font-weight: 700; }
.step.done .step-label { color: var(--teal); }
.step-line { flex: 1; height: 2px; background: var(--g2); min-width: 24px; }
.step-line.done { background: var(--teal); }

/* Section card */
.section-card {
    background: white;
    border: 1px solid var(--g2);
    border-radius: var(--r-lg);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}
.section-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--g9);
    margin-bottom: 1rem;
}

/* Detection box (다크 배경 인식 결과) */
.detection-box {
    background: var(--g9);
    border-radius: var(--r-lg);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
}
.det-label {
    font-size: 12px;
    color: var(--teal-2);
    font-weight: 700;
    margin-bottom: 10px;
}
.det-chip {
    display: inline-block;
    padding: 6px 14px;
    background: rgba(29,158,117,0.2);
    border: 1px solid rgba(29,158,117,0.35);
    border-radius: 20px;
    font-size: 12px;
    color: white;
    font-weight: 500;
    margin: 3px 4px 3px 0;
}

/* Philosophy card (3개국 카드) */
.philo-card {
    border-radius: var(--r-lg);
    padding: 1.5rem;
    border: 1.5px solid transparent;
    transition: all 0.2s;
    height: 100%;
    margin-bottom: 1rem;
}
.philo-card-c0 { background: var(--teal-3); }
.philo-card-c1 { background: #FFF8F0; }
.philo-card-c2 { background: #F3F0FF; }
.philo-flag { font-size: 26px; margin-bottom: 8px; }
.philo-country {
    font-size: 12px;
    font-weight: 700;
    color: var(--g5);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.philo-title {
    font-size: 17px;
    font-weight: 900;
    color: var(--g9);
    margin-bottom: 6px;
    line-height: 1.3;
}
.philo-subtitle {
    font-size: 12px;
    color: var(--g7);
    margin-bottom: 12px;
}
.philo-tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 12px;
}
.philo-card-c0 .philo-tag { background: var(--teal); color: white; }
.philo-card-c1 .philo-tag { background: var(--coral); color: white; }
.philo-card-c2 .philo-tag { background: #7C6FCA; color: white; }
.philo-format {
    font-size: 11px;
    color: var(--g5);
    font-weight: 500;
    margin-bottom: 10px;
}
.philo-section-label {
    font-size: 10px;
    font-weight: 700;
    color: var(--g7);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-top: 12px;
    margin-bottom: 4px;
}
.philo-section-text {
    font-size: 12.5px;
    color: var(--g7);
    line-height: 1.6;
}

/* Output area (지도안 결과) */
.output-area {
    background: white;
    border: 1px solid var(--g2);
    border-radius: var(--r-lg);
    padding: 1.5rem 2rem;
    margin-top: 1rem;
}
.output-area h1, .output-area h2 {
    font-family: 'Instrument Serif', Georgia, serif;
    color: var(--g9);
}
.output-area h2 { font-size: 22px; border-bottom: 2px solid var(--teal-3); padding-bottom: 8px; margin-top: 1.5rem; }
.output-area h3 { font-size: 16px; color: var(--teal-dark); margin-top: 1rem; }
.output-area h4 { font-size: 13px; color: var(--g5); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.8rem; }
.output-area p, .output-area li { font-size: 14px; color: var(--g7); line-height: 1.8; }
.output-area strong { color: var(--g9); }
.output-area blockquote {
    border-left: 3px solid var(--teal);
    padding-left: 1rem;
    color: var(--g5);
    font-size: 13px;
    margin: 1rem 0;
}

/* Streamlit 버튼 커스터마이징 */
.stButton > button {
    background: white;
    border: 1.5px solid var(--g2);
    border-radius: var(--r);
    color: var(--g7);
    font-weight: 700;
    font-size: 13px;
    padding: 10px 20px;
    transition: all 0.15s;
    font-family: 'Noto Sans KR', sans-serif !important;
}
.stButton > button:hover {
    border-color: var(--teal);
    color: var(--teal);
}

/* Primary 버튼 (kind="primary") */
.stButton > button[kind="primary"] {
    background: var(--teal);
    color: white;
    border: none;
}
.stButton > button[kind="primary"]:hover {
    background: var(--teal-mid);
    color: white;
}

/* 입력 필드 */
.stTextArea textarea, .stTextInput input {
    border-radius: var(--r) !important;
    border: 1.5px solid var(--g2) !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 1px var(--teal) !important;
}

/* SelectBox */
.stSelectbox > div > div {
    border-radius: var(--r) !important;
    border: 1.5px solid var(--g2) !important;
}

/* File uploader 영역 */
[data-testid="stFileUploader"] {
    background: white;
    border: 2px dashed var(--g3);
    border-radius: var(--r-lg);
    padding: 1.5rem;
    transition: all 0.2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--teal);
    background: var(--teal-3);
}

/* Hide Streamlit 기본 footer */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }

/* 사이드바 다크 테마 */
[data-testid="stSidebar"] {
    background: var(--g9);
}
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: white;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--teal);
    border-color: var(--teal);
}

/* divider 색상 */
hr { border-color: var(--g2) !important; }
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ============================================================
# 캐싱
# ============================================================
@st.cache_resource(show_spinner="📚 교육과정 데이터베이스 로드 중...")
def get_retriever():
    return Retriever()

@st.cache_resource(show_spinner="📚 국가 메타데이터 로드 중...")
def get_metadata():
    return load_countries_metadata(BACKEND_ROOT / "data" / "all_countries.json")


# ============================================================
# 세션 상태
# ============================================================
def init_state():
    defaults = {
        "page": "input",
        "current_step": 1,           # 1: 입력, 2: 인식, 3: 매칭, 4: 지도안
        "keywords_result": None,
        "retrieval_result": None,
        "cards_result": None,
        "selected_card_idx": None,
        "lesson_plan_md": None,
        "input_text": "",
        "input_age": 4,
        "input_duration": 40,
        "input_image_bytes": None,
        "input_image_name": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ============================================================
# 헬퍼
# ============================================================
def reset_to_input():
    for k in [
        "keywords_result", "retrieval_result", "cards_result",
        "selected_card_idx", "lesson_plan_md",
    ]:
        st.session_state[k] = None
    st.session_state.current_step = 1
    st.session_state.page = "input"


def country_flag(code: str) -> str:
    flags = {
        "KOR": "🇰🇷", "JPN": "🇯🇵", "SGP": "🇸🇬", "GBR": "🇬🇧", "GER": "🇩🇪",
        "ITA": "🇮🇹", "FIN": "🇫🇮", "SWE": "🇸🇪", "AUS": "🇦🇺", "NZL": "🇳🇿",
    }
    return flags.get(code, "🌐")


def render_brand_header():
    st.markdown("""
    <div class="brand-header">
        <div>
            <h1>EDU-<span>bridge</span></h1>
            <p>글로벌 교육안 설계 플랫폼</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_step_bar(current: int):
    """1=입력, 2=인식, 3=철학 매칭, 4=지도안 생성"""
    steps = ["입력", "인식", "철학 매칭", "지도안 생성"]
    html = '<div class="step-bar">'
    for i, label in enumerate(steps, 1):
        if i < current:
            cls = "done"
        elif i == current:
            cls = "active"
        else:
            cls = ""
        html += f'<div class="step {cls}"><div class="step-dot">{i}</div><div class="step-label">{label}</div></div>'
        if i < len(steps):
            line_cls = "done" if i < current else ""
            html += f'<div class="step-line {line_cls}"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_detection_chips(kw: dict):
    """다크 배경의 인식 결과 박스"""
    chips_html = ""
    for keyword in kw.get("keywords", [])[:8]:
        chips_html += f'<span class="det-chip">{keyword}</span>'

    activity_type = kw.get("activity_type", "")
    areas = ", ".join(kw.get("suggested_areas", []))

    st.markdown(f"""
    <div class="detection-box">
        <div class="det-label">📡 키워드 추출 결과 (Gemini 분석)</div>
        <div style="margin-bottom: 10px;">
            <span style="color: rgba(255,255,255,0.7); font-size: 11px;">활동 유형</span>
            <span style="color: white; font-size: 13px; margin-left: 8px;">{activity_type}</span>
        </div>
        <div style="margin-bottom: 10px;">
            {chips_html}
        </div>
        <div>
            <span style="color: rgba(255,255,255,0.7); font-size: 11px;">누리과정 영역</span>
            <span style="color: var(--teal-2); font-size: 12px; margin-left: 8px; font-weight: 500;">{areas}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.markdown("### 🌏 EDU-bridge")
    st.caption("글로벌 교육안 설계 플랫폼")
    st.markdown("---")
    st.markdown("**📍 현재 단계**")
    step_names = {1: "1. 입력", 2: "2. 인식", 3: "3. 철학 매칭", 4: "4. 지도안 생성"}
    st.info(step_names.get(st.session_state.current_step, "?"))

    st.markdown("---")
    if st.button("🔄 처음부터 다시", use_container_width=True):
        reset_to_input()
        st.rerun()

    st.markdown("---")
    st.caption("**기술 스택**")
    st.caption("• Gemini 2.5 Flash (멀티모달)")
    st.caption("• ChromaDB + bge-m3 (RAG)")
    st.caption("• 10개국 유아교육과정 DB")


# ============================================================
# 페이지 1: 입력 + 카드
# ============================================================
def page_input():
    render_brand_header()
    st.markdown('<div class="page-title">📷 Play-Scanner</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">사진 또는 주제로 글로벌 교육 철학 3-Way 지도안을 생성합니다</div>', unsafe_allow_html=True)

    # Step bar
    render_step_bar(st.session_state.current_step)

    # 카드 결과가 있다면 카드 화면 함께 보여줌
    if st.session_state.cards_result is None:
        render_input_form()
    else:
        # 입력 요약 + 카드 화면
        render_detection_chips(st.session_state.keywords_result)
        render_cards_section()


def render_input_form():
    """입력 폼 (이미지 + 텍스트 + 연령/시간)"""
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="section-title">📷 교구 사진 업로드 (선택)</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            " ",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
            key="img_uploader",
        )
        if uploaded is not None:
            st.session_state.input_image_bytes = uploaded.getvalue()
            st.session_state.input_image_name = uploaded.name
            st.image(uploaded, use_container_width=True)
        elif st.session_state.input_image_bytes:
            st.image(st.session_state.input_image_bytes, use_container_width=True)
            if st.button("🗑️ 이미지 제거"):
                st.session_state.input_image_bytes = None
                st.session_state.input_image_name = None
                st.rerun()

    with col_right:
        st.markdown('<div class="section-title">✏️ 활동 아이디어</div>', unsafe_allow_html=True)
        text_input = st.text_area(
            " ",
            value=st.session_state.input_text,
            height=160,
            placeholder="예) 종이컵으로 쌓기 놀이를 하면서 균형을 배우는 활동",
            label_visibility="collapsed",
            key="text_area_main",
        )
        st.session_state.input_text = text_input

        col_a, col_b = st.columns(2)
        with col_a:
            age = st.selectbox(
                "대상 연령",
                options=[3, 4, 5],
                index=[3, 4, 5].index(st.session_state.input_age),
                format_func=lambda x: f"만 {x}세",
            )
            st.session_state.input_age = age
        with col_b:
            dur = st.selectbox(
                "활동 시간",
                options=[20, 30, 40, 50, 60],
                index=[20, 30, 40, 50, 60].index(st.session_state.input_duration),
                format_func=lambda x: f"{x}분",
            )
            st.session_state.input_duration = dur

    st.markdown("")
    has_input = bool(text_input.strip()) or st.session_state.input_image_bytes is not None

    col_btn = st.columns([2, 3, 2])[1]
    with col_btn:
        if st.button(
            "✨ 글로벌 교육 철학 매칭 시작",
            type="primary",
            use_container_width=True,
            disabled=not has_input,
        ):
            run_pipeline_to_cards()

    if not has_input:
        st.caption("📝 텍스트나 이미지 중 하나는 입력해주세요.")


def run_pipeline_to_cards():
    text = st.session_state.input_text.strip()
    age = st.session_state.input_age
    duration = st.session_state.input_duration
    image_bytes = st.session_state.input_image_bytes

    image_path = None
    tmp_file = None
    if image_bytes:
        suffix = Path(st.session_state.input_image_name or "img.png").suffix
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_file.write(image_bytes)
        tmp_file.close()
        image_path = tmp_file.name

    try:
        # Step 2: 인식 (키워드 추출)
        st.session_state.current_step = 2
        with st.spinner("🔍 [1/3] 입력 분석 및 키워드 추출 중... (약 5초)"):
            kw = extract_keywords(
                text=text or "유아 교육 활동",
                age=age, duration=duration, image_path=image_path,
            )
            st.session_state.keywords_result = kw

        # Step 3: 철학 매칭 (retriever + cards)
        st.session_state.current_step = 3
        with st.spinner("🌍 [2/3] 10개국 교육과정 DB 검색 중..."):
            retriever = get_retriever()
            retrieval = retriever.search(kw["search_query"], top_k_countries=3)
            st.session_state.retrieval_result = retrieval

        with st.spinner("🎴 [3/3] 3개국 수업 카드 생성 중... (약 15~20초)"):
            metadata = get_metadata()
            cards = generate_cards(
                user_query=kw["search_query"],
                age=age, duration=duration,
                top_countries=retrieval["top_countries"],
                countries_metadata=metadata,
            )
            st.session_state.cards_result = cards

        st.rerun()

    except Exception as e:
        st.error(f"❌ 처리 중 오류: {type(e).__name__}: {e}")
        st.exception(e)
        st.session_state.current_step = 1
    finally:
        if tmp_file:
            Path(tmp_file.name).unlink(missing_ok=True)


def render_cards_section():
    """철학 매칭 결과 — 3개국 카드 가로 배치"""
    st.markdown("""
    <div class="section-title" style="margin-top: 1rem;">
        🌍 글로벌 교육 철학 3-Way 매칭
        <span style="font-size:12px; font-weight:400; color:var(--g5); margin-left:6px;">(RAG 기반)</span>
    </div>
    """, unsafe_allow_html=True)

    cards = st.session_state.cards_result["cards"]

    cols = st.columns(3, gap="medium")
    for i, card in enumerate(cards):
        with cols[i]:
            render_philo_card(card, i)


def render_philo_card(card: dict, idx: int):
    """philosophy 카드 1장 — HTML 디자인 그대로"""
    code = card.get("country_code", "?")
    flag = country_flag(code)
    color_class = f"philo-card-c{idx}"   # c0=teal, c1=coral, c2=purple

    card_html = f"""
    <div class="philo-card {color_class}">
        <div class="philo-flag">{flag}</div>
        <div class="philo-country">{card.get('country', '')}</div>
        <div class="philo-title">{card.get('card_title', '')}</div>
        <div class="philo-subtitle">{card.get('card_subtitle', '')}</div>
        <span class="philo-tag">{card.get('philosophy_tag', '')}</span>
        <div class="philo-format">📚 {card.get('activity_format', '')}</div>

        <div class="philo-section-label">🎯 핵심 접근</div>
        <div class="philo-section-text">{card.get('key_approach', '')}</div>

        <div class="philo-section-label">🎬 활동 시나리오</div>
        <div class="philo-section-text">{card.get('activity_preview', '')}</div>

        <div class="philo-section-label">👶 유아 경험</div>
        <div class="philo-section-text">{card.get('expected_experience', '')}</div>

        <div class="philo-section-label">🧑‍🏫 교사 역할</div>
        <div class="philo-section-text">{card.get('teacher_role', '')}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # 선택 버튼
    if st.button(
        f"이 수업으로 지도안 만들기 →",
        key=f"select_{idx}",
        use_container_width=True,
        type="primary",
    ):
        st.session_state.selected_card_idx = idx
        run_lesson_plan_generation()


def run_lesson_plan_generation():
    cards = st.session_state.cards_result["cards"]
    retrieval = st.session_state.retrieval_result
    metadata = get_metadata()
    kw = st.session_state.keywords_result

    selected_card = cards[st.session_state.selected_card_idx]
    selected_code = selected_card["country_code"]
    country_data = next(
        (c for c in retrieval["top_countries"] if c["country_code"] == selected_code),
        None,
    )

    try:
        st.session_state.current_step = 4
        with st.spinner(f"📝 {selected_card['country']} 교육철학에 맞춘 지도안 작성 중... (약 20~30초)"):
            md = generate_lesson_plan(
                user_query=kw["search_query"],
                age=st.session_state.input_age,
                duration=st.session_state.input_duration,
                selected_country_code=selected_code,
                selected_card=selected_card,
                country_chunks=country_data["matched_chunks"],
                country_metadata=metadata[selected_code],
            )
            st.session_state.lesson_plan_md = md
        st.session_state.page = "lesson"
        st.rerun()
    except Exception as e:
        st.error(f"❌ 지도안 생성 실패: {type(e).__name__}: {e}")
        st.exception(e)


# ============================================================
# 페이지 2: 지도안
# ============================================================
def page_lesson():
    render_brand_header()
    st.markdown('<div class="page-title">📋 완성된 지도안</div>', unsafe_allow_html=True)
    cards = st.session_state.cards_result["cards"]
    selected_card = cards[st.session_state.selected_card_idx]
    code = selected_card["country_code"]
    md = st.session_state.lesson_plan_md

    st.markdown(
        f'<div class="page-sub">{country_flag(code)} <strong>{selected_card["country"]}</strong> 교육철학 기반 — '
        f'{selected_card.get("philosophy_tag", "")}</div>',
        unsafe_allow_html=True
    )

    render_step_bar(4)

    # 액션 버튼들
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("⬅️ 카드로 돌아가기", use_container_width=True):
            st.session_state.lesson_plan_md = None
            st.session_state.page = "input"
            st.session_state.current_step = 3
            st.rerun()
    with col2:
        st.download_button(
            "📥 Markdown 다운로드",
            data=md,
            file_name=f"lesson_plan_{code}_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col3:
        if st.button("🆕 새 활동 시작", use_container_width=True):
            reset_to_input()
            st.rerun()

    st.markdown("")
    # 지도안 본문 (예쁜 카드 안에)
    st.markdown('<div class="output-area">', unsafe_allow_html=True)
    st.markdown(md)
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 라우터
# ============================================================
if st.session_state.page == "input":
    page_input()
elif st.session_state.page == "lesson":
    page_lesson()
else:
    reset_to_input()
    st.rerun()
