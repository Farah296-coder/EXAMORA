import html
import json
import os

import requests
import streamlit as st

from ui_common import (
    clean_display_text,
    clean_exam_data,
    clean_question_data,
    create_exam_pdf,
    find_grounding_item,
    get_duplicate_pairs,
    get_grounding_items,
    get_grounding_verdict,
    get_overall_quality,
    get_quality_items,
    get_quality_score,
    normalize_verdict,
)

API_URL = os.environ.get("EXAMORA_API_URL", "http://127.0.0.1:8000")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def render_html(content):
    lines = [line.strip() for line in str(content).splitlines() if line.strip()]
    return st.markdown(chr(10).join(lines), unsafe_allow_html=True)


QUESTION_TYPES = ["MCQ", "True/False", "Short Answer"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]

PIPELINE = [
    (
        "Index",
        "Every page of your PDF is extracted, split into overlapping passages and turned into "
        "embeddings stored in a local Chroma vector database.",
    ),
    (
        "Retrieve",
        "For each question the section title is used as a semantic query, and the closest passages "
        "from your file are pulled back with their page numbers.",
    ),
    (
        "Generate",
        "Those passages — and nothing else — are handed to the language model, which writes one "
        "question, its options and the correct answer as strict JSON.",
    ),
    (
        "Verify",
        "Each question is scored for writing quality, compared with the others for repetition, and "
        "read back against the source pages to confirm the answer is really there.",
    ),
]

STACK = ["PyMuPDF", "MiniLM embeddings", "ChromaDB", "Groq · gpt-oss-20b", "FastAPI", "Streamlit"]

TEAM = [
    "Habiba Saad",
    "Farah",
    "Nima Galal",
    "Hend Elhout",
]

NAV = ["Chat", "How it works", "Team"]

FLOW_DIAGRAM = [
    ("Your PDF", "the only source"),
    ("Text extraction", "page by page"),
    ("Chunk & embed", "MiniLM vectors"),
    ("Vector database", "ChromaDB"),
    ("Semantic search", "top passages"),
    ("Language model", "writes the question"),
    ("Verification", "quality · repeats · grounding"),
]

FLOW_STEPS = ["Source", "Setup", "Draft", "Review"]

STAGE_STEP = {
    "pdf": 0,
    "count": 1,
    "setup": 1,
    "menu": 2,
    "edit_pick": 2,
    "edit_action": 2,
    "quality": 3,
    "export": 3,
}

st.set_page_config(
    page_title="Examora",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)


render_html("""
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@600;700;800&display=swap');

    :root {
        --primary: #7c3aed;
        --primary-dark: #5b21b6;
        --text: #0f172a;
        --muted: #64748b;
        --border: #e6e8f0;
    }

    * { font-family: 'Inter', sans-serif; }

    html, body, .stApp, [data-testid="stAppViewContainer"] {
        color: #0f172a !important;
        color-scheme: light !important;
    }

    .stApp { background: #f7f7fb; }

    section[data-testid="stSidebar"], #MainMenu, footer, header { display: none !important; }

    .block-container {
        max-width: 1120px;
        padding-top: 0.55rem;
        padding-bottom: 4rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* Nav bar */
    .st-key-navbar {
        position: sticky;
        top: 0;
        z-index: 90;
        background: rgba(255, 255, 255, 0.96);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border);
        border-radius: 16px;
        margin: 0 0 30px 0;
        padding: 10px 18px;
        box-shadow: 0 2px 10px rgba(20, 24, 58, 0.04);
    }

    .st-key-navbar div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 0.4rem !important;
    }

    .st-key-navbar div[data-testid="stVerticalBlock"] { gap: 0 !important; }

    .st-key-navbar div.stButton > button {
        border: none !important;
        background: transparent !important;
        color: #5a6379 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        min-height: 34px !important;
        padding: 0 8px !important;
        border-radius: 9px !important;
        letter-spacing: -0.1px !important;
    }

    .st-key-navbar div.stButton > button p,
    .st-key-navbar div.stButton > button div {
        white-space: nowrap !important;
        overflow: visible !important;
    }

    .st-key-navbar .head-note {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .st-key-navbar div.stButton > button:hover {
        background: #f4f1fe !important;
        color: #5b21b6 !important;
    }

    .st-key-navbar div.stButton > button[kind="primary"] {
        background: #ede9fe !important;
        color: #5b21b6 !important;
        font-weight: 700 !important;
    }

    .st-key-navbar .head-mark { width: 34px; height: 34px; min-width: 34px; border-radius: 10px; font-size: 15px; }

    .st-key-navbar .head-title { font-size: 16px; }

    .st-key-navbar .head-note { font-size: 11px; }

    .head-right { justify-content: flex-end; }

    /* Landing hero */
    .hero {
        text-align: center;
        max-width: 660px;
        margin: 9vh auto 30px auto;
    }

    .landing div[data-testid="stChatMessage"] { justify-content: center !important; }

    .hero-eyebrow {
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #8b93a7;
        margin-bottom: 14px;
    }

    .hero-title {
        font-family: 'Poppins', sans-serif;
        font-size: 36px;
        font-weight: 800;
        color: #14183a;
        letter-spacing: -1.1px;
        line-height: 1.2;
        margin-bottom: 14px;
    }

    .hero-sub {
        font-size: 14.5px;
        line-height: 1.7;
        color: #5a6379;
        max-width: 540px;
        margin: 0 auto;
    }

    .hero-wrap { max-width: 760px; margin: 0 auto; }

    .hero-gap { height: 6px; }

    div[data-testid="stChatMessage"] p { font-size: 15px; line-height: 1.7; }

    p, li, .stMarkdown p, div[data-testid="stMarkdownContainer"] p { color: #27314a; }

    div[data-testid="stMarkdownContainer"] strong { color: #14183a; }

    div[data-testid="stWidgetLabel"] p, .stTextInput label, .stNumberInput label,
    .stRadio label, .stSelectbox label, .stTextArea label, .stFileUploader label {
        color: #4a5570 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }

    /* Header */
    .app-head {
        display: flex;
        align-items: center;
        gap: 13px;
        padding: 4px 2px 18px 2px;
    }

    .app-mark {
        width: 42px;
        height: 42px;
        border-radius: 13px;
        background: #6d28d9;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Poppins', sans-serif;
        font-weight: 800;
        font-size: 19px;
    }

    .app-name {
        font-family: 'Poppins', sans-serif;
        font-size: 19px;
        font-weight: 800;
        color: #14183a;
        line-height: 1.15;
    }

    .app-sub { font-size: 12px; color: var(--muted); font-weight: 500; }

    .app-source {
        margin-left: auto;
        font-size: 11.5px;
        font-weight: 600;
        color: #4c1d95;
        background: #f1ecfe;
        border: 1px solid #e0d5fd;
        border-radius: 999px;
        padding: 6px 13px;
    }

    /* Chat bubbles */
    div[data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 0 14px 0 !important;
        display: flex !important;
        gap: 0 !important;
    }

    div[data-testid="stChatMessageAvatarUser"],
    div[data-testid="stChatMessageAvatarAssistant"],
    div[data-testid="stChatMessageAvatarCustom"] {
        display: none !important;
    }

    div[data-testid="stChatMessageContent"] {
        position: relative;
        max-width: 78%;
        background: #ffffff;
        border: 1px solid #e4e6f0;
        border-radius: 16px;
        border-top-left-radius: 4px;
        padding: 13px 17px;
        box-shadow: 0 1px 3px rgba(20, 24, 58, 0.06);
    }

    div[data-testid="stChatMessageContent"]::after {
        content: "";
        position: absolute;
        top: 0;
        left: -8px;
        width: 0;
        height: 0;
        border-top: 10px solid #ffffff;
        border-left: 10px solid transparent;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        justify-content: flex-end !important;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"])
    div[data-testid="stChatMessageContent"] {
        background: #ede9fe;
        border-color: #ddd2fb;
        border-top-left-radius: 16px;
        border-top-right-radius: 4px;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"])
    div[data-testid="stChatMessageContent"]::after {
        left: auto;
        right: -8px;
        border-top: 10px solid #ede9fe;
        border-left: none;
        border-right: 10px solid transparent;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"])
    div[data-testid="stChatMessageContent"] p { color: #3b2a63; }

    /* Question cards inside a message */
    .q {
        border: 1px solid var(--border);
        border-left: 4px solid #c4b5fd;
        border-radius: 14px;
        padding: 13px 15px;
        margin: 9px 0;
        background: #fcfcff;
    }

    .q-top {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 7px;
        flex-wrap: wrap;
    }

    .q-num {
        font-family: 'Poppins', sans-serif;
        font-size: 13px;
        font-weight: 800;
        color: #4c1d95;
    }

    .tag {
        font-size: 10.5px;
        font-weight: 700;
        padding: 3px 9px;
        border-radius: 999px;
        background: #f1f5f9;
        color: #52607a;
        border: 1px solid #e6e8f0;
    }

    .tag.type { background: #f1ecfe; color: #5b21b6; border-color: #e0d5fd; }
    .tag.ok { background: #e9f9ef; color: #15803d; border-color: #c9f0d8; }
    .tag.warn { background: #fef6e7; color: #92400e; border-color: #fbe3b8; }
    .tag.bad { background: #fdeceb; color: #b91c1c; border-color: #f8cfcd; }
    .tag.idle { background: #f1f5f9; color: #64748b; border-color: #e6e8f0; }

    .q-text { font-size: 15px; line-height: 1.65; color: #1f2740; }

    .q-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
        gap: 10px;
    }

    .q-grid .q { margin: 0; }

    .q-choice {
        font-size: 13.5px;
        line-height: 1.55;
        color: #46506b;
        padding: 2px 0 2px 2px;
    }

    .q-choice.right { color: #15803d; font-weight: 600; }

    .q-ans { font-size: 12.5px; color: #15803d; font-weight: 600; margin-top: 6px; }

    .q-why { font-size: 12.5px; color: #64748b; line-height: 1.6; margin-top: 6px; }

    /* Score summary */
    .score-line {
        display: flex;
        align-items: baseline;
        gap: 10px;
        margin: 2px 0 10px 0;
    }

    .score-big {
        font-family: 'Poppins', sans-serif;
        font-size: 34px;
        font-weight: 800;
        color: #5b21b6;
        line-height: 1;
    }

    .score-of { font-size: 12px; color: var(--muted); font-weight: 600; }

    /* Inputs */
    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"] {
        background: #ffffff !important;
        border-radius: 12px !important;
    }

    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: var(--border) !important;
        border-radius: 12px !important;
    }

    div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.13) !important;
    }

    div[data-baseweb="select"] > div {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: var(--border) !important;
        border-radius: 12px !important;
    }

    ul[role="listbox"], div[data-baseweb="popover"] ul {
        background: #ffffff !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }

    li[role="option"] { color: #0f172a !important; }
    li[role="option"]:hover { background: #f5f3ff !important; }

    section[data-testid="stFileUploaderDropzone"] {
        background: #fbfaff !important;
        border: 1.5px dashed #c4b5fd !important;
        border-radius: 16px !important;
        color: #46506b !important;
    }

    section[data-testid="stFileUploaderDropzone"] span,
    section[data-testid="stFileUploaderDropzone"] small { color: var(--muted) !important; }

    section[data-testid="stFileUploaderDropzone"] button {
        background: #ffffff !important;
        color: #5b21b6 !important;
        border: 1px solid #c4b5fd !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }

    /* Radios as chips */
    div[data-testid="stRadio"] > div {
        gap: 8px !important;
        flex-wrap: wrap !important;
    }

    div[data-testid="stRadio"] label {
        background: #ffffff !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 9px 15px !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        color: #46506b !important;
        cursor: pointer !important;
    }

    div[data-testid="stRadio"] label:has(input:checked) {
        background: #6d28d9 !important;
        border-color: #6d28d9 !important;
        color: #ffffff !important;
    }

    div[data-testid="stRadio"] label > div:first-child { display: none !important; }

    /* Buttons */
    div.stButton > button, div[data-testid="stDownloadButton"] button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        min-height: 42px !important;
        border: 1px solid var(--border) !important;
        background: #ffffff !important;
        color: #4c1d95 !important;
    }

    div.stButton > button:hover, div[data-testid="stDownloadButton"] button:hover {
        border-color: #c4b5fd !important;
        background: #faf8ff !important;
    }

    div.stButton > button[kind="primary"], div[data-testid="stDownloadButton"] button {
        background: #6d28d9 !important;
        color: #ffffff !important;
        border-color: #6d28d9 !important;
    }

    div.stButton > button[kind="primary"]:hover, div[data-testid="stDownloadButton"] button:hover {
        background: #5b21b6 !important;
        color: #ffffff !important;
    }

    div[data-testid="stAlert"] { border-radius: 14px !important; }

    div[data-testid="stSpinner"] p { color: #5b21b6 !important; }

    ::-webkit-scrollbar { width: 9px; }
    ::-webkit-scrollbar-thumb { background: #ddd6fe; border-radius: 999px; }

    </style>
    """)


# ============================================================
# STATE
# ============================================================

defaults = {
    "chat": [],
    "stage": "pdf",
    "pdf_name": None,
    "pdf_pages": 0,
    "pdf_chunks": 0,
    "processed_key": None,
    "failed_key": None,
    "num_questions": 10,
    "topic": "",
    "focus_topic": "",
    "topic_seeds": [],
    "types": ["MCQ"],
    "difficulties": ["Medium"],
    "question_type": "MCQ",
    "difficulty": "Medium",
    "exam": [],
    "quality": None,
    "duplicates": None,
    "grounding": None,
    "edit_index": 0,
    "view": "Chat",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def say(role, text, as_html=False):
    st.session_state.chat.append({"role": role, "text": text, "html": as_html})


def bot(text, as_html=False):
    say("assistant", text, as_html)


def user(text):
    say("user", text)


def go(stage):
    st.session_state.stage = stage
    st.rerun()


def multi_choice(label, options, default, key):
    if hasattr(st, "pills"):
        picked = st.pills(
            label,
            options,
            selection_mode="multi",
            default=default,
            key=key,
        )
        return list(picked or [])

    return st.multiselect(label, options, default=default, key=key)


def load_extracted_pages():
    path = os.path.join(BASE_DIR, "output", "extracted_text.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def first_meaningful_line(text, banned):
    for raw_line in str(text).splitlines():
        line = clean_display_text(raw_line)
        if len(line) < 4 or len(line) > 70:
            continue
        if not any(character.isalpha() for character in line):
            continue
        if line.lower() in banned:
            continue
        return line
    return ""


def build_topic_seeds(count):
    pages = load_extracted_pages()

    if not pages:
        return []

    openers = {}
    for page in pages:
        line = clean_display_text(str(page.get("text", "")).splitlines()[0]) if page.get("text") else ""
        if line:
            openers[line.lower()] = openers.get(line.lower(), 0) + 1

    banned = {line for line, hits in openers.items() if hits > max(2, len(pages) * 0.4)}

    titles = []
    seen = set()
    for page in pages:
        title = first_meaningful_line(page.get("text", ""), banned)
        if title and title.lower() not in seen:
            seen.add(title.lower())
            titles.append(title)

    if not titles:
        return []

    if len(titles) <= count:
        return titles

    step = len(titles) / float(count)
    return [titles[int(i * step)] for i in range(count)]


def reset_results():
    st.session_state.quality = None
    st.session_state.duplicates = None
    st.session_state.grounding = None


# ============================================================
# API
# ============================================================

def api_call(method, endpoint, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}{endpoint}", timeout=300, **kwargs)

        if response.status_code == 429:
            st.warning("The AI service is rate-limited right now. Wait a few seconds and try again.")
            return None

        response.raise_for_status()
        payload = response.json()

        if not payload.get("success"):
            st.error(payload.get("error", "The request failed."))
            return None

        return payload.get("data")

    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the backend. Keep the API window open and try again.")
        return None
    except requests.exceptions.Timeout:
        st.error("That took too long. Try again with fewer questions.")
        return None
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        return None


# ============================================================
# MESSAGE BUILDERS
# ============================================================

def question_html(index, question):
    question = clean_question_data(question)
    qtype = clean_display_text(question.get("question_type", "MCQ")) or "MCQ"
    difficulty = clean_display_text(question.get("difficulty", "Medium")) or "Medium"
    text = clean_display_text(question.get("question", ""))
    answer = clean_display_text(question.get("correct_answer", question.get("answer", "")))
    choices = question.get("choices") or []

    parts = [
        '<div class="q">',
        '<div class="q-top">',
        f'<span class="q-num">Question {index + 1}</span>',
        f'<span class="tag type">{html.escape(qtype)}</span>',
        f'<span class="tag">{html.escape(difficulty)}</span>',
        "</div>",
        f'<div class="q-text">{html.escape(text)}</div>',
    ]

    if isinstance(choices, list) and choices:
        for choice_index, choice in enumerate(choices):
            choice_text = clean_display_text(choice)
            is_right = choice_text and choice_text == answer
            letter = chr(65 + choice_index)
            mark = " ✓" if is_right else ""
            css = "q-choice right" if is_right else "q-choice"
            parts.append(f'<div class="{css}">{letter}. {html.escape(choice_text)}{mark}</div>')
    elif answer:
        parts.append(f'<div class="q-ans">Answer: {html.escape(answer)}</div>')

    parts.append("</div>")
    return "".join(parts)


def exam_html(exam):
    return "".join(question_html(index, question) for index, question in enumerate(exam))


def quality_html(exam, quality):
    items = get_quality_items(quality)
    overall = get_overall_quality(quality, items)

    parts = []

    if overall is not None:
        verdict = (
            "Solid exam overall."
            if overall >= 80
            else "Usable, but some questions are weak."
            if overall >= 60
            else "Several questions need rewriting."
        )
        parts.append(
            '<div class="score-line">'
            f'<span class="score-big">{overall:.0f}</span>'
            '<span class="score-of">/ 100 average</span>'
            "</div>"
            f'<div class="q-why">{html.escape(verdict)}</div>'
        )

    for index, question in enumerate(exam):
        item = items[index] if index < len(items) else None
        score = get_quality_score(item)
        text = clean_display_text(question.get("question", ""))

        if score is None:
            tag, label = "idle", "not scored"
        elif score >= 80:
            tag, label = "ok", f"{score:.0f}/100"
        elif score >= 60:
            tag, label = "warn", f"{score:.0f}/100"
        else:
            tag, label = "bad", f"{score:.0f}/100"

        feedback = ""
        if isinstance(item, dict):
            feedback = clean_display_text(item.get("feedback", ""))

        parts.append(
            '<div class="q">'
            '<div class="q-top">'
            f'<span class="q-num">Question {index + 1}</span>'
            f'<span class="tag {tag}">{html.escape(label)}</span>'
            "</div>"
            f'<div class="q-text">{html.escape(text)}</div>'
            + (f'<div class="q-why">{html.escape(feedback)}</div>' if feedback else "")
            + "</div>"
        )

    return "".join(parts)


def duplicates_html(duplicates):
    pairs = get_duplicate_pairs(duplicates)
    flagged = [
        pair for pair in pairs
        if isinstance(pair, dict) and pair.get("status") in ("Duplicate", "Review")
    ]

    if not flagged:
        return (
            f'<div class="q-why">I compared {len(pairs)} question pairs and none of them '
            "ask the same thing. Nothing to merge.</div>"
        )

    parts = [
        f'<div class="q-why">{len(flagged)} of {len(pairs)} compared pairs look close. '
        "The rest are fine.</div>"
    ]

    for pair in flagged:
        status = str(pair.get("status", "Review"))
        tag = "bad" if status == "Duplicate" else "warn"
        reason = clean_display_text(pair.get("reason", ""))
        similarity = pair.get("semantic_similarity", 0)

        parts.append(
            '<div class="q">'
            '<div class="q-top">'
            f'<span class="q-num">Question {pair.get("question_a")} &amp; {pair.get("question_b")}</span>'
            f'<span class="tag {tag}">{html.escape(status)}</span>'
            f'<span class="tag">{similarity}% similar</span>'
            "</div>"
            + (f'<div class="q-why">{html.escape(reason)}</div>' if reason else "")
            + "</div>"
        )

    return "".join(parts)


def grounding_html(exam, grounding):
    items = get_grounding_items(grounding)
    parts = []
    supported = 0

    for index, question in enumerate(exam):
        item = find_grounding_item(items, question, index)
        verdict = normalize_verdict(get_grounding_verdict(item) if item else None)
        text = clean_display_text(question.get("question", ""))
        reason = clean_display_text(item.get("reason", "")) if isinstance(item, dict) else ""
        pages = item.get("source_pages") if isinstance(item, dict) else None

        if verdict == "supported":
            tag, label = "ok", "found in your PDF"
            supported += 1
        elif verdict == "unsupported":
            tag, label = "warn", "not backed by the PDF"
        else:
            tag, label = "idle", "not evaluated"

        pages_tag = ""
        if isinstance(pages, list) and pages:
            shown = ", ".join(str(page) for page in pages[:4])
            pages_tag = f'<span class="tag">pages {html.escape(shown)}</span>'

        parts.append(
            '<div class="q">'
            '<div class="q-top">'
            f'<span class="q-num">Question {index + 1}</span>'
            f'<span class="tag {tag}">{html.escape(label)}</span>'
            f"{pages_tag}"
            "</div>"
            f'<div class="q-text">{html.escape(text)}</div>'
            + (f'<div class="q-why">{html.escape(reason)}</div>' if reason else "")
            + "</div>"
        )

    header = f'<div class="q-why">{supported} of {len(exam)} questions are supported by the source text.</div>'
    return header + "".join(parts)


# ============================================================
# HEADER
# ============================================================

render_html("""
    <style>

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--border);
        width: 330px !important;
    }

    section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }

    .side-brand {
        display: flex;
        align-items: center;
        gap: 11px;
        padding: 0 4px 16px 4px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 18px;
    }

    .side-mark {
        width: 38px;
        height: 38px;
        border-radius: 11px;
        background: #6d28d9;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Poppins', sans-serif;
        font-weight: 800;
        font-size: 17px;
    }

    .side-name {
        font-family: 'Poppins', sans-serif;
        font-size: 17px;
        font-weight: 800;
        color: #14183a;
        line-height: 1.15;
    }

    .side-role { font-size: 11.5px; color: var(--muted); font-weight: 500; }

    .side-label {
        font-size: 10.5px;
        font-weight: 800;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #8b93a7;
        margin: 22px 4px 10px 4px;
    }

    .side-lead {
        font-size: 12.5px;
        line-height: 1.65;
        color: #4a5570;
        padding: 0 4px;
        margin-bottom: 4px;
    }

    .step-row {
        display: flex;
        gap: 10px;
        padding: 9px 4px;
        border-top: 1px solid #f1f2f7;
    }

    .step-index {
        width: 21px;
        height: 21px;
        min-width: 21px;
        border-radius: 7px;
        background: #f1ecfe;
        color: #5b21b6;
        font-size: 11px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 1px;
    }

    .step-name {
        font-size: 12.5px;
        font-weight: 700;
        color: #14183a;
        margin-bottom: 2px;
    }

    .step-note { font-size: 11.5px; line-height: 1.6; color: #6b7386; }

    .chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 4px; }

    .chip {
        font-size: 10.5px;
        font-weight: 600;
        color: #4a5570;
        background: #f6f7fb;
        border: 1px solid var(--border);
        border-radius: 7px;
        padding: 4px 8px;
    }

    .member {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 4px;
        border-top: 1px solid #f1f2f7;
    }

    .member-badge {
        width: 28px;
        height: 28px;
        min-width: 28px;
        border-radius: 9px;
        background: #f1ecfe;
        color: #5b21b6;
        font-size: 11px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .member-name { font-size: 12.5px; font-weight: 700; color: #14183a; line-height: 1.3; }
    .member-role { font-size: 11px; color: #6b7386; line-height: 1.45; }

    .side-foot {
        font-size: 10.5px;
        color: #9aa1b4;
        padding: 16px 4px 0 4px;
        border-top: 1px solid var(--border);
        margin-top: 20px;
        line-height: 1.6;
    }

    /* Main header */
    .head {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 2px 0 16px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 18px;
    }

    .head-title {
        font-family: 'Poppins', sans-serif;
        font-size: 21px;
        font-weight: 800;
        color: #14183a;
        line-height: 1.2;
    }

    .head-note { font-size: 12.5px; color: var(--muted); line-height: 1.5; }

    .head-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }

    .head-chip {
        font-size: 11.5px;
        font-weight: 600;
        color: #4a5570;
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 6px 13px;
        white-space: nowrap;
    }

    .head-chip.live { color: #4c1d95; background: #f4f0ff; border-color: #e2d9fd; }

    /* Flow strip */
    .flow {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }

    .flow-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 7px 14px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: #ffffff;
        font-size: 12.5px;
        font-weight: 600;
        color: #8b93a7;
    }

    .flow-item .dot {
        width: 18px;
        height: 18px;
        border-radius: 6px;
        background: #f1f2f7;
        color: #8b93a7;
        font-size: 10px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .flow-item.done { color: #15803d; border-color: #cdeedb; background: #f4fcf7; }
    .flow-item.done .dot { background: #dcf5e6; color: #15803d; }

    .flow-item.now { color: #ffffff; border-color: #6d28d9; background: #6d28d9; }
    .flow-item.now .dot { background: rgba(255, 255, 255, 0.22); color: #ffffff; }

    .flow-sep { width: 14px; height: 1px; background: #e2e4ee; }

    .head-brand { display: flex; align-items: center; gap: 13px; }

    .head-mark {
        width: 40px;
        height: 40px;
        min-width: 40px;
        border-radius: 12px;
        background: #6d28d9;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Poppins', sans-serif;
        font-weight: 800;
        font-size: 18px;
    }

    /* Nav */
    .nav-rule {
        height: 1px;
        background: var(--border);
        margin: 14px 0 22px 0;
    }

    /* Content pages */
    .page-head { margin-bottom: 26px; }

    .page-title {
        font-family: 'Poppins', sans-serif;
        font-size: 27px;
        font-weight: 800;
        color: #14183a;
        letter-spacing: -0.5px;
        margin-bottom: 8px;
    }

    .page-lead {
        font-size: 14.5px;
        line-height: 1.75;
        color: #4a5570;
        max-width: 860px;
    }

    .block-label {
        font-size: 10.5px;
        font-weight: 800;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #8b93a7;
        margin: 30px 0 14px 0;
    }

    .diagram {
        display: flex;
        align-items: stretch;
        gap: 6px;
        flex-wrap: wrap;
        padding: 20px;
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 16px;
    }

    .node {
        flex: 1;
        min-width: 132px;
        background: #fbfaff;
        border: 1px solid #ece9f8;
        border-radius: 12px;
        padding: 12px 13px;
    }

    .node-name {
        font-size: 12.5px;
        font-weight: 800;
        color: #4c1d95;
        line-height: 1.3;
        margin-bottom: 3px;
    }

    .node-note { font-size: 11px; color: #6b7386; line-height: 1.5; }

    .arrow {
        display: flex;
        align-items: center;
        color: #c9cbd8;
        font-size: 14px;
        font-weight: 700;
    }

    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
        gap: 14px;
    }

    .card {
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 18px 19px;
    }

    .card-index {
        width: 26px;
        height: 26px;
        border-radius: 9px;
        background: #f1ecfe;
        color: #5b21b6;
        font-size: 12px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 11px;
    }

    .card-name {
        font-family: 'Poppins', sans-serif;
        font-size: 15px;
        font-weight: 700;
        color: #14183a;
        margin-bottom: 6px;
        line-height: 1.3;
    }

    .card-note { font-size: 13px; line-height: 1.7; color: #5a6379; }

    .name-list {
        max-width: 420px;
        border: 1px solid var(--border);
        border-radius: 16px;
        background: #ffffff;
        overflow: hidden;
    }

    .name-row {
        font-family: 'Poppins', sans-serif;
        font-size: 16px;
        font-weight: 600;
        color: #14183a;
        padding: 15px 20px;
        border-bottom: 1px solid #f1f2f7;
    }

    .name-row:last-child { border-bottom: none; }

    .member-card { display: flex; flex-direction: column; gap: 10px; }

    .member-top { display: flex; align-items: center; gap: 12px; }

    .member-top .card-name { margin-bottom: 2px; }

    .member-badge {
        width: 40px;
        height: 40px;
        min-width: 40px;
        border-radius: 13px;
        background: #6d28d9;
        color: #ffffff;
        font-size: 14px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .member-role { font-size: 12px; color: #5b21b6; font-weight: 600; line-height: 1.4; }

    .member-files {
        font-size: 11px;
        color: #8b93a7;
        font-family: 'Inter', monospace;
        border-top: 1px solid #f1f2f7;
        padding-top: 10px;
        line-height: 1.6;
    }

    </style>
    """)


if st.session_state.pdf_name:
    source_chip = (
        f'<div class="head-chip live">{html.escape(st.session_state.pdf_name)}</div>'
        f'<div class="head-chip">{st.session_state.pdf_pages} pages</div>'
    )
else:
    source_chip = ""

if st.session_state.exam:
    source_chip += f'<div class="head-chip">{len(st.session_state.exam)} questions</div>'

with st.container(key="navbar"):

    brand_column, chat_column, how_column, team_column, status_column = st.columns(
        [2.9, 1, 1.45, 1, 3.65],
        vertical_alignment="center",
    )

    with brand_column:
        render_html(
            """
            <div class="head-brand">
                <div class="head-mark">E</div>
                <div>
                    <div class="head-title">Examora</div>
                    <div class="head-note">Exams grounded in your own material</div>
                </div>
            </div>
            """
        )

    for column, item in zip([chat_column, how_column, team_column], NAV):
        with column:
            if st.button(
                item,
                key=f"nav_{item}",
                type="primary" if st.session_state.view == item else "secondary",
                use_container_width=True,
            ):
                st.session_state.view = item
                st.rerun()

    with status_column:
        render_html(f'<div class="head-right">{source_chip}</div>')


# ============================================================
# PAGE: HOW IT WORKS
# ============================================================

if st.session_state.view == "How it works":

    render_html("""
        <div class="page-head">
            <div class="page-title">How this assistant works</div>
            <div class="page-lead">
                Examora is a retrieval-augmented generation (RAG) system. A general chatbot answers from
                what it memorised during training; this one is only allowed to use the document you
                upload. Your PDF is indexed, searched for the passages that match each section, and only
                those passages reach the language model &mdash; so every question can be traced back to the
                page it came from.
            </div>
        </div>
        """)

    render_html(
'<div class="diagram">'
        + '<div class="arrow">&rarr;</div>'.join(
            f'<div class="node"><div class="node-name">{html.escape(name)}</div>'
            f'<div class="node-note">{html.escape(note)}</div></div>'
            for name, note in FLOW_DIAGRAM
        )
        + "</div>"
    )

    render_html('<div class="block-label">The four stages</div>')

    render_html(
'<div class="card-grid">'
        + "".join(
            f'<div class="card">'
            f'<div class="card-index">{index + 1}</div>'
            f'<div class="card-name">{html.escape(name)}</div>'
            f'<div class="card-note">{html.escape(note)}</div>'
            f"</div>"
            for index, (name, note) in enumerate(PIPELINE)
        )
        + "</div>"
    )

    render_html('<div class="block-label">Why not just ask a chatbot</div>')

    render_html("""
        <div class="card-grid">
            <div class="card">
                <div class="card-name">It cannot invent material</div>
                <div class="card-note">
                    The prompt carries the retrieved passages and an instruction to use nothing else, so the
                    exam stays inside the syllabus you actually taught.
                </div>
            </div>
            <div class="card">
                <div class="card-name">Every question cites its pages</div>
                <div class="card-note">
                    Retrieval returns page numbers with each passage, and they travel with the question all
                    the way to the grounding report.
                </div>
            </div>
            <div class="card">
                <div class="card-name">It checks its own work</div>
                <div class="card-note">
                    A second pass scores the writing, flags questions that repeat each other, and re-reads
                    every answer against the source before you export the paper.
                </div>
            </div>
        </div>
        """)

    render_html('<div class="block-label">Built with</div>')
    render_html(
'<div class="chips">'
        + "".join(f'<span class="chip">{html.escape(item)}</span>' for item in STACK)
        + "</div>"
    )

    st.stop()


# ============================================================
# PAGE: TEAM
# ============================================================

if st.session_state.view == "Team":

    render_html("""
        <div class="page-head">
            <div class="page-title">The team</div>
        </div>
        """)

    render_html(
        '<div class="name-list">'
        + "".join(f'<div class="name-row">{html.escape(name)}</div>' for name in TEAM)
        + "</div>"
    )

    st.stop()


# ============================================================
# PAGE: CHAT
# ============================================================

on_landing = st.session_state.stage == "pdf" and not st.session_state.chat

if on_landing:

    render_html(
        """
        <div class="hero">
            <div class="hero-eyebrow">Examora assistant</div>
            <div class="hero-title">How can I help you today?</div>
            <div class="hero-sub">
                Give me the PDF you teach from and I will build the exam with you — question by question,
                grounded in your own pages, with the answers checked against the source before you export.
            </div>
        </div>
        """
    )

current_step = STAGE_STEP.get(st.session_state.stage, 0)

flow_parts = []
for index, label in enumerate(FLOW_STEPS):
    if index < current_step:
        state, marker = "done", "✓"
    elif index == current_step:
        state, marker = "now", str(index + 1)
    else:
        state, marker = "", str(index + 1)

    flow_parts.append(
        f'<div class="flow-item {state}"><div class="dot">{marker}</div>{html.escape(label)}</div>'
    )

if not on_landing:
    render_html('<div class="flow">' + '<div class="flow-sep"></div>'.join(flow_parts) + "</div>")


# ============================================================
# HISTORY
# ============================================================

for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        if message.get("html"):
            render_html(message["text"])
        else:
            st.markdown(message["text"])


# ============================================================
# CURRENT STEP
# ============================================================

stage = st.session_state.stage

with st.chat_message("assistant"):

    # --------------------------------------------------------
    if stage == "pdf":

        prompt = (
            "Hi! Upload the PDF you want the exam to come from — lecture slides, a chapter, "
            "any course material. I read it page by page and index it so every question I write "
            "comes from your file and nothing else."
        )
        st.markdown(prompt)

        uploaded = st.file_uploader("PDF file", type=["pdf"], key="chat_pdf", label_visibility="collapsed")

        if uploaded is not None:
            file_key = f"{uploaded.name}:{uploaded.size}"

            if st.session_state.failed_key == file_key:
                if st.button("Try this file again"):
                    st.session_state.failed_key = None
                    st.rerun()

            elif st.session_state.processed_key != file_key:
                with st.spinner("Reading and indexing your PDF..."):
                    data = None
                    try:
                        response = requests.post(
                            f"{API_URL}/api/upload-pdf",
                            files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                            timeout=300,
                        )
                        response.raise_for_status()
                        payload = response.json()
                        if payload.get("success"):
                            data = payload.get("data", {})
                        else:
                            st.session_state.failed_key = file_key
                            st.error(payload.get("error", "I could not read this PDF."))
                    except requests.exceptions.ConnectionError:
                        st.session_state.failed_key = file_key
                        st.error("Cannot reach the backend. Keep the API window open.")
                    except Exception as e:
                        st.session_state.failed_key = file_key
                        st.error(f"Upload failed: {e}")

                if data:
                    st.session_state.pdf_name = data.get("filename", uploaded.name)
                    st.session_state.pdf_pages = data.get("pages", 0)
                    st.session_state.pdf_chunks = data.get("chunks", 0)
                    st.session_state.processed_key = file_key
                    st.session_state.failed_key = None
                    st.session_state.exam = []
                    reset_results()

                    st.session_state.topic = os.path.splitext(st.session_state.pdf_name)[0].replace("_", " ")[:60]
                    st.session_state.focus_topic = ""
                    st.session_state.topic_seeds = build_topic_seeds(30)

                    bot(prompt)
                    user(f"Uploaded **{st.session_state.pdf_name}**")

                    reply = (
                        f"Got it — {st.session_state.pdf_pages} pages, split into "
                        f"{st.session_state.pdf_chunks} searchable sections."
                    )

                    if st.session_state.topic_seeds:
                        sample = ", ".join(st.session_state.topic_seeds[:3])
                        reply += (
                            f" I picked up {len(st.session_state.topic_seeds)} sections across the file "
                            f"(for example: {sample}), so I can spread the questions over the whole document."
                        )

                    bot(reply)
                    go("count")

    # --------------------------------------------------------
    elif stage == "count":

        prompt = "How many questions should the exam have?"
        st.markdown(prompt)

        count = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=30,
            value=int(st.session_state.num_questions),
            step=1,
            key="count_input",
            label_visibility="collapsed",
        )

        if st.button("Continue", type="primary", key="count_send"):
            st.session_state.num_questions = int(count)
            bot(prompt)
            user(f"{int(count)} questions")
            go("setup")

    # --------------------------------------------------------
    elif stage == "setup":

        prompt = (
            "What kind of questions do you want? Pick as many types and difficulty levels as you like — "
            "I mix them across the exam."
        )
        st.markdown(prompt)

        chosen_types = multi_choice(
            "Question types",
            QUESTION_TYPES,
            st.session_state.types or ["MCQ"],
            "types_pick",
        )

        chosen_difficulties = multi_choice(
            "Difficulty levels",
            DIFFICULTIES,
            st.session_state.difficulties or ["Medium"],
            "difficulties_pick",
        )

        focus = st.text_input(
            "Focus on one topic — optional",
            value=st.session_state.focus_topic,
            key="focus_input",
            placeholder="Leave empty and I cover the whole PDF",
        )

        st.caption(
            "Empty means the questions are spread over every section I found in your file. "
            "Fill it in only if you want the whole exam to stay on one subject."
        )

        if st.button(
            f"Build my exam ({st.session_state.num_questions} questions)",
            type="primary",
            key="generate_button",
        ):
            if not chosen_types:
                st.warning("Pick at least one question type.")
            elif not chosen_difficulties:
                st.warning("Pick at least one difficulty level.")
            else:
                st.session_state.types = chosen_types
                st.session_state.difficulties = chosen_difficulties
                st.session_state.focus_topic = focus.strip()
                st.session_state.question_type = chosen_types[0]
                st.session_state.difficulty = chosen_difficulties[0]

                if st.session_state.focus_topic:
                    topics = [{"topic": st.session_state.focus_topic}]
                    coverage = f"on {st.session_state.focus_topic}"
                else:
                    seeds = st.session_state.topic_seeds[: int(st.session_state.num_questions)]
                    if not seeds:
                        seeds = [st.session_state.topic or "the main concepts"]
                    topics = [{"topic": seed} for seed in seeds]
                    coverage = "across the whole PDF"

                st.session_state.topic = topics[0]["topic"]

                payload = {
                    "settings": {
                        "num_questions": int(st.session_state.num_questions),
                        "question_types": chosen_types,
                        "difficulty_levels": chosen_difficulties,
                        "topics": topics,
                    }
                }

                estimate = max(15, int(st.session_state.num_questions) * 3)
                spinner_text = (
                    f"Writing {st.session_state.num_questions} questions "
                    f"({', '.join(chosen_types)}) {coverage} — about {estimate} seconds..."
                )

                with st.spinner(spinner_text):
                    result = api_call("POST", "/api/generate-exam", json=payload)

                if result is not None:
                    exam = clean_exam_data(result.get("exam", []) if isinstance(result, dict) else [])
                    st.session_state.exam = exam
                    reset_results()

                    bot(prompt)
                    user(f"{', '.join(chosen_types)} · {', '.join(chosen_difficulties)}")

                    if not exam:
                        bot(
                            "I could not write any question from this PDF. Try fewer questions, or "
                            "set a focus topic that really appears in the file."
                        )
                        go("setup")
                    else:
                        requested = int(st.session_state.num_questions)
                        missing = requested - len(exam)
                        note = f"Here are your {len(exam)} questions, {coverage}:"
                        if missing > 0:
                            note += (
                                f" You asked for {requested}; {missing} did not come back usable even "
                                "after a second attempt — that is almost always the free Groq rate limit. "
                                "Wait a few seconds and ask again, or request fewer questions at a time."
                            )
                        bot(note)
                        bot('<div class="q-grid">' + exam_html(exam) + "</div>", as_html=True)
                        go("menu")

    # --------------------------------------------------------
    elif stage == "menu":

        prompt = "What do you want to do with this exam?"
        st.markdown(prompt)

        if st.button("Check quality", use_container_width=True, key="menu_quality"):
            bot(prompt)
            user("Check quality")
            go("quality")

        if st.button("Edit a question", use_container_width=True, key="menu_edit"):
            bot(prompt)
            user("Edit a question")
            go("edit_pick")

        if st.button("Export exam", use_container_width=True, key="menu_export"):
            bot(prompt)
            user("Export the exam")
            go("export")

        if st.button("Start over with another PDF", use_container_width=True, key="menu_reset"):
            for key in ["chat", "exam", "pdf_name", "pdf_pages", "pdf_chunks", "processed_key", "failed_key"]:
                st.session_state[key] = defaults[key]
            st.session_state.pop("chat_pdf", None)
            reset_results()
            go("pdf")

    # --------------------------------------------------------
    elif stage == "quality":

        exam = st.session_state.exam

        if not exam:
            st.markdown("There is no exam yet. Let's build one first.")
            if st.button("Start", type="primary", key="quality_empty"):
                go("pdf")
            st.stop()

        prompt = (
            "Which check should I run? Each one asks the AI about every question, so it takes "
            "a few seconds per question."
        )
        st.markdown(prompt)

        if st.button("Run all checks", type="primary", use_container_width=True, key="q_all"):
            bot(prompt)
            user("Run all checks")

            with st.spinner("Scoring how well each question is written..."):
                quality = api_call("POST", "/api/quality-score", json={"questions": exam})

            if quality is not None:
                st.session_state.quality = quality
                bot(quality_html(exam, quality), as_html=True)

                if isinstance(quality, dict) and isinstance(quality.get("duplicates"), list):
                    st.session_state.duplicates = {"duplicates": quality["duplicates"]}
                    bot(duplicates_html(st.session_state.duplicates), as_html=True)

            with st.spinner("Looking for every answer in your PDF..."):
                grounding = api_call("POST", "/api/validate", json={"questions": exam})

            if grounding is not None:
                st.session_state.grounding = grounding
                bot(grounding_html(exam, grounding), as_html=True)

            go("quality")

        if st.button("Writing quality", use_container_width=True, key="q_score"):
            bot(prompt)
            user("Score the writing quality")
            with st.spinner("Scoring each question..."):
                quality = api_call("POST", "/api/quality-score", json={"questions": exam})
            if quality is not None:
                st.session_state.quality = quality
                bot(quality_html(exam, quality), as_html=True)
                if isinstance(quality, dict) and isinstance(quality.get("duplicates"), list):
                    st.session_state.duplicates = {"duplicates": quality["duplicates"]}
            go("quality")

        if st.button("Repeated questions", use_container_width=True, key="q_dupes"):
            bot(prompt)
            user("Find repeated questions")
            with st.spinner("Comparing the questions with each other..."):
                duplicates = api_call("POST", "/api/duplicates", json={"questions": exam})
            if duplicates is not None:
                st.session_state.duplicates = duplicates
                bot(duplicates_html(duplicates), as_html=True)
            go("quality")

        if st.button("Against the PDF", use_container_width=True, key="q_ground"):
            bot(prompt)
            user("Check the answers against the PDF")
            with st.spinner("Looking for every answer in your PDF..."):
                grounding = api_call("POST", "/api/validate", json={"questions": exam})
            if grounding is not None:
                st.session_state.grounding = grounding
                bot(grounding_html(exam, grounding), as_html=True)
            go("quality")

        if st.button("← Back", use_container_width=True, key="q_back"):
            go("menu")

    # --------------------------------------------------------
    elif stage == "edit_pick":

        exam = st.session_state.exam

        if not exam:
            st.markdown("There is no exam to edit yet.")
            if st.button("Start", type="primary", key="edit_empty"):
                go("pdf")
            st.stop()

        prompt = "Which question do you want to change?"
        st.markdown(prompt)

        labels = [
            f"{index + 1}. {clean_display_text(question.get('question', ''))[:70]}"
            for index, question in enumerate(exam)
        ]

        picked = st.selectbox("Question", labels, key="edit_pick_box", label_visibility="collapsed")

        p1, p2 = st.columns([1, 1])

        with p1:
            if st.button("Continue", type="primary", use_container_width=True, key="edit_pick_go"):
                st.session_state.edit_index = labels.index(picked)
                bot(prompt)
                user(f"Question {st.session_state.edit_index + 1}")
                go("edit_action")

        with p2:
            if st.button("← Back", use_container_width=True, key="edit_pick_back"):
                go("menu")

    # --------------------------------------------------------
    elif stage == "edit_action":

        exam = st.session_state.exam

        if not exam:
            st.markdown("There is no exam to edit yet.")
            if st.button("Start", type="primary", key="edit_action_empty"):
                go("pdf")
            st.stop()

        index = min(st.session_state.edit_index, len(exam) - 1)
        question = exam[index]
        current_type = clean_display_text(question.get("question_type", "MCQ")) or "MCQ"
        current_difficulty = clean_display_text(question.get("difficulty", "Medium")) or "Medium"

        st.markdown(f"**Question {index + 1}** — currently {current_type}, {current_difficulty}.")
        render_html(question_html(index, question))

        prompt = f"What should I change about question {index + 1}?"
        st.markdown(prompt)

        actions = [
            "Make it MCQ",
            "Make it True/False",
            "Make it Short Answer",
            "Change its difficulty",
            "Let me fix the wording myself",
        ]

        action = st.radio("Change", actions, key="edit_action_radio")

        new_difficulty = current_difficulty
        manual_question = clean_display_text(question.get("question", ""))
        manual_answer = clean_display_text(question.get("correct_answer", question.get("answer", "")))

        if action == "Change its difficulty":
            new_difficulty = st.radio(
                "New difficulty",
                DIFFICULTIES,
                index=DIFFICULTIES.index(current_difficulty) if current_difficulty in DIFFICULTIES else 1,
                horizontal=True,
                key="edit_difficulty_radio",
            )

        if action == "Let me fix the wording myself":
            manual_question = st.text_area("Question", value=manual_question, key="edit_text_area", height=110)
            manual_answer = st.text_input("Correct answer", value=manual_answer, key="edit_answer_input")

        e1, e2 = st.columns([1, 1])

        with e1:
            apply_clicked = st.button("Apply", type="primary", use_container_width=True, key="edit_apply")

        with e2:
            if st.button("← Back", use_container_width=True, key="edit_action_back"):
                go("menu")

        if apply_clicked:

            if action == "Let me fix the wording myself":
                updated = dict(question)
                updated["question"] = manual_question
                updated["correct_answer"] = manual_answer
                st.session_state.exam[index] = clean_question_data(updated)

                bot(prompt)
                user("I rewrote it myself")
                bot("Saved your version:")
                bot(question_html(index, st.session_state.exam[index]), as_html=True)
                reset_results()
                go("menu")

            target_type = current_type
            target_difficulty = new_difficulty

            if action == "Make it MCQ":
                target_type = "MCQ"
            elif action == "Make it True/False":
                target_type = "True/False"
            elif action == "Make it Short Answer":
                target_type = "Short Answer"

            payload = {
                "question": dict(question),
                "quality_result": st.session_state.quality if isinstance(st.session_state.quality, dict) else {},
                "topic": st.session_state.topic or clean_display_text(question.get("topic", "")) or "general",
                "learning_objective": None,
                "difficulty": target_difficulty,
                "question_type": target_type,
            }

            with st.spinner(f"Rewriting question {index + 1} as {target_type} ({target_difficulty})..."):
                result = api_call("POST", "/api/regenerate", json=payload)

            if result is not None:
                new_question = {}

                if isinstance(result, dict):
                    for key in ["final_question", "regenerated_question", "new_question", "question"]:
                        candidate = result.get(key)
                        if isinstance(candidate, dict):
                            new_question = dict(candidate)
                            break

                if not new_question:
                    st.error("The AI did not return a usable question. Try again.")
                else:
                    new_question["question_type"] = target_type
                    new_question["difficulty"] = target_difficulty

                    for carried in ["source_pages", "source_page", "topic", "learning_objective"]:
                        if not new_question.get(carried) and question.get(carried):
                            new_question[carried] = question.get(carried)

                    if target_type == "True/False":
                        new_question["choices"] = ["True", "False"]
                        if str(new_question.get("correct_answer", "")).strip().capitalize() not in ("True", "False"):
                            new_question["correct_answer"] = "True"
                    elif target_type == "Short Answer":
                        new_question["choices"] = []

                    st.session_state.exam[index] = clean_question_data(new_question)

                    bot(prompt)
                    user(action if action != "Change its difficulty" else f"Make it {target_difficulty}")
                    bot(f"Done — question {index + 1} is now {target_type}, {target_difficulty}:")
                    bot(question_html(index, st.session_state.exam[index]), as_html=True)
                    reset_results()
                    go("menu")

    # --------------------------------------------------------
    elif stage == "export":

        exam = st.session_state.exam

        if not exam:
            st.markdown("There is no exam to export yet.")
            if st.button("Start", type="primary", key="export_empty"):
                go("pdf")
            st.stop()

        st.markdown(
            f"Your exam has **{len(exam)} questions** from **{html.escape(str(st.session_state.pdf_name))}**. "
            "Take whichever copy you need."
        )

        student_pdf = create_exam_pdf(exam, source_pdf=st.session_state.pdf_name, include_answers=False)
        answers_pdf = create_exam_pdf(exam, source_pdf=st.session_state.pdf_name, include_answers=True)

        x1, x2 = st.columns(2)

        with x1:
            st.download_button(
                "Student paper (PDF)",
                data=student_pdf,
                file_name="exam.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="dl_student",
            )

        with x2:
            st.download_button(
                "Answer key (PDF)",
                data=answers_pdf,
                file_name="exam_answer_key.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="dl_answers",
            )

        st.download_button(
            "JSON backup",
            data=json.dumps(
                {"source_pdf": st.session_state.pdf_name, "questions": exam},
                ensure_ascii=False,
                indent=2,
            ),
            file_name="exam.json",
            mime="application/json",
            use_container_width=True,
            key="dl_json",
        )

        if st.button("← Back", key="export_back"):
            go("menu")
