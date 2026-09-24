"""Shared, Streamlit-free helpers used by both front ends."""

import html
import io
import re

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


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
