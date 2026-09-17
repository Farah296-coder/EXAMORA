import html
import json
import os

import streamlit as st

from exam_editor import (
    APPROVED_PATH,
    DIFFICULTY_LEVELS,
    DRAFT_PATH,
    LOW_QUALITY_THRESHOLD,
    QUESTION_TYPES,
    add_choice,
    add_question,
    apply_regeneration,
    approval_blockers,
    approve_exam,
    build_exam_from_pipeline,
    change_question_type,
    delete_question,
    discard_draft,
    duplicate_messages,
    duplicate_question,
    exam_summary,
    generate_new_question,
    get_question,
    load_exam,
    load_source_pages,
    move_question,
    propose_regeneration,
    question_warnings,
    recheck_duplicates,
    recheck_question,
    remove_choice,
    save_draft,
    set_choice,
    update_field,
)

st.set_page_config(
    page_title="Exam Editor",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, .hero-title { font-family: 'Poppins', sans-serif; }

        .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1250px; }

        .hero {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            padding: 1.7rem 2.2rem;
            border-radius: 18px;
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 10px 30px rgba(79, 70, 229, 0.25);
        }
        .hero-title { font-size: 1.85rem; font-weight: 700; margin-bottom: 0.2rem; }
        .hero-subtitle { font-size: 0.98rem; opacity: 0.92; }
        .hero-flow { margin-top: 0.8rem; display: flex; flex-wrap: wrap; gap: 6px; font-size: 0.78rem; }
        .hero-flow span { background: rgba(255,255,255,0.16); padding: 3px 10px; border-radius: 999px; }
        .hero-flow span.active { background: white; color: #4F46E5; font-weight: 600; }

        div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px !important; }
        .stButton > button, .stDownloadButton > button { border-radius: 10px; font-weight: 600; }
        .stButton > button[kind="primary"] { background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border: none; }
        div[data-testid="stMetric"] { background: rgba(124, 58, 237, 0.07); padding: 0.8rem 1rem; border-radius: 12px; }

        .q-head { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; }
        .q-num {
            font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 1.05rem;
            background: #4F46E5; color: white; border-radius: 10px; padding: 2px 11px; margin-right: 4px;
        }

        .chip {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 3px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;
        }
        .chip-type { background: rgba(99, 102, 241, 0.14); color: #6366F1; }
        .chip-easy, .chip-good { background: rgba(22, 163, 74, 0.14); color: #16A34A; }
        .chip-medium, .chip-mid { background: rgba(217, 119, 6, 0.15); color: #D97706; }
        .chip-hard, .chip-bad { background: rgba(220, 38, 38, 0.13); color: #DC2626; }
        .chip-muted { background: rgba(107, 114, 128, 0.15); color: #6B7280; }
        .chip-accent { background: rgba(168, 85, 247, 0.15); color: #A855F7; }

        .warn-list { display: flex; flex-direction: column; gap: 5px; margin: 8px 0 4px 0; }
        .warn { font-size: 0.84rem; padding: 6px 11px; border-radius: 9px; border-left: 4px solid; line-height: 1.35; }
        .warn b { margin-right: 4px; }
        .warn-error { background: rgba(220, 38, 38, 0.08); border-color: #DC2626; }
        .warn-warning { background: rgba(217, 119, 6, 0.09); border-color: #D97706; }
        .warn-info { background: rgba(99, 102, 241, 0.07); border-color: #818CF8; }

        .panel { border: 1px solid rgba(128, 128, 128, 0.22); border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }
        .panel-title { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.7; margin-bottom: 6px; display: flex; gap: 6px; align-items: center; }
        .muted { opacity: 0.65; font-size: 0.86rem; }
        .score { font-family: 'Poppins', sans-serif; font-size: 2rem; font-weight: 700; line-height: 1.1; margin-bottom: 8px; }
        .score span { font-size: 0.95rem; opacity: 0.6; font-weight: 500; }
        .score.good { color: #16A34A; }
        .score.mid { color: #D97706; }
        .score.bad { color: #DC2626; }
        .bar-row { display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 0.8rem; }
        .bar-label { width: 78px; opacity: 0.8; }
        .bar { flex: 1; height: 7px; background: rgba(128, 128, 128, 0.18); border-radius: 999px; overflow: hidden; }
        .bar-fill { height: 100%; border-radius: 999px; }
        .bar-fill.good { background: #16A34A; }
        .bar-fill.mid { background: #D97706; }
        .bar-fill.bad { background: #DC2626; }
        .bar-value { width: 26px; text-align: right; font-weight: 600; }
        .feedback { font-size: 0.83rem; margin-top: 8px; opacity: 0.85; line-height: 1.4; }

        .choice-letter {
            display: inline-flex; align-items: center; justify-content: center;
            width: 30px; height: 30px; border-radius: 8px; font-weight: 700; font-size: 0.85rem;
            background: rgba(128, 128, 128, 0.14);
        }
        .choice-letter.correct { background: #16A34A; color: white; }

        .preview { border: 1px solid rgba(128, 128, 128, 0.22); border-radius: 12px; padding: 12px 14px; height: 100%; }
        .preview-label { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.6; margin-bottom: 6px; }
        .preview-q { font-weight: 600; margin-bottom: 8px; line-height: 1.4; }
        .preview-choice { font-size: 0.88rem; padding: 4px 8px; border-radius: 7px; margin: 3px 0; }
        .preview-choice.is-correct { background: rgba(22, 163, 74, 0.13); color: #16A34A; font-weight: 600; }
        .critique-item { font-size: 0.86rem; margin: 3px 0; line-height: 1.4; }
    </style>
    """,
    unsafe_allow_html=True,
)

TYPE_ICON = {"MCQ": "🔤", "True-False": "✅", "Short Answer": "✍️"}
DIFFICULTY_CHIP = {"Easy": "chip-easy", "Medium": "chip-medium", "Hard": "chip-hard"}
VERDICT_CHIP = {"Correct": "chip-good", "Incorrect": "chip-bad", "Unsupported": "chip-bad"}
VERDICT_ICON = {"Correct": "✔", "Incorrect": "✖", "Unsupported": "⚠"}
LEVEL_ICON = {"error": "⛔", "warning": "⚠️", "info": "ℹ️"}
SCORE_LABELS = [
    ("relevance", "Relevance"),
    ("difficulty", "Difficulty"),
    ("objective", "Objective"),
    ("clarity", "Clarity"),
    ("distractors", "Distractors"),
]
FILTERS = ["All", "Needs attention", "Errors only"]


def esc(value):
    return html.escape(str(value if value is not None else ""))


def letter(index):
    return chr(65 + index)


def wkey(qid, name):
    return f"q_{qid}_{name}"


def bkey(qid, name):
    return f"btn_{qid}_{name}"


def seed(key, value):
    if key not in st.session_state:
        st.session_state[key] = value
    return key


def reset_widgets(qid=None):
    prefix = f"q_{qid}_" if qid else "q_"
    for key in [k for k in list(st.session_state.keys()) if isinstance(k, str) and k.startswith(prefix)]:
        del st.session_state[key]


def init_state():
    if "exam" not in st.session_state:
        exam, from_draft = load_exam()
        st.session_state.exam = exam
        st.session_state.from_draft = from_draft
    st.session_state.setdefault("proposals", {})
    st.session_state.setdefault("flash", [])
    st.session_state.setdefault("approved", None)


def current_exam():
    return st.session_state.exam


def persist():
    save_draft(st.session_state.exam)
    st.session_state.from_draft = True
    st.session_state.approved = None


def flash(kind, message):
    st.session_state.flash.append((kind, message))


def question_number(qid):
    for index, question in enumerate(current_exam()["questions"], start=1):
        if question["id"] == qid:
            return index
    return None


@st.cache_data
def cached_pages():
    return load_source_pages()


def score_class(value):
    if value is None:
        return "mid"
    if value >= 80:
        return "good"
    if value >= LOW_QUALITY_THRESHOLD:
        return "mid"
    return "bad"


def chip(text, css_class):
    return f'<span class="chip {css_class}">{esc(text)}</span>'


def on_field(qid, field):
    question = get_question(current_exam(), qid)
    if question is None:
        return
    update_field(question, field, st.session_state[wkey(qid, field)])
    persist()


def on_type(qid):
    question = get_question(current_exam(), qid)
    if question is None:
        return
    change_question_type(question, st.session_state[wkey(qid, "question_type")])
    reset_widgets(qid)
    st.session_state.proposals.pop(qid, None)
    persist()


def on_choice(qid, index):
    question = get_question(current_exam(), qid)
    if question is None:
        return
    set_choice(question, index, st.session_state[wkey(qid, f"choice_{index}")])
    persist()


def on_mcq_correct(qid):
    question = get_question(current_exam(), qid)
    index = st.session_state.get(wkey(qid, "correct_index"))
    if question is None or index is None or index >= len(question["choices"] or []):
        return
    update_field(question, "correct_answer", question["choices"][index])
    persist()


def on_answer(qid, widget_name):
    question = get_question(current_exam(), qid)
    value = st.session_state.get(wkey(qid, widget_name))
    if question is None or value is None:
        return
    update_field(question, "correct_answer", value)
    persist()


def on_source_pages(qid):
    question = get_question(current_exam(), qid)
    if question is None:
        return
    raw = st.session_state[wkey(qid, "source_pages")]
    pages = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit() and int(part) not in pages:
            pages.append(int(part))
    update_field(question, "source_pages", pages)
    st.session_state[wkey(qid, "source_pages")] = ", ".join(str(p) for p in pages)
    persist()


def on_add_choice(qid):
    question = get_question(current_exam(), qid)
    if question is None:
        return
    add_choice(question)
    reset_widgets(qid)
    persist()


def on_remove_choice(qid, index):
    question = get_question(current_exam(), qid)
    if question is None:
        return
    remove_choice(question, index)
    reset_widgets(qid)
    persist()


def on_move(qid, offset):
    move_question(current_exam(), qid, offset)
    persist()


def on_copy(qid):
    copied = duplicate_question(current_exam(), qid)
    if copied is not None:
        flash("success", f"Question copied as Question {question_number(copied['id'])}.")
    persist()


def on_delete(qid):
    number = question_number(qid)
    delete_question(current_exam(), qid)
    reset_widgets(qid)
    st.session_state.proposals.pop(qid, None)
    flash("success", f"Question {number} deleted.")
    persist()


def on_discard_proposal(qid):
    st.session_state.proposals.pop(qid, None)


def on_reload_pipeline():
    discard_draft()
    reset_widgets()
    st.session_state.exam = build_exam_from_pipeline()
    st.session_state.from_draft = False
    st.session_state.proposals = {}
    st.session_state.approved = None
    st.session_state.confirm_reset = False
    flash("success", "Reloaded questions and checks from the pipeline output files.")


def run_recheck(qid):
    question = get_question(current_exam(), qid)
    number = question_number(qid)
    if question is None:
        return
    with st.spinner(f"Validating Question {number} against the PDF and scoring quality..."):
        try:
            recheck_question(question, cached_pages())
        except Exception as e:
            flash("error", f"Re-check failed for Question {number}: {e}")
        else:
            flash("success", f"Question {number} re-checked.")
    persist()
    st.rerun()


def run_recheck_all():
    exam = current_exam()
    questions = exam["questions"]
    if not questions:
        return
    progress = st.progress(0.0, text="Starting checks...")
    failures = []
    for index, question in enumerate(questions):
        progress.progress(index / len(questions), text=f"Checking question {index + 1} of {len(questions)}")
        try:
            recheck_question(question, cached_pages())
        except RuntimeError as e:
            failures.append(str(e))
            break
        except Exception as e:
            failures.append(f"Question {index + 1}: {e}")
    progress.progress(1.0, text="Checking duplicates...")
    try:
        recheck_duplicates(exam)
    except Exception as e:
        failures.append(f"Duplicate detection: {e}")
    persist()
    if failures:
        flash("error", "Some checks failed:\n\n" + "\n\n".join(f"- {f}" for f in failures))
    else:
        flash("success", f"All {len(questions)} questions re-checked, duplicates refreshed.")
    st.rerun()


def run_duplicates():
    with st.spinner("Comparing all questions for duplicates..."):
        try:
            duplicates = recheck_duplicates(current_exam())
        except Exception as e:
            flash("error", f"Duplicate detection failed: {e}")
        else:
            flash("success", f"Duplicate check done: {len(duplicates)} similar pair(s) found.")
    persist()
    st.rerun()


def run_regenerate(qid, note):
    question = get_question(current_exam(), qid)
    number = question_number(qid)
    if question is None:
        return
    with st.spinner(f"AI critic is reviewing Question {number}..."):
        try:
            proposal = propose_regeneration(question, note)
        except Exception as e:
            flash("error", f"Regeneration failed for Question {number}: {e}")
        else:
            st.session_state.proposals[qid] = proposal
    st.rerun()


def run_accept_proposal(qid):
    question = get_question(current_exam(), qid)
    proposal = st.session_state.proposals.get(qid)
    number = question_number(qid)
    if question is None or not proposal:
        return
    apply_regeneration(question, proposal["final_question"])
    reset_widgets(qid)
    st.session_state.proposals.pop(qid, None)
    persist()
    with st.spinner(f"Validating the new Question {number}..."):
        try:
            recheck_question(question, cached_pages())
        except Exception as e:
            flash("warning", f"New version applied, but the re-check failed: {e}")
        else:
            flash("success", f"Question {number} replaced with the regenerated version and re-checked.")
    persist()
    st.rerun()


def run_add_generated(topic, objective, question_type, difficulty, position, validate):
    exam = current_exam()
    with st.spinner("Retrieving content from the PDF and generating a question..."):
        try:
            raw = generate_new_question(topic, objective, question_type, difficulty)
        except Exception as e:
            flash("error", f"Generation failed: {e}")
            st.rerun()
        question = add_question(exam, raw, position)
        persist()
    if validate:
        with st.spinner("Validating and scoring the new question..."):
            try:
                recheck_question(question, cached_pages())
            except Exception as e:
                flash("warning", f"Question added, but the check failed: {e}")
    flash("success", f"AI question added as Question {question_number(question['id'])}.")
    persist()
    st.rerun()


def header_html(question, number):
    parts = [
        '<div class="q-head">',
        f'<span class="q-num">Q{number}</span>',
        chip(f"{TYPE_ICON[question['question_type']]} {question['question_type']}", "chip-type"),
        chip(question["difficulty"], DIFFICULTY_CHIP[question["difficulty"]]),
    ]

    grounding = question.get("grounding")
    if grounding:
        verdict = grounding["verdict"]
        parts.append(chip(f"{VERDICT_ICON.get(verdict, '')} {verdict}", VERDICT_CHIP.get(verdict, "chip-muted")))
    else:
        parts.append(chip("Not validated", "chip-muted"))

    quality = question.get("quality")
    if quality and quality.get("quality_score") is not None:
        score = quality["quality_score"]
        parts.append(chip(f"★ {score}/100", f"chip-{score_class(score)}"))

    if question.get("origin") == "regenerated":
        parts.append(chip("✨ Regenerated", "chip-accent"))
    elif question.get("origin") == "manual":
        parts.append(chip("✍️ Added by teacher", "chip-accent"))
    if question.get("stale") and (grounding or quality):
        parts.append(chip("✏️ Edited", "chip-muted"))

    parts.append("</div>")
    return "".join(parts)


def warnings_html(warnings):
    if not warnings:
        return '<div class="warn-list"><div class="warn warn-info" style="border-color:#16A34A;background:rgba(22,163,74,0.08)">✅ <b>All checks passed</b></div></div>'
    rows = [
        f'<div class="warn warn-{w["level"]}">{LEVEL_ICON[w["level"]]} <b>{esc(w["source"])}</b>{esc(w["message"])}</div>'
        for w in warnings
    ]
    return '<div class="warn-list">' + "".join(rows) + "</div>"


def quality_html(question):
    quality = question.get("quality")
    outdated = chip("outdated", "chip-muted") if question.get("stale") and quality else ""
    if not quality:
        return '<div class="panel"><div class="panel-title">Quality score</div><div class="muted">Not scored yet. Use Re-check.</div></div>'

    score = quality.get("quality_score")
    rows = []
    for field, label in SCORE_LABELS:
        value = (quality.get("scores") or {}).get(field)
        if value is None:
            continue
        value = int(value)
        width = max(0, min(100, value))
        rows.append(
            f'<div class="bar-row"><span class="bar-label">{label}</span>'
            f'<div class="bar"><div class="bar-fill {score_class(value)}" style="width:{width}%"></div></div>'
            f'<span class="bar-value">{value}</span></div>'
        )
    feedback = f'<div class="feedback">{esc(quality["feedback"])}</div>' if quality.get("feedback") else ""
    return (
        f'<div class="panel"><div class="panel-title">Quality score {outdated}</div>'
        f'<div class="score {score_class(score)}">{esc(score)}<span>/100</span></div>'
        + "".join(rows)
        + feedback
        + "</div>"
    )


def grounding_html(question):
    grounding = question.get("grounding")
    outdated = chip("outdated", "chip-muted") if question.get("stale") and grounding else ""
    pages = ", ".join(str(p) for p in question.get("source_pages") or []) or "none"
    if not grounding:
        return (
            '<div class="panel"><div class="panel-title">Grounding</div>'
            f'<div class="muted">Not validated against the PDF yet.</div>'
            f'<div class="feedback">Source pages: {esc(pages)}</div></div>'
        )
    verdict = grounding["verdict"]
    supported = "Supported by the PDF" if grounding.get("supported_by_source") else "Not supported by the PDF"
    return (
        f'<div class="panel"><div class="panel-title">Grounding {outdated}</div>'
        f'<div>{chip(VERDICT_ICON.get(verdict, "") + " " + verdict, VERDICT_CHIP.get(verdict, "chip-muted"))} '
        f'{chip(supported, "chip-good" if grounding.get("supported_by_source") else "chip-bad")}</div>'
        f'<div class="feedback">{esc(grounding.get("reason"))}</div>'
        f'<div class="feedback"><b>Source pages:</b> {esc(pages)}</div></div>'
    )


def preview_html(label, data, question_type):
    parts = [f'<div class="preview"><div class="preview-label">{esc(label)}</div>']
    parts.append(f'<div class="preview-q">{esc(data.get("question"))}</div>')
    answer = data.get("correct_answer")
    if question_type == "Short Answer":
        parts.append(f'<div class="preview-choice is-correct">Answer: {esc(answer)}</div>')
    else:
        choices = ["True", "False"] if question_type == "True-False" else (data.get("choices") or [])
        for index, choice in enumerate(choices):
            is_correct = choice == answer
            css = "preview-choice is-correct" if is_correct else "preview-choice"
            mark = " ✓" if is_correct else ""
            parts.append(f'<div class="{css}">{letter(index)}. {esc(choice)}{mark}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_answer_editor(question):
    qid = question["id"]
    question_type = question["question_type"]

    if question_type == "MCQ":
        choices = question["choices"] or []
        correct = question["correct_answer"]
        correct_index = choices.index(correct) if correct and correct in choices else None

        st.markdown("**Choices**")
        for index, choice in enumerate(choices):
            letter_col, input_col, remove_col = st.columns([0.45, 8, 0.6], vertical_alignment="center")
            css = "choice-letter correct" if index == correct_index else "choice-letter"
            letter_col.markdown(f'<span class="{css}">{letter(index)}</span>', unsafe_allow_html=True)
            input_col.text_input(
                f"Choice {letter(index)}",
                key=seed(wkey(qid, f"choice_{index}"), choice),
                on_change=on_choice,
                args=(qid, index),
                placeholder=f"Choice {letter(index)}",
                label_visibility="collapsed",
            )
            remove_col.button(
                "✕",
                key=bkey(qid, f"remove_choice_{index}"),
                on_click=on_remove_choice,
                args=(qid, index),
                disabled=len(choices) <= 2,
                help="Remove this choice",
            )

        correct_col, add_col = st.columns([4, 1.3], vertical_alignment="bottom")
        radio_key = wkey(qid, "correct_index")
        radio_kwargs = {}
        if radio_key not in st.session_state:
            if correct_index is None:
                radio_kwargs["index"] = None
            else:
                st.session_state[radio_key] = correct_index
        correct_col.radio(
            "Correct answer",
            options=list(range(len(choices))),
            format_func=letter,
            key=radio_key,
            on_change=on_mcq_correct,
            args=(qid,),
            horizontal=True,
            **radio_kwargs,
        )
        add_col.button(
            "➕ Add choice",
            key=bkey(qid, "add_choice"),
            on_click=on_add_choice,
            args=(qid,),
            width="stretch",
        )

    elif question_type == "True-False":
        radio_key = wkey(qid, "answer_tf")
        radio_kwargs = {}
        if radio_key not in st.session_state:
            if question["correct_answer"] in ("True", "False"):
                st.session_state[radio_key] = question["correct_answer"]
            else:
                radio_kwargs["index"] = None
        st.radio(
            "Correct answer",
            options=["True", "False"],
            key=radio_key,
            on_change=on_answer,
            args=(qid, "answer_tf"),
            horizontal=True,
            **radio_kwargs,
        )

    else:
        st.text_area(
            "Model answer",
            key=seed(wkey(qid, "answer_text"), question["correct_answer"]),
            on_change=on_answer,
            args=(qid, "answer_text"),
            height=80,
        )


def render_proposal(question):
    qid = question["id"]
    proposal = st.session_state.proposals.get(qid)
    if not proposal:
        return

    with st.container(border=True):
        st.markdown("#### ✨ AI critic review")
        critique = proposal.get("critique") or {}
        issues = critique.get("issues") or []
        suggestions = critique.get("suggestions") or []

        issues_col, suggestions_col = st.columns(2)
        with issues_col:
            st.markdown("**Problems found**")
            if issues:
                st.markdown("".join(f'<div class="critique-item">• {esc(i)}</div>' for i in issues), unsafe_allow_html=True)
            else:
                st.caption("No problems found.")
        with suggestions_col:
            st.markdown("**Suggestions**")
            if suggestions:
                st.markdown("".join(f'<div class="critique-item">• {esc(s)}</div>' for s in suggestions), unsafe_allow_html=True)
            else:
                st.caption("No suggestions.")

        if proposal.get("regenerated"):
            current_col, new_col = st.columns(2)
            current_col.markdown(
                preview_html("Current", proposal.get("original_question") or {}, question["question_type"]),
                unsafe_allow_html=True,
            )
            new_col.markdown(
                preview_html("Proposed", proposal["final_question"], question["question_type"]),
                unsafe_allow_html=True,
            )
            st.write("")
            accept_col, discard_col = st.columns(2)
            if accept_col.button("✅ Use new version", key=bkey(qid, "accept"), type="primary", width="stretch"):
                run_accept_proposal(qid)
            discard_col.button(
                "Keep current version",
                key=bkey(qid, "discard"),
                on_click=on_discard_proposal,
                args=(qid,),
                width="stretch",
            )
        else:
            if proposal.get("error"):
                st.warning(f"{proposal['error']}. The current version was kept. Try again or add a note.")
            else:
                st.info("The critic found no meaningful problems. Add a note describing what to change and regenerate if you still want a new version.")
            st.button("Dismiss", key=bkey(qid, "dismiss"), on_click=on_discard_proposal, args=(qid,))


def render_question_card(question, number, total, warnings):
    qid = question["id"]

    with st.container(border=True):
        head_col, up_col, down_col, copy_col, delete_col = st.columns([8, 0.55, 0.55, 0.55, 0.55], vertical_alignment="center")
        head_col.markdown(header_html(question, number), unsafe_allow_html=True)
        up_col.button("↑", key=bkey(qid, "up"), on_click=on_move, args=(qid, -1), disabled=number == 1, help="Move up")
        down_col.button("↓", key=bkey(qid, "down"), on_click=on_move, args=(qid, 1), disabled=number == total, help="Move down")
        copy_col.button("⧉", key=bkey(qid, "copy"), on_click=on_copy, args=(qid,), help="Duplicate this question")
        with delete_col.popover("🗑️", help="Delete question"):
            st.markdown(f"Delete **Question {number}**?")
            st.button("Delete", key=bkey(qid, "delete"), on_click=on_delete, args=(qid,), type="primary")

        st.markdown(warnings_html(warnings), unsafe_allow_html=True)

        edit_col, insight_col = st.columns([1.75, 1], gap="large")

        with edit_col:
            st.text_area(
                "Question",
                key=seed(wkey(qid, "question"), question["question"]),
                on_change=on_field,
                args=(qid, "question"),
                height=90,
            )
            type_col, difficulty_col = st.columns(2)
            type_col.selectbox(
                "Question type",
                QUESTION_TYPES,
                key=seed(wkey(qid, "question_type"), question["question_type"]),
                on_change=on_type,
                args=(qid,),
                format_func=lambda t: f"{TYPE_ICON[t]} {t}",
            )
            difficulty_col.selectbox(
                "Difficulty",
                DIFFICULTY_LEVELS,
                key=seed(wkey(qid, "difficulty"), question["difficulty"]),
                on_change=on_field,
                args=(qid, "difficulty"),
            )

            render_answer_editor(question)

            with st.expander("Topic, learning objective & source pages"):
                st.text_input(
                    "Topic",
                    key=seed(wkey(qid, "topic"), question["topic"]),
                    on_change=on_field,
                    args=(qid, "topic"),
                )
                st.text_input(
                    "Learning objective",
                    key=seed(wkey(qid, "learning_objective"), question["learning_objective"]),
                    on_change=on_field,
                    args=(qid, "learning_objective"),
                )
                st.text_input(
                    "Source pages",
                    key=seed(wkey(qid, "source_pages"), ", ".join(str(p) for p in question["source_pages"])),
                    on_change=on_source_pages,
                    args=(qid,),
                    help="Comma-separated page numbers, e.g. 3, 2, 9",
                )

        with insight_col:
            st.markdown(quality_html(question), unsafe_allow_html=True)
            st.markdown(grounding_html(question), unsafe_allow_html=True)
            if question["source_pages"]:
                with st.expander("📄 View source text"):
                    pages = cached_pages()
                    for page in question["source_pages"]:
                        st.caption(f"Page {page}")
                        st.text(pages.get(page, "Page text not found in extracted_text.json"))

        recheck_col, note_col, regen_col = st.columns([1.2, 3.2, 1.3], vertical_alignment="bottom")
        if recheck_col.button("🔍 Re-check", key=bkey(qid, "recheck"), width="stretch", help="Validate against the PDF and refresh the quality score"):
            run_recheck(qid)
        note = note_col.text_input(
            "Regeneration note (optional)",
            key=wkey(qid, "regen_note"),
            placeholder="e.g. make the distractors more plausible",
        )
        if regen_col.button("✨ Regenerate", key=bkey(qid, "regenerate"), type="primary", width="stretch", help="AI critic analyzes the question and proposes a better version"):
            run_regenerate(qid, note)

        render_proposal(question)


def render_add_question():
    exam = current_exam()
    total = len(exam["questions"])
    positions = list(range(1, total + 2))

    st.markdown("### ➕ Add question")
    with st.container(border=True):
        manual_tab, ai_tab = st.tabs(["✍️ Write it yourself", "🤖 Generate with AI"])

        with manual_tab:
            type_col, difficulty_col, position_col = st.columns(3)
            question_type = type_col.selectbox("Question type", QUESTION_TYPES, key="new_manual_type")
            difficulty = difficulty_col.selectbox("Difficulty", DIFFICULTY_LEVELS, index=1, key="new_manual_difficulty")
            position = position_col.selectbox("Position", positions, index=len(positions) - 1, format_func=lambda p: f"Question {p}")
            topic_col, objective_col = st.columns(2)
            topic = topic_col.text_input("Topic", key="new_manual_topic")
            objective = objective_col.text_input("Learning objective", key="new_manual_objective")
            if st.button("Add blank question", key="add_manual", width="stretch"):
                question = add_question(
                    exam,
                    {
                        "question_type": question_type,
                        "difficulty": difficulty,
                        "topic": topic,
                        "learning_objective": objective,
                        "origin": "manual",
                    },
                    position - 1,
                )
                flash("success", f"Blank question added as Question {question_number(question['id'])}. Fill it in above.")
                persist()
                st.rerun()

        with ai_tab:
            type_col, difficulty_col, position_col = st.columns(3)
            question_type = type_col.selectbox("Question type", QUESTION_TYPES, key="new_ai_type")
            difficulty = difficulty_col.selectbox("Difficulty", DIFFICULTY_LEVELS, index=1, key="new_ai_difficulty")
            position = position_col.selectbox("Insert at", positions, index=len(positions) - 1, format_func=lambda p: f"Question {p}")
            topic_col, objective_col = st.columns(2)
            topic = topic_col.text_input("Topic", key="new_ai_topic", placeholder="e.g. Generic Classes")
            objective = objective_col.text_input("Learning objective", key="new_ai_objective", placeholder="Optional")
            validate = st.checkbox("Validate and score after generating", value=True, key="new_ai_validate")
            if st.button("Generate question", key="add_ai", type="primary", width="stretch", disabled=not topic.strip()):
                run_add_generated(topic.strip(), objective.strip(), question_type, difficulty, position - 1, validate)


def render_approval():
    exam = current_exam()
    summary = exam_summary(exam)
    blockers = approval_blockers(exam)

    st.markdown("### ✅ Approve exam")
    with st.container(border=True):
        if blockers:
            st.error("Fix these before approving:\n\n" + "\n".join(f"- {b}" for b in blockers))

        concerns = []
        not_correct = summary["verdicts"].get("Incorrect", 0) + summary["verdicts"].get("Unsupported", 0)
        if not_correct:
            concerns.append(f"{not_correct} question(s) are Incorrect or Unsupported by the PDF")
        if summary["unchecked"]:
            concerns.append(f"{summary['unchecked']} question(s) were never validated")
        if summary["warnings"]:
            concerns.append(f"{summary['warnings']} warning(s) remain")
        stale = sum(1 for q in exam["questions"] if q.get("stale") and (q.get("grounding") or q.get("quality")))
        if stale:
            concerns.append(f"{stale} edited question(s) have outdated checks")

        acknowledged = True
        if concerns and not blockers:
            st.warning("Before approving:\n\n" + "\n".join(f"- {c}" for c in concerns))
            acknowledged = st.checkbox("I reviewed these and want to approve anyway", key="ack_concerns")
        elif not blockers:
            st.success("Every question passed validation. The exam is ready.")

        if st.button("Approve exam", type="primary", width="stretch", disabled=bool(blockers) or not acknowledged):
            try:
                st.session_state.approved = approve_exam(exam)
            except ValueError as e:
                st.error(str(e))

        approved = st.session_state.approved
        if approved:
            st.success(f"Exam approved with {approved['total_questions']} questions. Saved to {APPROVED_PATH}")
            st.download_button(
                "⬇️ Download approved_exam.json",
                data=json.dumps(approved, indent=2, ensure_ascii=False),
                file_name="approved_exam.json",
                mime="application/json",
                width="stretch",
            )


def render_sidebar():
    exam = current_exam()
    with st.sidebar:
        st.markdown("### 📂 Exam source")
        if st.session_state.from_draft:
            st.caption(f"Working draft `{DRAFT_PATH}`. Edits are saved automatically.")
        else:
            st.caption("Loaded from the pipeline output files. A draft is created on your first edit.")
        st.caption(f"Last update: {exam.get('updated_at', '-')}")

        st.markdown("### 🤖 AI checks")
        if not os.environ.get("GROQ_API_KEY"):
            st.warning("GROQ_API_KEY is not set. Editing works, but AI actions will fail.")
        if st.button("🔍 Re-check all questions", width="stretch", disabled=not exam["questions"]):
            run_recheck_all()
        if st.button("🧬 Re-check duplicates", width="stretch", disabled=len(exam["questions"]) < 2):
            run_duplicates()

        st.markdown("### 💾 Export")
        st.download_button(
            "⬇️ Download draft",
            data=json.dumps(exam, indent=2, ensure_ascii=False),
            file_name="exam_editor_draft.json",
            mime="application/json",
            width="stretch",
        )

        st.markdown("### ♻️ Reset")
        st.checkbox("Discard all my edits", key="confirm_reset")
        st.button(
            "Reload from pipeline files",
            width="stretch",
            on_click=on_reload_pipeline,
            disabled=not st.session_state.get("confirm_reset"),
        )


def render_overview():
    exam = current_exam()
    summary = exam_summary(exam)
    checked = sum(summary["verdicts"].values())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Questions", summary["total"])
    m2.metric("Avg quality", f"{summary['average_quality']}/100" if summary["average_quality"] is not None else "—")
    m3.metric("Grounded", f"{summary['verdicts']['Correct']}/{checked}" if checked else "—")
    m4.metric("Issues", summary["errors"] + summary["warnings"])

    chips = [chip(f"{TYPE_ICON[t]} {t}: {n}", "chip-type") for t, n in summary["by_type"].items() if n]
    chips += [chip(f"{d}: {n}", DIFFICULTY_CHIP[d]) for d, n in summary["by_difficulty"].items() if n]
    if chips:
        st.markdown(f'<div class="q-head" style="margin:10px 0 4px 0">{"".join(chips)}</div>', unsafe_allow_html=True)

    duplicates = duplicate_messages(exam)
    if duplicates:
        st.warning("**Duplicate detected**\n\n" + "\n".join(f"- {d}" for d in duplicates))


def render_flash():
    for kind, message in st.session_state.flash:
        getattr(st, kind)(message)
    st.session_state.flash = []


def matches_filter(question, warnings, mode, search):
    if search and search.lower() not in question["question"].lower():
        return False
    if mode == "Needs attention":
        return any(w["level"] in ("error", "warning") for w in warnings)
    if mode == "Errors only":
        return any(w["level"] == "error" for w in warnings)
    return True


def main():
    init_state()

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">📝 Exam Editor</div>
            <div class="hero-subtitle">Review, fix and approve the AI-generated exam before it reaches students.</div>
            <div class="hero-flow">
                <span>Generate</span><span>→</span><span>Grounding</span><span>→</span><span>Quality &amp; Duplicates</span><span>→</span><span>Critic &amp; Regeneration</span><span>→</span><span class="active">Teacher Review</span><span>→</span><span>Approved Exam</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_sidebar()
    render_flash()

    exam = current_exam()
    if not exam["questions"]:
        st.info("No questions yet. Run the generation pipeline to create output/generated_exam.json, or add questions below.")
    else:
        render_overview()

        st.write("")
        filter_col, search_col = st.columns([1.4, 1], vertical_alignment="bottom")
        mode = filter_col.radio("Show", FILTERS, horizontal=True, key="filter_mode")
        search = search_col.text_input("Search questions", key="filter_search", placeholder="Search question text")

        total = len(exam["questions"])
        shown = 0
        for number, question in enumerate(list(exam["questions"]), start=1):
            warnings = question_warnings(exam, question)
            if not matches_filter(question, warnings, mode, search.strip()):
                continue
            shown += 1
            render_question_card(question, number, total, warnings)

        if shown == 0:
            st.success("No questions match this filter.")

    st.write("")
    render_add_question()
    st.write("")
    render_approval()


main()
