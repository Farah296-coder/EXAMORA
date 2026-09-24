"""
exam_settings.py
-----------------
This is Hend's part of the Phase 2 pipeline (Exam Settings UI).

Flow:
    Teacher fills in settings (in exam_settings_ui.py)
        -> build_exam_settings()    # validates + structures the teacher's choices
        -> save_exam_settings()     # writes exam_settings.json for handoff
        -> picked up by Farah's exam blueprint system

This file has no Streamlit import on purpose: the logic is kept separate
from the UI so Farah (or anyone else) can `import` and call
build_exam_settings() directly without needing to run the app.
"""

from importlib.resources import path
import json

# -----------------------------
# 1. Config: allowed values
# -----------------------------

QUESTION_TYPES = ["MCQ", "True/False", "Short Answer"]
DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]


# -----------------------------
# 2. Validation
# -----------------------------

def validate_exam_settings(num_questions, question_types, difficulty_levels, topics):
    """
    Raises a clear ValueError if the teacher's choices don't make sense,
    so bad settings never silently get passed to the blueprint system.
    `topics` is a list of dicts: [{"topic": str, "learning_objectives": [str, ...]}, ...]
    """
    if not isinstance(num_questions, int) or num_questions <= 0:
        raise ValueError("num_questions must be a positive integer")

    if not question_types:
        raise ValueError("At least one question type must be selected")

    for question_type in question_types:
        if question_type not in QUESTION_TYPES:
            raise ValueError(f"question_type must be one of {QUESTION_TYPES}, got '{question_type}'")

    if not difficulty_levels:
        raise ValueError("At least one difficulty level must be selected")

    for difficulty in difficulty_levels:
        if difficulty not in DIFFICULTY_LEVELS:
            raise ValueError(f"difficulty must be one of {DIFFICULTY_LEVELS}, got '{difficulty}'")

    if not topics:
        raise ValueError("At least one topic must be selected")

    for entry in topics:
        if not entry.get("topic", "").strip():
            raise ValueError("Every topic entry needs a non-empty topic name")


# -----------------------------
# 3. Build the structured settings object
# -----------------------------

def build_exam_settings(num_questions, question_types, difficulty_levels, topics):
    """
    Turns the teacher's raw choices into the fixed structure the exam
    blueprint system expects.

    topics: list of dicts, e.g.
        [
            {"topic": "Generic Classes", "learning_objectives": ["Explain the purpose of generics"]},
            {"topic": "Generic Methods", "learning_objectives": []},
        ]

    Returns a dict:
        {
            "num_questions": 10,
            "question_types": ["MCQ", "True/False"],
            "difficulty_levels": ["Easy", "Medium"],
            "topics": [ ... same shape as input, cleaned ... ]
        }
    """
    validate_exam_settings(num_questions, question_types, difficulty_levels, topics)

    cleaned_topics = []
    for entry in topics:
        cleaned_topics.append({
            "topic": entry["topic"].strip(),
            "learning_objectives": [
                objective.strip()
                for objective in entry.get("learning_objectives", [])
                if objective.strip()
            ],
        })

    exam_settings = {
        "num_questions": num_questions,
        "question_types": question_types,
        "difficulty_levels": difficulty_levels,
        "topics": cleaned_topics,
    }

    return exam_settings


# -----------------------------
# 4. Save for handoff to Farah's blueprint system
# -----------------------------

def save_exam_settings(exam_settings: dict, path: str = "output/exam_settings.json"):
    """
    Saves the teacher's finalized settings to a JSON file, ready for
    Farah's exam blueprint system to pick up.
    """
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(exam_settings, f, indent=2, ensure_ascii=False)
    print(f"Saved exam settings to {path}")


if __name__ == "__main__":
    # Quick manual test — no Streamlit needed
    settings = build_exam_settings(
        num_questions=10,
        question_types=["MCQ", "True/False"],
        difficulty_levels=["Easy", "Medium"],
        topics=[
            {"topic": "Generic Classes", "learning_objectives": ["Explain the purpose of generics"]},
            {"topic": "Generic Methods", "learning_objectives": []},
        ],
    )
    print(json.dumps(settings, indent=2, ensure_ascii=False))
    save_exam_settings(settings)
