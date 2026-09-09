"""
exam_settings_ui.py
--------------------
This is Hend's UI for the Phase 2 task (Exam Settings UI).

The teacher uses this screen to configure:
    - Number of questions
    - Question types + difficulty levels
    - Topics + learning objectives

On submit, the settings are built and validated by exam_settings.py,
then saved to output/exam_settings.json for Farah's exam blueprint
system to pick up.

Run with:
    streamlit run src/exam_settings_ui.py
"""

import json

import streamlit as st

from exam_settings import (
    QUESTION_TYPES,
    DIFFICULTY_LEVELS,
    build_exam_settings,
    save_exam_settings,
)

st.set_page_config(
    page_title="Exam Settings",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styling
# -----------------------------

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, .hero-title {
            font-family: 'Poppins', sans-serif;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1100px;
        }

        .hero {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            padding: 1.9rem 2.25rem;
            border-radius: 18px;
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 10px 30px rgba(79, 70, 229, 0.25);
        }
        .hero-title {
            font-size: 1.9rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .hero-subtitle {
            font-size: 1rem;
            opacity: 0.9;
            font-weight: 400;
        }

        .progress-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.82rem;
            color: #6B7280;
            font-weight: 500;
            margin-bottom: 0.3rem;
        }

        .step-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: #4F46E5;
            color: white;
            font-weight: 600;
            font-size: 0.85rem;
            margin-right: 10px;
            flex-shrink: 0;
        }
        .step-badge.done {
            background: #16A34A;
        }
        .step-title {
            font-size: 1.15rem;
            font-weight: 600;
            color: #1F2937;
            display: flex;
            align-items: center;
            margin-bottom: 0.25rem;
        }
        .step-caption {
            color: #6B7280;
            font-size: 0.88rem;
            margin-bottom: 1rem;
            margin-left: 38px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px !important;
        }

        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            border: none;
        }

        div[data-testid="stMetric"] {
            background: #F5F3FF;
            padding: 0.9rem 1rem;
            border-radius: 12px;
        }

        section[data-testid="stSidebar"] {
            background: #FAFAFB;
        }

        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 4px 0 2px 0;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 0.83rem;
            font-weight: 600;
        }
        .badge-type { background: #EEF2FF; color: #4338CA; }
        .badge-easy { background: #ECFDF5; color: #15803D; }
        .badge-medium { background: #FFFBEB; color: #B45309; }
        .badge-hard { background: #FEF2F2; color: #B91C1C; }

        .topic-card {
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 10px;
            background: #FAFAFA;
        }
        .topic-card-name {
            font-weight: 600;
            color: #1F2937;
            margin-bottom: 4px;
        }
        .topic-card-objectives {
            font-size: 0.85rem;
            color: #6B7280;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

DIFFICULTY_BADGE_CLASS = {"Easy": "badge-easy", "Medium": "badge-medium", "Hard": "badge-hard"}
DIFFICULTY_ICON = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}
TYPE_ICON = {"MCQ": "🔤", "True-False": "✅", "Short Answer": "✍️"}


def badges_html(items, css_class, icon_map=None):
    spans = []
    for item in items:
        icon = f"{icon_map[item]} " if icon_map and item in icon_map else ""
        cls = DIFFICULTY_BADGE_CLASS.get(item, css_class) if css_class == "badge-difficulty" else css_class
        spans.append(f'<span class="badge {cls}">{icon}{item}</span>')
    return f'<div class="badge-row">{"".join(spans)}</div>' if spans else '<span style="color:#9CA3AF;">None selected</span>'


# -----------------------------
# Hero header
# -----------------------------

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">🧠 Exam Settings</div>
        <div class="hero-subtitle">Configure the exam the AI will generate from your course material.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Session state: list of topics the teacher has added
# -----------------------------

if "topics" not in st.session_state:
    st.session_state.topics = [{"topic": "", "learning_objectives": ""}]


def add_topic_row():
    st.session_state.topics.append({"topic": "", "learning_objectives": ""})


def remove_topic_row(index):
    st.session_state.topics.pop(index)


def step_header(number, title, caption, done=False):
    badge_class = "step-badge done" if done else "step-badge"
    badge_content = "✓" if done else str(number)
    st.markdown(
        f"""
        <div class="step-title"><span class="{badge_class}">{badge_content}</span>{title}</div>
        <div class="step-caption">{caption}</div>
        """,
        unsafe_allow_html=True,
    )


main_col, summary_col = st.columns([2.3, 1], gap="large")

with main_col:
    # -----------------------------
    # Progress bar (computed from current form state)
    # -----------------------------
    types_now = st.session_state.get("qtypes_widget", ["MCQ"])
    diff_now = st.session_state.get("diff_widget", ["Medium"])
    topics_now = [row["topic"] for row in st.session_state.topics if row["topic"].strip()]

    steps_done = sum([
        True,                     # number of questions always has a value
        bool(types_now),
        bool(diff_now),
        bool(topics_now),
    ])
    progress_pct = steps_done / 4

    st.markdown(
        f'<div class="progress-label"><span>Setup progress</span><span>{steps_done}/4 steps</span></div>',
        unsafe_allow_html=True,
    )
    st.progress(progress_pct)
    st.write("")

    # -----------------------------
    # 1. Number of questions
    # -----------------------------
    with st.container(border=True):
        step_header(1, "Number of questions", "How many questions should the exam have?", done=True)
        num_questions = st.slider("Number of questions", min_value=1, max_value=50, value=10, label_visibility="collapsed")

    st.write("")

    # -----------------------------
    # 2. Question types + difficulty levels
    # -----------------------------
    with st.container(border=True):
        step_header(2, "Question types & difficulty", "Pick the formats and difficulty mix for this exam.", done=bool(types_now and diff_now))
        col1, col2 = st.columns(2)
        with col1:
            selected_question_types = st.multiselect(
                "Question types",
                options=QUESTION_TYPES,
                default=["MCQ"],
                key="qtypes_widget",
            )
        with col2:
            selected_difficulty_levels = st.multiselect(
                "Difficulty levels",
                options=DIFFICULTY_LEVELS,
                default=["Medium"],
                key="diff_widget",
            )

    st.write("")

    # -----------------------------
    # 3. Topics + learning objectives
    # -----------------------------
    with st.container(border=True):
        step_header(3, "Topics & learning objectives", "Add one card per topic. Learning objectives are optional and comma-separated.", done=bool(topics_now))

        for i, row in enumerate(st.session_state.topics):
            with st.container(border=True):
                topic_col, remove_col = st.columns([6, 1])
                with topic_col:
                    st.session_state.topics[i]["topic"] = st.text_input(
                        f"Topic {i + 1}",
                        value=row["topic"],
                        key=f"topic_{i}",
                        placeholder="e.g. Generic Classes",
                    )
                with remove_col:
                    st.write("")
                    st.write("")
                    if len(st.session_state.topics) > 1:
                        st.button("🗑️", key=f"remove_{i}", on_click=remove_topic_row, args=(i,), help="Remove this topic")

                st.session_state.topics[i]["learning_objectives"] = st.text_input(
                    "Learning objectives",
                    value=row["learning_objectives"],
                    key=f"objectives_{i}",
                    placeholder="e.g. Explain the purpose of generics, Compare generic vs raw types",
                )

        st.button("➕ Add another topic", on_click=add_topic_row)

    st.write("")

    # -----------------------------
    # 4. Submit -> build, validate, save, hand off
    # -----------------------------
    with st.container(border=True):
        step_header(4, "Review & confirm", "Build the settings and hand them off to the exam blueprint system.")

        submitted = st.button("✅ Build exam settings", type="primary", use_container_width=True)

        if submitted:
            topics_payload = [
                {
                    "topic": row["topic"],
                    "learning_objectives": [
                        objective.strip()
                        for objective in row["learning_objectives"].split(",")
                        if objective.strip()
                    ],
                }
                for row in st.session_state.topics
                if row["topic"].strip()
            ]

            try:
                exam_settings = build_exam_settings(
                    num_questions=int(num_questions),
                    question_types=selected_question_types,
                    difficulty_levels=selected_difficulty_levels,
                    topics=topics_payload,
                )
            except ValueError as e:
                st.error(f"⚠️ {e}")
            else:
                save_exam_settings(exam_settings)
                st.success("Exam settings saved — ready for the blueprint system.")

                # ---- Clean summary instead of a raw JSON tree ----
                st.write("")
                m1, m2, m3 = st.columns(3)
                m1.metric("Questions", exam_settings["num_questions"])
                m2.metric("Question types", len(exam_settings["question_types"]))
                m3.metric("Topics", len(exam_settings["topics"]))

                st.markdown("**Question types**")
                st.markdown(badges_html(exam_settings["question_types"], "badge-type", TYPE_ICON), unsafe_allow_html=True)

                st.markdown("**Difficulty levels**")
                st.markdown(badges_html(exam_settings["difficulty_levels"], "badge-difficulty", DIFFICULTY_ICON), unsafe_allow_html=True)

                st.markdown("**Topics**")
                for topic in exam_settings["topics"]:
                    objectives = ", ".join(topic["learning_objectives"]) if topic["learning_objectives"] else "No specific objectives set"
                    st.markdown(
                        f"""
                        <div class="topic-card">
                            <div class="topic-card-name">📘 {topic['topic']}</div>
                            <div class="topic-card-objectives">{objectives}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                json_str = json.dumps(exam_settings, indent=2, ensure_ascii=False)
                st.download_button(
                    "⬇️ Download exam_settings.json",
                    data=json_str,
                    file_name="exam_settings.json",
                    mime="application/json",
                    use_container_width=True,
                )

                with st.expander("🧩 View raw JSON (for developers)"):
                    st.code(json_str, language="json")

# -----------------------------
# Live summary sidebar
# -----------------------------

with summary_col:
    st.markdown("#### 📋 Live preview")
    with st.container(border=True):
        st.metric("Questions", num_questions)

        st.markdown("**Types**")
        st.markdown(badges_html(selected_question_types, "badge-type", TYPE_ICON), unsafe_allow_html=True)

        st.markdown("**Difficulty**")
        st.markdown(badges_html(selected_difficulty_levels, "badge-difficulty", DIFFICULTY_ICON), unsafe_allow_html=True)

        topic_names = [row["topic"] for row in st.session_state.topics if row["topic"].strip()]
        st.markdown(f"**Topics ({len(topic_names)})**")
        if topic_names:
            for name in topic_names:
                st.markdown(f"- {name}")
        else:
            st.caption("No topics added yet")

    st.caption("This preview updates live as you fill in the form on the left.")
