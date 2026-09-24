
import io
import json
import re
import html
import requests
from textwrap import dedent
import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import cm


# ============================================================
# CONFIG
# ============================================================

API_URL = "http://127.0.0.1:8000"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Examora",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# HTML / MARKDOWN RENDERING (FIXES HTML CODE BLOCK LEAKS)
# ============================================================

def render_html(content):
    """Render raw HTML in Streamlit cleanly without line-indentation triggering code blocks."""
    if isinstance(content, str):
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        content = "\n".join(lines)
    return st.markdown(content, unsafe_allow_html=True)


def render_markdown(content, **kwargs):
    """Render Streamlit markdown after removing line indentation."""
    if isinstance(content, str):
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        content = "\n".join(lines)
    kwargs.setdefault("unsafe_allow_html", True)
    return st.markdown(content, **kwargs)


# ============================================================
# PREMIUM STYLING
# ============================================================

render_html(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@500;600;700;800;900&display=swap'
    );

    :root {
        --primary: #7c3aed;
        --primary-dark: #5b21b6;
        --primary-light: #ede9fe;
        --indigo: #6366f1;
        --text: #0f172a;
        --muted: #64748b;
        --border: #e2e8f0;
        --surface: #ffffff;
        --background: #f8fafc;
        --green: #16a34a;
        --yellow: #d97706;
        --red: #dc2626;
    }

    * {
        font-family: 'Inter', sans-serif;
    }

    /* Hide Sidebar Completely */
    section[data-testid="stSidebar"],
    div[data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* App Ambient Background */
    .stApp {
        background:
            radial-gradient(circle at 15% 10%, rgba(124, 58, 237, 0.08), transparent 35%),
            radial-gradient(circle at 85% 20%, rgba(99, 102, 241, 0.07), transparent 30%),
            radial-gradient(circle at 50% 85%, rgba(168, 85, 247, 0.06), transparent 40%),
            #f8fafc;
        background-attachment: fixed;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 1.2rem;
        padding-bottom: 4rem;
    }

    #MainMenu, footer, header {
        visibility: hidden;
    }

    /* Top Floating Navigation Bar */
    .top-navbar-container {
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 14px 28px;
        margin-bottom: 20px;
        box-shadow: 0 10px 35px rgba(30, 20, 60, 0.05);
        animation: fadeInDown 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .top-navbar-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
    }

    .nav-brand {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .nav-logo {
        width: 48px;
        height: 48px;
        border-radius: 16px;
        background: linear-gradient(135deg, #6d28d9, #8b5cf6, #6366f1);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        box-shadow: 0 10px 25px rgba(109, 40, 217, 0.3);
        transition: transform 0.3s ease;
    }

    .nav-logo:hover {
        transform: scale(1.08) rotate(5deg);
    }

    .nav-title {
        font-family: 'Poppins', sans-serif;
        font-size: 22px;
        font-weight: 800;
        color: var(--primary);
        line-height: 1.2;
    }

    .nav-title span { color: var(--text); }

    .nav-subtitle {
        color: var(--muted);
        font-size: 11px;
        font-weight: 500;
    }

    .nav-center-status {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .status-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 15px;
        background: #f0fdf4;
        color: #15803d;
        border: 1px solid #bbf7d0;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
    }

    .status-dot-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22c55e;
        animation: pulseDot 2s infinite;
    }

    @keyframes pulseDot {
        0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
        70% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
        100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }

    .nav-pdf-badge {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 15px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
    }

    .nav-pdf-badge.ready {
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
    }

    .nav-pdf-badge.empty {
        background: #f1f5f9;
        color: #64748b;
        border: 1px solid #e2e8f0;
    }

    /* Top Horizontal Tabs */
    div[data-testid="stRadio"] {
        display: flex;
        justify-content: center;
        margin-bottom: 28px;
    }

    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        gap: 10px !important;
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(226, 232, 240, 0.9) !important;
        padding: 8px 12px !important;
        border-radius: 22px !important;
        box-shadow: 0 12px 35px rgba(124, 58, 237, 0.07) !important;
    }

    div[data-testid="stRadio"] label {
        background: transparent !important;
        padding: 10px 24px !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        color: #475569 !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: pointer !important;
        border: 1px solid transparent !important;
        display: flex !important;
        align-items: center !important;
    }

    div[data-testid="stRadio"] label:hover {
        color: #7c3aed !important;
        background: rgba(124, 58, 237, 0.08) !important;
        transform: translateY(-2px) !important;
    }

    div[data-testid="stRadio"] label[aria-checked="true"],
    div[data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, #6d28d9, #7c3aed, #6366f1) !important;
        color: #ffffff !important;
        box-shadow: 0 8px 25px rgba(109, 40, 217, 0.35) !important;
    }

    div[data-testid="stRadio"] label input[type="radio"],
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }

    /* Hero Banner */
    .hero {
        position: relative;
        overflow: hidden;
        background:
            radial-gradient(circle at 85% 15%, rgba(255,255,255,0.22), transparent 25%),
            radial-gradient(circle at 100% 100%, rgba(99,102,241,0.5), transparent 35%),
            linear-gradient(135deg, #3b0764 0%, #5b21b6 35%, #7c3aed 70%, #4f46e5 100%);
        border-radius: 32px;
        padding: 44px 48px;
        color: white;
        margin-bottom: 32px;
        box-shadow: 0 25px 60px rgba(91, 33, 182, 0.22);
        animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .hero-content {
        position: relative;
        z-index: 2;
        max-width: 880px;
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.28) 50%, rgba(255,255,255,0.15) 100%);
        background-size: 200% 100%;
        border: 1px solid rgba(255,255,255,0.25);
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 16px;
        animation: shimmer 4s infinite linear;
    }

    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }

    .hero h1 {
        font-family: 'Poppins', sans-serif;
        font-size: 44px;
        line-height: 1.15;
        font-weight: 900;
        margin: 0 0 14px 0;
        letter-spacing: -1.5px;
    }

    .hero p {
        margin: 0;
        font-size: 16px;
        line-height: 1.75;
        opacity: 0.92;
        max-width: 780px;
    }

    .hero-pills {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 24px;
    }

    .hero-pill {
        padding: 9px 15px;
        border-radius: 12px;
        background: rgba(255,255,255,0.12);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.18);
        font-size: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .hero-pill:hover {
        background: rgba(255, 255, 255, 0.25);
        transform: translateY(-2px);
    }

    /* Cards */
    .main-card, .question-card, .quality-hero, .grounding-card, .export-card {
        background: rgba(255, 255, 255, 0.92);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border);
        box-shadow: 0 10px 30px rgba(30,20,60,0.04);
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
        animation: fadeInUp 0.5s ease-out forwards;
    }

    .main-card:hover, .question-card:hover, .export-card:hover {
        transform: translateY(-4px);
        border-color: #c4b5fd;
        box-shadow: 0 20px 40px rgba(109, 40, 217, 0.08);
    }

    .upload-card {
        background: linear-gradient(145deg, #ffffff, #faf8ff);
        border: 2px dashed #c4b5fd;
        border-radius: 26px;
        padding: 28px;
        margin-bottom: 20px;
        box-shadow: 0 12px 35px rgba(109,40,217,0.06);
        transition: all 0.3s ease;
    }

    .upload-card:hover {
        border-color: var(--primary);
        box-shadow: 0 16px 40px rgba(109,40,217,0.12);
        transform: translateY(-2px);
    }

    .upload-icon {
        width: 62px;
        height: 62px;
        border-radius: 20px;
        background: #ede9fe;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        margin-bottom: 14px;
    }

    .upload-title {
        font-family: 'Poppins', sans-serif;
        font-size: 19px;
        font-weight: 800;
        color: #1e1b4b;
    }

    .upload-description {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.65;
        margin: 6px 0 16px 0;
        max-width: 720px;
    }

    .page-title {
        font-family: 'Poppins', sans-serif;
        font-size: 32px;
        font-weight: 900;
        color: var(--text);
        margin-top: 5px;
        margin-bottom: 4px;
        letter-spacing: -0.6px;
    }

    .page-subtitle {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.6;
        margin-bottom: 24px;
    }

    .section-label {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 28px 0 14px 0;
    }

    .section-icon {
        width: 36px;
        height: 36px;
        border-radius: 12px;
        background: var(--primary-light);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
    }

    .section-title {
        font-family: 'Poppins', sans-serif;
        font-size: 17px;
        font-weight: 800;
        color: #1e1b4b;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 18px;
        box-shadow: 0 8px 25px rgba(30,20,60,0.035);
        transition: all 0.3s ease;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        border-color: #a78bfa;
        box-shadow: 0 14px 30px rgba(124, 58, 237, 0.09);
    }

    div[data-testid="stMetricLabel"] {
        font-size: 12px;
        font-weight: 600;
        color: #64748b;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Poppins', sans-serif;
        font-weight: 900;
        color: var(--primary-dark);
    }

    /* Question Cards */
    .question-card {
        border-radius: 22px;
        padding: 22px;
        margin: 18px 0 0 0;
    }

    .question-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
    }

    .question-number {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .question-number-badge {
        width: 38px;
        height: 38px;
        border-radius: 13px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #ede9fe;
        color: #6d28d9;
        font-family: 'Poppins', sans-serif;
        font-weight: 800;
        font-size: 14px;
    }

    .question-title {
        font-family: 'Poppins', sans-serif;
        font-size: 16px;
        font-weight: 800;
        color: #1e1b4b;
    }

    .badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        margin-left: 5px;
    }

    .badge-purple { background: #ede9fe; color: #6d28d9; }
    .badge-blue { background: #dbeafe; color: #1d4ed8; }
    .badge-green { background: #dcfce7; color: #15803d; }
    .badge-yellow { background: #fef3c7; color: #92400e; }
    .badge-red { background: #fee2e2; color: #b91c1c; }

    /* Grounding Cards */
    .grounding-card {
        border-radius: 18px;
        padding: 18px 20px;
        margin: 10px 0;
    }

    .grounded { border-left: 6px solid #22c55e; }
    .not-grounded { border-left: 6px solid #f59e0b; }
    .not-evaluated { border-left: 6px solid #94a3b8; }

    /* Buttons */
    div.stButton > button[kind="primary"],
    div[data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #6d28d9 0%, #7c3aed 50%, #4f46e5 100%) !important;
        background-size: 200% 100% !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        min-height: 44px !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 10px 25px rgba(109, 40, 217, 0.25) !important;
    }

    div.stButton > button[kind="primary"]:hover,
    div[data-testid="stDownloadButton"] button:hover {
        background-position: 100% 0 !important;
        transform: translateY(-3px) scale(1.01) !important;
        box-shadow: 0 15px 35px rgba(109, 40, 217, 0.4) !important;
    }

    div.stButton > button {
        border-radius: 14px !important;
        font-weight: 700 !important;
        min-height: 44px !important;
        transition: all 0.3s ease !important;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(30,20,60,0.08);
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-18px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .app-footer {
        margin-top: 50px;
        padding-top: 24px;
        border-top: 1px solid var(--border);
        text-align: center;
        color: #94a3b8;
        font-size: 11px;
        font-weight: 600;
    }

    </style>
    """
)


# ============================================================
# TEXT COLOUR HARDENING
# ============================================================

render_html(
    """
    <style>

    html, body, .stApp, [data-testid="stAppViewContainer"] {
        color: #0f172a !important;
        color-scheme: light !important;
    }

    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stText"] {
        color: #334155;
    }

    div[data-testid="stMarkdownContainer"] strong { color: #1e1b4b; }

    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 { color: #1e1b4b; }

    div[data-testid="stCaptionContainer"],
    div[data-testid="stCaptionContainer"] p { color: #64748b !important; }

    div[data-testid="stWidgetLabel"] p,
    div[data-testid="stWidgetLabel"] label,
    .stTextInput label, .stTextArea label,
    .stSelectbox label, .stMultiSelect label,
    .stNumberInput label, .stFileUploader label {
        color: #475569 !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="textarea"] { background: #ffffff !important; }

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: #e2e8f0 !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder { color: #94a3b8 !important; }

    div[data-baseweb="select"] > div {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: #e2e8f0 !important;
    }

    div[data-baseweb="popover"] div[role="listbox"],
    div[data-baseweb="popover"] ul,
    ul[role="listbox"] {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
    }

    li[role="option"], div[role="option"] { color: #0f172a !important; }
    li[role="option"]:hover, div[role="option"]:hover { background: #f5f3ff !important; }

    span[data-baseweb="tag"] {
        background: #6d28d9 !important;
        color: #ffffff !important;
    }

    span[data-baseweb="tag"] svg { fill: #ffffff !important; }

    section[data-testid="stFileUploaderDropzone"],
    div[data-testid="stFileUploader"] section {
        background: #faf8ff !important;
        color: #334155 !important;
    }

    section[data-testid="stFileUploaderDropzone"] span,
    section[data-testid="stFileUploaderDropzone"] small,
    div[data-testid="stFileUploaderFile"] span,
    div[data-testid="stFileUploaderFile"] small { color: #64748b !important; }

    section[data-testid="stFileUploaderDropzone"] button {
        background: #ffffff !important;
        color: #5b21b6 !important;
        border: 1px solid #c4b5fd !important;
    }

    div[data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
    }

    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary p {
        color: #1e1b4b !important;
        font-weight: 700 !important;
    }

    div.stButton > button:not([kind="primary"]) {
        background: #ffffff !important;
        color: #4c1d95 !important;
        border: 1px solid #e2e8f0 !important;
    }

    div[data-testid="stAlert"] p { color: inherit !important; }

    div[data-testid="stSpinner"] p,
    div[data-testid="stSpinner"] div { color: #5b21b6 !important; }

    div[data-testid="stMetricValue"] { color: #5b21b6 !important; }
    div[data-testid="stMetricLabel"] { color: #64748b !important; }

    .grounding-card strong { color: #0f172a !important; }
    .grounding-card > div { color: #475569 !important; }

    </style>
    """
)


# ============================================================
# API
# ============================================================

def api_call(method, endpoint, **kwargs):
    try:
        response = requests.request(
            method,
            f"{API_URL}{endpoint}",
            timeout=180,
            **kwargs,
        )

        if response.status_code == 429:
            st.warning(
                "⏳ The AI service is temporarily rate-limited. "
                "Please wait a little and try again."
            )
            return None

        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            raise RuntimeError(result.get("error", "API request failed."))

        return result.get("data")

    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the backend. Make sure FastAPI is running on port 8000.")
        return None
    except requests.exceptions.Timeout:
        st.error("⏳ The request took too long. Please try again.")
        return None
    except Exception as e:
        st.error(f"❌ API Error: {e}")
        return None


# ============================================================
# TEXT CLEANING & NORMALIZATION
# ============================================================

def clean_display_text(value):
    if value is None:
        return ""

    text = str(value)

    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded

    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(p|div|li|h[1-6]|tr|td|th|ul|ol|span|strong|em|b|i|label)[^>]*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"```[a-zA-Z0-9_+-]*", "", text)
    text = text.replace("```", "")
    text = re.sub(r"`+([^`]*)`+", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"___(.+?)___", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\w)\*([^*\n]+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}([-*_])\1{2,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*(question|answer|q|a|correct answer|choice)\s*[:.\-)]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*[-*]\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"&(?:nbsp|amp|lt|gt|quot|#\d+);", " ", text, flags=re.IGNORECASE)

    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    text = text.replace("\u2028", "\n")
    text = text.replace("\u2029", "\n")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = re.sub(r"^[\s\-*:•]+|[\s\-*:•]+$", "", text, flags=re.MULTILINE)

    return text.strip()


def clean_question_data(question):
    if not isinstance(question, dict):
        return question

    cleaned = dict(question)

    for field in [
        "question",
        "correct_answer",
        "answer",
        "topic",
        "difficulty",
        "question_type",
    ]:
        if field in cleaned:
            cleaned[field] = clean_display_text(cleaned[field])

    # Normalize True/False type strings
    q_type = str(cleaned.get("question_type", "")).strip()
    if q_type.lower() in ["true/false", "true-false", "true or false", "t/f", "tf", "true_false"]:
        cleaned["question_type"] = "True/False"

    choices = cleaned.get("choices")
    if isinstance(choices, list) and choices:
        cleaned["choices"] = [clean_display_text(choice) for choice in choices]
    elif cleaned.get("question_type") == "True/False":
        cleaned["choices"] = ["True", "False"]

    return cleaned


def clean_exam_data(exam):
    if not isinstance(exam, list):
        return []

    return [clean_question_data(question) for question in exam if isinstance(question, dict)]


# ============================================================
# GROUNDING & RESULT HELPERS
# ============================================================

def get_duplicate_pairs(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ["duplicates", "similar_pairs", "pairs", "results"]:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def get_quality_items(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ["results", "questions", "quality_results", "scores", "items"]:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def get_quality_score(item):
    if not isinstance(item, dict):
        return None
    for key in ["quality_score", "score", "quality", "overall_score"]:
        value = item.get(key)
        if value is None:
            continue
        try:
            score = float(value)
            if 0 <= score <= 1:
                score *= 100
            return max(0, min(score, 100))
        except (ValueError, TypeError):
            continue
    return None


def get_overall_quality(data, items):
    if isinstance(data, dict):
        for key in ["overall_score", "average_score", "score"]:
            value = data.get(key)
            if value is not None:
                try:
                    score = float(value)
                    if 0 <= score <= 1:
                        score *= 100
                    return max(0, min(score, 100))
                except (ValueError, TypeError):
                    pass

    scores = []
    for item in items:
        score = get_quality_score(item)
        if score is not None:
            scores.append(score)

    if scores:
        return sum(scores) / len(scores)

    return None


def get_grounding_items(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    for key in ["results", "questions", "grounding_results", "items"]:
        value = data.get(key)
        if isinstance(value, list):
            return value

    return []


def get_grounding_verdict(item):
    """Extract raw model verdict regardless of key structure."""
    if item is None:
        return None

    if isinstance(item, str):
        return item.strip()

    if isinstance(item, bool):
        return "supported" if item else "unsupported"

    if isinstance(item, dict):
        for key in [
            "verdict",
            "status",
            "result",
            "label",
            "is_grounded",
            "grounded",
            "supported",
            "is_supported",
            "evaluation",
            "judgment",
            "decision",
            "verdict_label",
            "verdict_text",
            "reasoning",
            "explanation",
        ]:
            val = item.get(key)
            if val is not None:
                if isinstance(val, bool):
                    return "supported" if val else "unsupported"
                if isinstance(val, (str, int, float)) and str(val).strip():
                    return str(val).strip()
                if isinstance(val, dict):
                    nested = get_grounding_verdict(val)
                    if nested:
                        return nested

    return None


def normalize_verdict(verdict):
    """Normalize model verdict using flexible keyword matching."""
    if verdict is None:
        return "not_evaluated"

    text = str(verdict).strip().lower()

    if not text or text in ["none", "null", "not_evaluated", "not evaluated"]:
        return "not_evaluated"

    # Check negative indicators first
    if any(kw in text for kw in ["unsupported", "not supported", "incorrect", "false", "not_grounded", "not grounded", "unverified", "no"]):
        return "unsupported"

    # Check positive indicators
    if any(kw in text for kw in ["supported", "correct", "grounded", "true", "verified", "yes", "valid"]):
        return "supported"

    return "not_evaluated"


def find_grounding_item(items, question, index):
    question_text = ""
    if isinstance(question, dict):
        question_text = clean_display_text(question.get("question", ""))

    if question_text:
        for item in items:
            if isinstance(item, dict):
                item_text = clean_display_text(item.get("question", ""))
                if item_text and item_text == question_text:
                    return item

    if index < len(items):
        return items[index]

    return None


def get_similarity(item):
    if not isinstance(item, dict):
        return None
    for key in ["similarity", "similarity_score", "score", "confidence"]:
        value = item.get(key)
        if value is None:
            continue
        try:
            value = float(value)
            if value <= 1:
                value *= 100
            return value
        except (ValueError, TypeError):
            pass
    return None


# ============================================================
# PDF EXPORT
# ============================================================

def create_exam_pdf(exam, source_pdf=None, include_answers=False):
    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ExamTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=22,
        leading=27,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ExamSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        leading=14,
        spaceAfter=20,
    )

    question_style = ParagraphStyle(
        "Question",
        parent=styles["Normal"],
        fontSize=11,
        leading=17,
        spaceAfter=8,
    )

    choice_style = ParagraphStyle(
        "Choice",
        parent=styles["Normal"],
        fontSize=10.5,
        leading=16,
        leftIndent=15,
        spaceAfter=5,
    )

    answer_style = ParagraphStyle(
        "Answer",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        spaceAfter=12,
    )

    story = []

    story.append(Paragraph("Examora", title_style))

    if source_pdf:
        story.append(Paragraph(f"Source: {html.escape(str(source_pdf))}", subtitle_style))
    else:
        story.append(Paragraph("Generated Exam", subtitle_style))

    for index, question in enumerate(exam):
        question = clean_question_data(question)
        question_text = question.get("question", "")
        qtype = question.get("question_type", "MCQ")
        difficulty = question.get("difficulty", "Medium")

        story.append(
            Paragraph(
                f"<b>Question {index + 1}</b> &nbsp;&nbsp; "
                f"<font size='9'>{html.escape(qtype)} · {html.escape(difficulty)}</font>",
                question_style,
            )
        )

        story.append(Paragraph(html.escape(question_text), question_style))

        choices = question.get("choices", [])

        if isinstance(choices, list):
            for choice_index, choice in enumerate(choices):
                letter = chr(65 + choice_index)
                choice_text = clean_display_text(choice)
                story.append(Paragraph(f"{letter}. {html.escape(choice_text)}", choice_style))

        if include_answers:
            answer = question.get("correct_answer", question.get("answer", ""))
            answer = clean_display_text(answer)
            if answer:
                story.append(Paragraph(f"<b>Answer:</b> {html.escape(answer)}", answer_style))

        story.append(Spacer(1, 0.35 * cm))

    document.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "page": "Create",
    "exam": [],
    "blueprint": None,
    "quality": None,
    "duplicates": None,
    "grounding": None,
    "generated": False,
    "uploaded_pdf_name": None,
    "pdf_processed": False,
    "num_questions": 10,
    "question_types": ["MCQ"],
    "difficulty_levels": ["Medium"],
    "topics": [{"topic": ""}],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

for topic in st.session_state.topics:
    if isinstance(topic, dict):
        topic.pop("learning_objectives", None)


# ============================================================
# TOP FLOATING NAVBAR & WORKSPACE NAVIGATION
# ============================================================

pdf_badge_html = (
    f'<div class="nav-pdf-badge ready">📄 {html.escape(st.session_state.uploaded_pdf_name or "PDF Ready")}</div>'
    if st.session_state.pdf_processed
    else '<div class="nav-pdf-badge empty">📄 No PDF Source</div>'
)

render_html(
    f"""
    <div class="top-navbar-container">
        <div class="top-navbar-content">

            <div class="nav-brand">
                <div class="nav-logo">🎓</div>
                <div class="nav-brand-text">
                    <div class="nav-title">Exa<span>mora</span></div>
                    <div class="nav-subtitle">Intelligent Assessment Platform</div>
                </div>
            </div>

            <div class="nav-center-status">
                <div class="status-badge">
                    <span class="status-dot-pulse"></span>
                    AI Engine Online
                </div>
                {pdf_badge_html}
            </div>

        </div>
    </div>
    """
)

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()


# Horizontal Pill Tab Menu
tabs = ["✨ Create", "📝 Review", "⭐ Quality", "📥 Export"]
tab_map = {
    "Create": "✨ Create",
    "Review": "📝 Review",
    "Quality": "⭐ Quality",
    "Export": "📥 Export",
}

target_tab = tab_map.get(st.session_state.page, "✨ Create")
st.session_state["main_top_nav_bar"] = target_tab

selected_nav = st.radio(
    "Navigation Tabs",
    tabs,
    horizontal=True,
    label_visibility="collapsed",
    key="main_top_nav_bar",
)

clean_nav_name = selected_nav.split(" ")[-1]
st.session_state.page = clean_nav_name


# ============================================================
# HERO BANNER
# ============================================================

render_html(
    """
    <div class="hero">
        <div class="hero-content">

            <div class="hero-badge">
                ✨ Next-Gen Assessment Workspace
            </div>

            <h1>
                Build smarter exams<br>
                from your learning material.
            </h1>

            <p>
                Upload your course material, generate questions grounded in your PDF,
                review every question, validate quality, and export a polished exam.
            </p>

            <div class="hero-pills">
                <div class="hero-pill">📄 PDF Grounding</div>
                <div class="hero-pill">🤖 AI Generation</div>
                <div class="hero-pill">⭐ Quality Analysis</div>
                <div class="hero-pill">📚 Source Validation</div>
            </div>

        </div>
    </div>
    """
)


# ============================================================
# PAGE 1: CREATE
# ============================================================

if st.session_state.page == "Create":

    render_html('<div class="page-title">Create Exam</div>')
    render_html(
        '<div class="page-subtitle">'
        'Configure your exam and use your learning material as the AI knowledge source.'
        '</div>'
    )

    # Upload Card
    render_html(
        """
        <div class="upload-card">
            <div class="upload-icon">📄</div>
            <div class="upload-title">Upload your learning material</div>
            <div class="upload-description">
                Add lecture notes, textbook chapters, course PDFs, study guides,
                or any educational material you want the generated exam to be based on.
            </div>
        </div>
        """
    )

    uploaded_pdf = st.file_uploader(
        "Choose PDF",
        type=["pdf"],
        key="pdf_uploader",
        label_visibility="collapsed",
    )

    if uploaded_pdf is not None:

        render_html(
            f"""
            <div class="file-ready">
                <div class="file-icon">📄</div>
                <div>
                    <div class="file-name">{html.escape(uploaded_pdf.name)}</div>
                    <div class="file-status">PDF selected · Ready to process</div>
                </div>
            </div>
            """
        )

        render_html("")

        if st.button("⚡ Process PDF", type="primary", use_container_width=True):
            with st.spinner("Processing your PDF..."):
                try:
                    response = requests.post(
                        f"{API_URL}/api/upload-pdf",
                        files={
                            "file": (
                                uploaded_pdf.name,
                                uploaded_pdf.getvalue(),
                                "application/pdf",
                            )
                        },
                        timeout=180,
                    )

                    if response.status_code == 429:
                        st.warning("⏳ The AI service is temporarily rate-limited.")
                    else:
                        response.raise_for_status()
                        result = response.json()

                        if result.get("success"):
                            data = result.get("data", {})
                            st.session_state.uploaded_pdf_name = data.get("filename", uploaded_pdf.name)
                            st.session_state.pdf_processed = True
                            st.session_state.exam = []
                            st.session_state.quality = None
                            st.session_state.duplicates = None
                            st.session_state.grounding = None
                            st.session_state.generated = False

                            st.success(
                                f"PDF ready — {data.get('pages', 0)} pages, {data.get('chunks', 0)} chunks."
                            )
                            st.rerun()
                        else:
                            st.session_state.pdf_processed = False
                            st.error(result.get("error", "PDF processing failed."))

                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to FastAPI backend.")
                except requests.exceptions.Timeout:
                    st.error("⏳ PDF processing timed out.")
                except Exception as e:
                    st.error(f"❌ Upload failed: {e}")

    # Configuration
    render_html(
        """
        <div class="section-label">
            <div class="section-icon">⚙️</div>
            <div class="section-title">Exam Configuration</div>
        </div>
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        st.session_state.num_questions = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=50,
            value=st.session_state.num_questions,
            step=1,
        )

        st.session_state.question_types = st.multiselect(
            "Question types",
            ["MCQ", "True/False", "Short Answer"],
            default=st.session_state.question_types,
        )

    with col2:
        st.session_state.difficulty_levels = st.multiselect(
            "Difficulty levels",
            ["Easy", "Medium", "Hard"],
            default=st.session_state.difficulty_levels,
        )

        topic_value = st.text_input(
            "Topic",
            value=st.session_state.topics[0].get("topic", ""),
            placeholder="e.g. Java Generics",
        )

    st.session_state.topics = [{"topic": topic_value}]

    # Preview Metrics
    render_html(
        """
        <div class="section-label">
            <div class="section-icon">📊</div>
            <div class="section-title">Exam Overview</div>
        </div>
        """
    )

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.metric("Questions", st.session_state.num_questions)
    with p2:
        st.metric("Question Types", len(st.session_state.question_types))
    with p3:
        st.metric("Difficulty Levels", len(st.session_state.difficulty_levels))
    with p4:
        st.metric("Source PDF", "Ready" if st.session_state.pdf_processed else "Missing")

    render_html("")

    if st.button("✨ Generate AI Exam", type="primary", use_container_width=True):

        if not st.session_state.pdf_processed:
            st.error("Please upload and process a PDF first.")
        elif not topic_value.strip():
            st.error("Please enter a topic.")
        elif not st.session_state.question_types:
            st.error("Please select at least one question type.")
        elif not st.session_state.difficulty_levels:
            st.error("Please select at least one difficulty level.")
        else:
            payload = {
                "settings": {
                    "num_questions": st.session_state.num_questions,
                    "question_types": st.session_state.question_types,
                    "difficulty_levels": st.session_state.difficulty_levels,
                    "topics": [{"topic": topic_value}],
                }
            }

            with st.spinner("🤖 Building your exam from the PDF..."):
                result = api_call("POST", "/api/generate-exam", json=payload)

            if result:
                raw_exam = result.get("exam", []) if isinstance(result, dict) else []
                st.session_state.exam = clean_exam_data(raw_exam)
                st.session_state.blueprint = result.get("blueprint") if isinstance(result, dict) else None
                st.session_state.quality = None
                st.session_state.duplicates = None
                st.session_state.grounding = None
                st.session_state.generated = True
                st.success(f"Generated {len(st.session_state.exam)} questions successfully.")
                navigate_to("Review")


# ============================================================
# PAGE 2: REVIEW
# ============================================================

elif st.session_state.page == "Review":

    render_html('<div class="page-title">Review Questions</div>')
    render_html(
        '<div class="page-subtitle">'
        'Inspect every generated question, edit it, or regenerate it before validation.'
        '</div>'
    )

    exam = clean_exam_data(st.session_state.exam)
    st.session_state.exam = exam

    if not exam:
        st.info("No exam has been generated yet.")
    else:
        grounded_count = sum(1 for q in exam if q.get("source_pages") or q.get("source_page"))

        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.metric("Questions", len(exam))
        with r2:
            types = set(str(q.get("question_type", "")) for q in exam)
            st.metric("Types", len(types))
        with r3:
            st.metric("Source", "Ready")
        with r4:
            st.metric("Linked", grounded_count)

        for index, question in enumerate(exam):
            question = clean_question_data(question)
            qtype = question.get("question_type", "MCQ")
            difficulty = question.get("difficulty", "Medium")

            render_html(
                f"""
                <div class="question-card">
                    <div class="question-header">
                        <div class="question-number">
                            <div class="question-number-badge">{index + 1}</div>
                            <div class="question-title">Question {index + 1}</div>
                        </div>
                        <div>
                            <span class="badge badge-purple">{html.escape(str(qtype))}</span>
                            <span class="badge badge-blue">{html.escape(str(difficulty))}</span>
                        </div>
                    </div>
                </div>
                """
            )

            edited_question = st.text_area(
                "Question",
                value=clean_display_text(question.get("question", "")),
                key=f"question_text_{index}",
                height=105,
            )
            question["question"] = clean_display_text(edited_question)

            choices = question.get("choices", [])
            if isinstance(choices, list) and choices:
                st.write("**Answer choices**")
                updated_choices = []
                for choice_index, choice in enumerate(choices):
                    new_choice = st.text_input(
                        f"Choice {chr(65 + choice_index)}",
                        value=clean_display_text(choice),
                        key=f"choice_{index}_{choice_index}",
                    )
                    updated_choices.append(clean_display_text(new_choice))
                question["choices"] = updated_choices

            current_answer = question.get("correct_answer", question.get("answer", ""))
            question["correct_answer"] = clean_display_text(
                st.text_input(
                    "Correct answer",
                    value=clean_display_text(current_answer),
                    key=f"answer_{index}",
                )
            )

            c1, c2 = st.columns(2)
            with c1:
                valid_types = ["MCQ", "True/False", "Short Answer"]
                current_type = qtype if qtype in valid_types else "MCQ"
                selected_type = st.selectbox(
                    "Question type",
                    valid_types,
                    index=valid_types.index(current_type),
                    key=f"type_{index}",
                )
                question["question_type"] = selected_type

            with c2:
                valid_difficulties = ["Easy", "Medium", "Hard"]
                current_difficulty = difficulty if difficulty in valid_difficulties else "Medium"
                selected_difficulty = st.selectbox(
                    "Difficulty",
                    valid_difficulties,
                    index=valid_difficulties.index(current_difficulty),
                    key=f"difficulty_{index}",
                )
                question["difficulty"] = selected_difficulty

            st.session_state.exam[index] = question

            with st.expander("🔄 Regenerate this question"):
                regen_topic = st.text_input(
                    "Topic",
                    value=st.session_state.topics[0].get("topic", ""),
                    key=f"regen_topic_{index}",
                )

                if st.button("Regenerate", key=f"regenerate_{index}"):
                    question_to_send = dict(question)
                    question_to_send["question_type"] = selected_type
                    question_to_send["difficulty"] = selected_difficulty

                    payload = {
                        "question": question_to_send,
                        "quality_result": st.session_state.quality or {},
                        "topic": regen_topic or st.session_state.topics[0].get("topic", ""),
                        "learning_objective": None,
                        "difficulty": selected_difficulty,
                        "question_type": selected_type,
                        "target_question_type": selected_type,
                        "type": selected_type,
                    }

                    with st.spinner(f"Regenerating question as {selected_type}..."):
                        regenerated = api_call("POST", "/api/regenerate", json=payload)

                    if regenerated is not None:
                        new_q_dict = {}

                        if isinstance(regenerated, dict):
                            for wrapper_key in [
                                "final_question",
                                "regenerated_question",
                                "new_question",
                                "question",
                            ]:
                                wrapped = regenerated.get(wrapper_key)
                                if isinstance(wrapped, dict):
                                    new_q_dict = dict(wrapped)
                                    break
                            else:
                                new_q_dict = dict(regenerated)
                        elif isinstance(regenerated, str):
                            new_q_dict = {
                                "question": regenerated,
                                "question_type": selected_type,
                                "difficulty": selected_difficulty,
                            }

                        new_q_dict["question_type"] = selected_type
                        new_q_dict["difficulty"] = selected_difficulty

                        for carried_key in [
                            "source_pages",
                            "source_page",
                            "topic",
                            "learning_objective",
                        ]:
                            if not new_q_dict.get(carried_key) and question.get(carried_key):
                                new_q_dict[carried_key] = question.get(carried_key)

                        if selected_type == "True/False":
                            new_q_dict["choices"] = ["True", "False"]
                            if not new_q_dict.get("correct_answer") or str(new_q_dict.get("correct_answer")).strip().capitalize() not in ["True", "False"]:
                                new_q_dict["correct_answer"] = "True"
                        elif selected_type == "Short Answer":
                            new_q_dict["choices"] = []

                        cleaned_new_q = clean_question_data(new_q_dict)

                        # Update main exam state
                        st.session_state.exam[index] = cleaned_new_q

                        # Safely clear widget keys to prevent StreamlitWidgetAlreadyInstantiatedError
                        st.session_state.pop(f"question_text_{index}", None)
                        st.session_state.pop(f"answer_{index}", None)
                        st.session_state.pop(f"type_{index}", None)
                        st.session_state.pop(f"difficulty_{index}", None)

                        for c_idx in range(10):
                            st.session_state.pop(f"choice_{index}_{c_idx}", None)

                        st.success(f"Question regenerated as {selected_type}!")
                        st.rerun()

            st.divider()

        # NAVIGATION BUTTONS (BACK & NEXT)
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            if st.button("← Back to Create", use_container_width=True):
                navigate_to("Create")
        with b_col2:
            if st.button("Continue to Quality  →", type="primary", use_container_width=True):
                navigate_to("Quality")


# ============================================================
# PAGE 3: QUALITY
# ============================================================

elif st.session_state.page == "Quality":

    render_html('<div class="page-title">Quality Center</div>')
    render_html(
        '<div class="page-subtitle">'
        'Analyze quality, detect similar questions, and validate the generated exam against your PDF.'
        '</div>'
    )

    exam = clean_exam_data(st.session_state.exam)
    st.session_state.exam = exam

    if not exam:
        st.info("No exam available.")
    else:
        a1, a2, a3 = st.columns(3)

        with a1:
            if st.button("⭐ Check Quality", use_container_width=True):
                with st.spinner("Evaluating question quality..."):
                    result = api_call("POST", "/api/quality-score", json={"questions": exam})
                if result is not None:
                    st.session_state.quality = result

        with a2:
            if st.button("🔍 Check Similarity", use_container_width=True):
                with st.spinner("Checking similar questions..."):
                    result = api_call("POST", "/api/duplicates", json={"questions": exam})
                if result is not None:
                    st.session_state.duplicates = result

        with a3:
            if st.button("📚 Check Grounding", use_container_width=True):
                with st.spinner("Checking questions against your PDF..."):
                    result = api_call("POST", "/api/validate", json={"questions": exam})
                if result is not None:
                    st.session_state.grounding = result

        st.divider()

        # Quality Hero Score
        if st.session_state.quality is not None:

            render_html(
                """
                <div class="section-label">
                    <div class="section-icon">⭐</div>
                    <div class="section-title">Quality Analysis</div>
                </div>
                """
            )

            quality = st.session_state.quality
            quality_items = get_quality_items(quality)
            overall = get_overall_quality(quality, quality_items)

            if overall is not None:
                message = "Strong exam quality" if overall >= 80 else "Some questions need review" if overall >= 60 else "Several questions need attention"
                icon = "🟢" if overall >= 80 else "🟡" if overall >= 60 else "🔴"
                score_angle = min(max(overall, 0), 100) * 3.6

                render_html(
                    f"""
                    <div class="quality-hero">
                        <div style="display:flex; align-items:center; gap:28px; flex-wrap:wrap;">
                            <div class="quality-score-ring" style="background: conic-gradient(#7c3aed 0deg, #8b5cf6 {score_angle}deg, #ede9fe {score_angle}deg, #ede9fe 360deg);">
                                <div class="quality-score-inner">
                                    <div class="quality-big-score">{overall:.0f}</div>
                                    <div class="quality-score-label">/ 100</div>
                                </div>
                            </div>
                            <div style="flex:1; min-width:240px;">
                                <div class="quality-message">{icon} {message}</div>
                                <div class="quality-description">
                                    The score summarizes the AI quality evaluation of the generated assessment questions.
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                )

            good_count = sum(1 for item in quality_items if (get_quality_score(item) or 0) >= 80)
            review_count = sum(1 for item in quality_items if 0 < (get_quality_score(item) or 0) < 80)
            pending_count = len(exam) - (good_count + review_count)

            q1, q2, q3 = st.columns(3)
            with q1:
                st.metric("🟢 Good", good_count)
            with q2:
                st.metric("🟡 Needs Review", review_count)
            with q3:
                st.metric("⚪ Pending", pending_count)

            st.write("### Question Quality Breakdown")

            for index, question in enumerate(exam):
                item = quality_items[index] if index < len(quality_items) else None
                score = get_quality_score(item)
                question_text = clean_display_text(question.get("question", ""))

                card_class = "pending" if score is None else "good" if score >= 80 else "review" if score >= 60 else "bad"
                score_class = "score-pending" if score is None else "score-good" if score >= 80 else "score-review" if score >= 60 else "score-bad"
                score_text = "—" if score is None else f"{score:.0f}/100"
                status = "⏳ Not evaluated" if score is None else "✓ Good" if score >= 80 else "! Needs review"

                render_html(
                    f"""
                    <div class="quality-question {card_class}">
                        <div class="quality-row">
                            <div class="quality-question-number">Question {index + 1}</div>
                            <div class="quality-score-pill {score_class}">{score_text}</div>
                        </div>
                        <div class="quality-question-text">{html.escape(question_text)}</div>
                        <div class="quality-status">{status}</div>
                    </div>
                    """
                )

        # Similar Questions
        if st.session_state.duplicates is not None:

            render_html(
                """
                <div class="section-label">
                    <div class="section-icon">🔍</div>
                    <div class="section-title">Similarity Analysis</div>
                </div>
                """
            )

            duplicate_items = get_duplicate_pairs(st.session_state.duplicates)

            if not duplicate_items:
                st.success("✓ No candidate duplicate question pairs were detected.")
            else:
                for pair_index, item in enumerate(duplicate_items):
                    if not isinstance(item, dict):
                        continue
                    q1 = item.get("question_a", item.get("question1", pair_index + 1))
                    q2 = item.get("question_b", item.get("question2", pair_index + 2))
                    
                    sem_sim = item.get("semantic_similarity", item.get("similarity", 0))
                    dup_score = item.get("duplicate_score", sem_sim)
                    status = item.get("status", "Review")
                    reason = item.get("reason", "Analyzed candidate pair.")

                    if status == "Duplicate":
                        badge_html = '<span style="background: rgba(220, 38, 38, 0.15); color: #dc2626; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem;">🔴 Duplicate</span>'
                    elif status == "Review":
                        badge_html = '<span style="background: rgba(217, 119, 6, 0.15); color: #d97706; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem;">🟡 Review Needed</span>'
                    else:
                        badge_html = '<span style="background: rgba(22, 163, 74, 0.15); color: #16a34a; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem;">🟢 Not Duplicate</span>'

                    render_html(
                        f"""
                        <div class="similar-card" style="border-left: 4px solid {'#dc2626' if status == 'Duplicate' else '#d97706' if status == 'Review' else '#16a34a'}; margin-bottom: 12px; padding: 16px; background: white; border-radius: 12px; border: 1px solid #e2e8f0;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div style="font-weight: 700; font-size: 1.05rem; color: #0f172a;">
                                    Question {q1} ↔ Question {q2}
                                </div>
                                {badge_html}
                            </div>
                            <div style="display: flex; gap: 20px; font-size: 0.9rem; color: #64748b; margin-bottom: 8px;">
                                <div><strong>Semantic Similarity:</strong> {sem_sim:.1f}%</div>
                                <div><strong>Duplicate Score:</strong> {dup_score:.0f}%</div>
                            </div>
                            <div style="font-size: 0.88rem; color: #334155; background: #f8fafc; padding: 8px 12px; border-radius: 8px;">
                                💡 <strong>Analysis:</strong> {html.escape(reason)}
                            </div>
                        </div>
                        """
                    )

        # Grounding Cards
        if st.session_state.grounding is not None:

            render_html(
                """
                <div class="section-label">
                    <div class="section-icon">📚</div>
                    <div class="section-title">PDF Grounding</div>
                </div>
                """
            )

            grounding_items = get_grounding_items(st.session_state.grounding)

            for index, question in enumerate(exam):
                item = find_grounding_item(grounding_items, question, index)
                verdict_raw = get_grounding_verdict(item) if item else None
                normalized = normalize_verdict(verdict_raw)
                question_text = clean_display_text(question.get("question", ""))

                verdict_suffix = f" ({verdict_raw})" if verdict_raw and str(verdict_raw).strip() else ""

                if normalized == "supported":
                    card_class = "grounded"
                    title = f"✓ Question {index + 1} — Supported by PDF{verdict_suffix}"
                elif normalized == "unsupported":
                    card_class = "not-grounded"
                    title = f"⚠ Question {index + 1} — Not supported by PDF{verdict_suffix}"
                else:
                    card_class = "not-evaluated"
                    title = f"⏳ Question {index + 1} — {verdict_raw if verdict_raw else 'Not evaluated'}"

                render_html(
                    f"""
                    <div class="grounding-card {card_class}">
                        <strong>{html.escape(title)}</strong>
                        <div style="margin-top:8px; color:#6b7280; font-size:12px; line-height:1.6;">
                            {html.escape(question_text)}
                        </div>
                    </div>
                    """
                )

        render_html("")

        # NAVIGATION BUTTONS (BACK & NEXT)
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            if st.button("← Back to Review", use_container_width=True):
                navigate_to("Review")
        with b_col2:
            if st.button("Continue to Export  →", type="primary", use_container_width=True):
                navigate_to("Export")


# ============================================================
# PAGE 4: EXPORT
# ============================================================

elif st.session_state.page == "Export":

    render_html('<div class="page-title">Export Exam</div>')
    render_html(
        '<div class="page-subtitle">'
        'Your exam is ready. Download the student version, answer key, or JSON backup.'
        '</div>'
    )

    exam = clean_exam_data(st.session_state.exam)
    st.session_state.exam = exam

    if not exam:
        st.info("No exam available.")
    else:
        quality_value = "Not checked"
        if st.session_state.quality is not None:
            quality_items = get_quality_items(st.session_state.quality)
            overall = get_overall_quality(st.session_state.quality, quality_items)
            if overall is not None:
                quality_value = f"{overall:.0f}/100"

        duplicate_count = len(get_duplicate_pairs(st.session_state.duplicates))
        grounding_items = get_grounding_items(st.session_state.grounding)
        grounded_count = sum(1 for item in grounding_items if normalize_verdict(get_grounding_verdict(item)) == "supported")

        e1, e2, e3, e4 = st.columns(4)
        with e1:
            st.metric("Questions", len(exam))
        with e2:
            st.metric("Quality Score", quality_value)
        with e3:
            st.metric("Similar Pairs", duplicate_count)
        with e4:
            st.metric("PDF Supported", grounded_count)

        render_html("")

        # DOWNLOAD CENTER
        render_html(
            """
            <div class="section-label">
                <div class="section-icon">📥</div>
                <div class="section-title">Download Center</div>
            </div>
            """
        )

        exam_pdf = create_exam_pdf(exam, source_pdf=st.session_state.uploaded_pdf_name, include_answers=False)
        answer_key_pdf = create_exam_pdf(exam, source_pdf=st.session_state.uploaded_pdf_name, include_answers=True)

        d1, d2 = st.columns(2)

        with d1:
            render_html(
                """
                <div class="export-card">
                    <div class="export-icon">📄</div>
                    <div class="export-title">Student Exam</div>
                    <div class="export-description">
                        Clean exam PDF without answers, ready to print or distribute to students.
                    </div>
                </div>
                """
            )
            st.download_button(
                "⬇️ Download Student Exam",
                data=exam_pdf,
                file_name="generated_exam.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

        with d2:
            render_html(
                """
                <div class="export-card">
                    <div class="export-icon">🔑</div>
                    <div class="export-title">Answer Key</div>
                    <div class="export-description">
                        Complete exam PDF including correct answers and explanations.
                    </div>
                </div>
                """
            )
            st.download_button(
                "⬇️ Download Answer Key",
                data=answer_key_pdf,
                file_name="generated_exam_answer_key.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

        # JSON BACKUP
        export_data = {"source_pdf": st.session_state.uploaded_pdf_name, "questions": exam}
        json_data = json.dumps(export_data, ensure_ascii=False, indent=4)

        with st.expander("🗂️ JSON Backup"):
            st.caption("Keep a machine-readable backup copy of your generated exam data.")
            st.download_button(
                "Download JSON Backup",
                data=json_data,
                file_name="generated_exam.json",
                mime="application/json",
                use_container_width=True,
            )

        # FINAL PREVIEW
        render_html(
            """
            <div class="section-label">
                <div class="section-icon">👀</div>
                <div class="section-title">Final Exam Preview</div>
            </div>
            """
        )

        for index, question in enumerate(exam):
            question = clean_question_data(question)

            render_html(
                f"""
                <div class="question-card">
                    <div class="question-header">
                        <div class="question-number">
                            <div class="question-number-badge">{index + 1}</div>
                            <div class="question-title">Question {index + 1}</div>
                        </div>
                        <div>
                            <span class="badge badge-purple">{html.escape(str(question.get("question_type", "MCQ")))}</span>
                            <span class="badge badge-blue">{html.escape(str(question.get("difficulty", "Medium")))}</span>
                        </div>
                    </div>
                </div>
                """
            )

            st.write(clean_display_text(question.get("question", "")))

            choices = question.get("choices", [])
            if isinstance(choices, list):
                for choice_index, choice in enumerate(choices):
                    st.write(f"{chr(65 + choice_index)}. {clean_display_text(choice)}")

            st.divider()

        # NAVIGATION BUTTON (BACK)
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            if st.button("← Back to Quality", use_container_width=True):
                navigate_to("Quality")


# ============================================================
# FOOTER
# ============================================================

render_html(
    """
    <div class="app-footer">
        🎓 Examora · Next-Gen Intelligent Assessment Workspace
    </div>
    """
)
