import copy
import json
import os
import uuid
from datetime import datetime

QUESTION_TYPES = ["MCQ", "True-False", "Short Answer"]
DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]
VERDICTS = ["Correct", "Incorrect", "Unsupported"]

LOW_QUALITY_THRESHOLD = 70
MCQ_CHOICE_COUNT = 4

EXAM_PATH = "output/generated_exam.json"
GROUNDING_PATH = "output/grounding_results.json"
QUALITY_PATH = "output/quality_score_results.json"
PAGES_PATH = "output/extracted_text.json"
DRAFT_PATH = "output/exam_editor_draft.json"
APPROVED_PATH = "output/approved_exam.json"


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def text_key(text):
    return " ".join(str(text or "").lower().split())


def new_question_id():
    return uuid.uuid4().hex[:10]


def default_choices(question_type):
    if question_type == "MCQ":
        return [""] * MCQ_CHOICE_COUNT
    if question_type == "True-False":
        return ["True", "False"]
    return None


def normalize_question(raw):
    question_type = raw.get("question_type") if raw.get("question_type") in QUESTION_TYPES else "MCQ"

    source_pages = raw.get("source_pages")
    if source_pages is None and raw.get("source_page") is not None:
        source_pages = [raw.get("source_page")]

    choices = raw.get("choices")
    if question_type == "Short Answer":
        choices = None
    elif question_type == "True-False":
        choices = ["True", "False"]
    else:
        choices = [str(c) for c in (choices or [])] or default_choices("MCQ")

    difficulty = raw.get("difficulty")
    if difficulty not in DIFFICULTY_LEVELS:
        difficulty = "Medium"

    return {
        "id": raw.get("id") or new_question_id(),
        "topic": raw.get("topic") or "",
        "learning_objective": raw.get("learning_objective") or "",
        "question_type": question_type,
        "difficulty": difficulty,
        "question": raw.get("question") or "",
        "choices": choices,
        "correct_answer": raw.get("correct_answer") or "",
        "source_pages": list(source_pages or []),
        "grounding": raw.get("grounding"),
        "quality": raw.get("quality"),
        "stale": bool(raw.get("stale", False)),
        "origin": raw.get("origin", "generated"),
    }


def match_results(questions, results):
    by_text = {}
    for result in results or []:
        by_text.setdefault(text_key(result.get("question")), result)

    matched = []
    for index, question in enumerate(questions):
        result = by_text.get(text_key(question.get("question")))
        if result is None and results and len(results) == len(questions):
            result = results[index]
        matched.append(result)
    return matched


def grounding_from_result(result):
    if not result:
        return None
    return {
        "verdict": result.get("verdict", "Unsupported"),
        "reason": result.get("reason", ""),
        "supported_by_source": bool(result.get("supported_by_source", False)),
    }


def quality_from_result(result):
    if not result or result.get("quality_score") is None:
        return None
    return {
        "quality_score": result.get("quality_score"),
        "scores": result.get("scores") or {},
        "feedback": result.get("feedback", ""),
        "distractor_issues": result.get("distractor_issues") or [],
    }


def duplicates_to_ids(duplicates, questions):
    pairs = []
    for dup in duplicates or []:
        a = dup.get("question_a", 0) - 1
        b = dup.get("question_b", 0) - 1
        if 0 <= a < len(questions) and 0 <= b < len(questions):
            pairs.append({
                "a": questions[a]["id"],
                "b": questions[b]["id"],
                "similarity": dup.get("similarity"),
            })
    return pairs


def build_exam_from_pipeline(
    exam_path=EXAM_PATH,
    grounding_path=GROUNDING_PATH,
    quality_path=QUALITY_PATH,
):
    raw_questions = load_json(exam_path, [])
    grounding_results = load_json(grounding_path, [])
    quality_data = load_json(quality_path, {}) or {}

    questions = [normalize_question(q) for q in raw_questions]

    grounding_matches = match_results(raw_questions, grounding_results)
    quality_matches = match_results(raw_questions, quality_data.get("questions", []))

    for question, grounding, quality in zip(questions, grounding_matches, quality_matches):
        question["grounding"] = grounding_from_result(grounding)
        question["quality"] = quality_from_result(quality)

    return {
        "questions": questions,
        "duplicates": duplicates_to_ids(quality_data.get("duplicates"), questions),
        "updated_at": now_iso(),
    }


def load_exam(draft_path=DRAFT_PATH):
    draft = load_json(draft_path)
    if draft and draft.get("questions") is not None:
        draft["questions"] = [normalize_question(q) for q in draft["questions"]]
        draft.setdefault("duplicates", [])
        return draft, True
    return build_exam_from_pipeline(), False


def save_draft(exam, path=DRAFT_PATH):
    exam["updated_at"] = now_iso()
    save_json(exam, path)


def discard_draft(path=DRAFT_PATH):
    if os.path.exists(path):
        os.remove(path)


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def find_index(exam, question_id):
    for index, question in enumerate(exam["questions"]):
        if question["id"] == question_id:
            return index
    return -1


def get_question(exam, question_id):
    index = find_index(exam, question_id)
    return exam["questions"][index] if index >= 0 else None


def mark_edited(question):
    question["stale"] = True


def update_field(question, field, value):
    if question.get(field) == value:
        return
    question[field] = value
    mark_edited(question)


def change_question_type(question, new_type):
    if new_type not in QUESTION_TYPES or question["question_type"] == new_type:
        return

    old_choices = question.get("choices") or []
    question["question_type"] = new_type

    if new_type == "Short Answer":
        question["choices"] = None
    elif new_type == "True-False":
        question["choices"] = ["True", "False"]
        if question["correct_answer"] not in ("True", "False"):
            question["correct_answer"] = ""
    else:
        kept = [c for c in old_choices if c not in ("True", "False")]
        if question["correct_answer"] and question["correct_answer"] not in kept:
            kept.insert(0, question["correct_answer"])
        while len(kept) < MCQ_CHOICE_COUNT:
            kept.append("")
        question["choices"] = kept

    mark_edited(question)


def set_choice(question, index, text):
    choices = question.get("choices") or []
    if not 0 <= index < len(choices) or choices[index] == text:
        return
    was_correct = choices[index] == question["correct_answer"] and choices[index] != ""
    choices[index] = text
    if was_correct:
        question["correct_answer"] = text
    mark_edited(question)


def add_choice(question):
    if question["question_type"] != "MCQ":
        return
    question["choices"].append("")
    mark_edited(question)


def remove_choice(question, index):
    choices = question.get("choices") or []
    if question["question_type"] != "MCQ" or len(choices) <= 2 or not 0 <= index < len(choices):
        return
    removed = choices.pop(index)
    if removed == question["correct_answer"]:
        question["correct_answer"] = ""
    mark_edited(question)


def add_question(exam, raw=None, position=None):
    question = normalize_question(raw or {"origin": "manual"})
    question["id"] = new_question_id()
    if position is None or position >= len(exam["questions"]):
        exam["questions"].append(question)
    else:
        exam["questions"].insert(max(position, 0), question)
    return question


def duplicate_question(exam, question_id):
    index = find_index(exam, question_id)
    if index < 0:
        return None
    copied = copy.deepcopy(exam["questions"][index])
    copied["id"] = new_question_id()
    copied["origin"] = "manual"
    copied["stale"] = True
    exam["questions"].insert(index + 1, copied)
    return copied


def delete_question(exam, question_id):
    index = find_index(exam, question_id)
    if index < 0:
        return
    exam["questions"].pop(index)
    exam["duplicates"] = [
        d for d in exam.get("duplicates", [])
        if d["a"] != question_id and d["b"] != question_id
    ]


def move_question(exam, question_id, offset):
    index = find_index(exam, question_id)
    target = index + offset
    if index < 0 or not 0 <= target < len(exam["questions"]):
        return
    questions = exam["questions"]
    questions[index], questions[target] = questions[target], questions[index]


def move_question_to(exam, question_id, position):
    index = find_index(exam, question_id)
    if index < 0:
        return
    question = exam["questions"].pop(index)
    position = max(0, min(position, len(exam["questions"])))
    exam["questions"].insert(position, question)


def structure_errors(question):
    errors = []
    question_type = question["question_type"]
    answer = str(question.get("correct_answer") or "").strip()

    if not str(question.get("question") or "").strip():
        errors.append("Question text is empty.")

    if not answer:
        errors.append("Correct answer is not set.")

    if question_type == "MCQ":
        choices = [str(c).strip() for c in question.get("choices") or []]
        if len(choices) < 2:
            errors.append("MCQ needs at least 2 choices.")
        if any(not c for c in choices):
            errors.append("One or more choices are empty.")
        filled = [c for c in choices if c]
        if len(filled) != len(set(text_key(c) for c in filled)):
            errors.append("Two or more choices are identical.")
        if answer and answer not in choices:
            errors.append("Correct answer does not match any choice.")

    if question_type == "True-False" and answer and answer not in ("True", "False"):
        errors.append("Correct answer must be True or False.")

    return errors


def question_warnings(exam, question):
    warnings = []
    numbers = {q["id"]: i + 1 for i, q in enumerate(exam["questions"])}

    for message in structure_errors(question):
        warnings.append({"level": "error", "source": "Editor", "message": message})

    grounding = question.get("grounding")
    if grounding is None:
        warnings.append({"level": "info", "source": "Grounding", "message": "Not validated against the PDF yet."})
    elif grounding["verdict"] == "Incorrect":
        warnings.append({"level": "error", "source": "Grounding", "message": f"Marked answer is incorrect: {grounding['reason']}"})
    elif grounding["verdict"] == "Unsupported":
        warnings.append({"level": "error", "source": "Grounding", "message": f"Not supported by the PDF: {grounding['reason']}"})

    quality = question.get("quality")
    if quality is None:
        warnings.append({"level": "info", "source": "Quality", "message": "No quality score yet."})
    else:
        if quality["quality_score"] is not None and quality["quality_score"] < LOW_QUALITY_THRESHOLD:
            warnings.append({"level": "warning", "source": "Quality", "message": f"Low quality score ({quality['quality_score']}/100)."})
        for issue in quality.get("distractor_issues") or []:
            warnings.append({"level": "warning", "source": "Distractors", "message": issue})

    for dup in exam.get("duplicates", []):
        if question["id"] in (dup["a"], dup["b"]):
            other = dup["b"] if dup["a"] == question["id"] else dup["a"]
            if other in numbers:
                similarity = dup.get("similarity")
                similarity_text = f" ({round(similarity * 100)}% similar)" if similarity is not None else ""
                warnings.append({
                    "level": "warning",
                    "source": "Duplicate",
                    "message": f"Similar to Question {numbers[other]}{similarity_text}.",
                })

    if question.get("stale") and (grounding is not None or quality is not None):
        warnings.append({"level": "info", "source": "Editor", "message": "Edited since last check. Re-check to refresh the scores."})

    return warnings


def duplicate_messages(exam):
    numbers = {q["id"]: i + 1 for i, q in enumerate(exam["questions"])}
    messages = []
    for dup in exam.get("duplicates", []):
        if dup["a"] in numbers and dup["b"] in numbers:
            a, b = sorted((numbers[dup["a"]], numbers[dup["b"]]))
            messages.append(f"Question {a} similar to Question {b}")
    return messages


def exam_summary(exam):
    questions = exam["questions"]
    scores = [
        q["quality"]["quality_score"]
        for q in questions
        if q.get("quality") and q["quality"].get("quality_score") is not None
    ]
    verdicts = {v: 0 for v in VERDICTS}
    for q in questions:
        if q.get("grounding"):
            verdicts[q["grounding"]["verdict"]] = verdicts.get(q["grounding"]["verdict"], 0) + 1

    errors = 0
    warnings = 0
    for q in questions:
        for w in question_warnings(exam, q):
            if w["level"] == "error":
                errors += 1
            elif w["level"] == "warning":
                warnings += 1

    return {
        "total": len(questions),
        "average_quality": round(sum(scores) / len(scores)) if scores else None,
        "verdicts": verdicts,
        "unchecked": sum(1 for q in questions if q.get("grounding") is None),
        "errors": errors,
        "warnings": warnings,
        "by_type": {t: sum(1 for q in questions if q["question_type"] == t) for t in QUESTION_TYPES},
        "by_difficulty": {d: sum(1 for q in questions if q["difficulty"] == d) for d in DIFFICULTY_LEVELS},
    }


def load_source_pages(path=PAGES_PATH):
    pages = load_json(path, []) or []
    return {page["page"]: page["text"] for page in pages}


def pipeline_question(question):
    data = {
        "topic": question["topic"],
        "learning_objective": question["learning_objective"] or None,
        "question_type": question["question_type"],
        "difficulty": question["difficulty"],
        "question": question["question"],
        "correct_answer": question["correct_answer"],
        "source_pages": question["source_pages"],
    }
    if question["question_type"] in ("MCQ", "True-False"):
        data["choices"] = list(question["choices"] or [])
    return data


def require_api_key():
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not set. Set it before using AI actions.")


def recheck_question(question, pages_by_number=None):
    require_api_key()
    from grounding_validation import validate_question
    from quality_score import score_question

    if pages_by_number is None:
        pages_by_number = load_source_pages()

    data = pipeline_question(question)
    grounding = validate_question(data, pages_by_number)
    quality = score_question(data)

    question["grounding"] = grounding_from_result(grounding)
    question["quality"] = quality_from_result(quality)
    question["stale"] = False
    return question


def recheck_duplicates(exam):
    require_api_key()
    from quality_score import detect_duplicates

    questions = exam["questions"]
    duplicates = detect_duplicates([pipeline_question(q) for q in questions])
    exam["duplicates"] = duplicates_to_ids(duplicates, questions)
    return exam["duplicates"]


def quality_for_critic(question):
    quality = question.get("quality") or {}
    return {
        "quality_score": quality.get("quality_score"),
        "scores": quality.get("scores", {}),
        "feedback": quality.get("feedback", ""),
        "distractor_issues": quality.get("distractor_issues", []),
    }


def propose_regeneration(question, teacher_note=""):
    require_api_key()
    from ai_critic import (
        critique_question,
        regenerate_question,
        smart_regenerate,
        validate_regenerated_question,
    )

    data = pipeline_question(question)
    quality = quality_for_critic(question)
    grounding = question.get("grounding")
    if grounding and grounding["verdict"] != "Correct":
        quality["grounding"] = grounding

    teacher_note = (teacher_note or "").strip()

    if not teacher_note and (grounding is None or grounding["verdict"] == "Correct"):
        return smart_regenerate(
            question=data,
            quality_result=quality,
            topic=question["topic"],
            learning_objective=question["learning_objective"],
            difficulty=question["difficulty"],
            question_type=question["question_type"],
        )

    critique = critique_question(data, quality)
    critique["issues"] = list(critique.get("issues") or [])
    if teacher_note:
        critique["issues"].append(f"Teacher request: {teacher_note}")
    if grounding and grounding["verdict"] != "Correct":
        critique["issues"].append(f"Grounding check: {grounding['verdict']} - {grounding['reason']}")
    critique["has_issues"] = True

    new_question = regenerate_question(
        question=data,
        critique=critique,
        topic=question["topic"],
        learning_objective=question["learning_objective"],
        difficulty=question["difficulty"],
        question_type=question["question_type"],
    )

    if not validate_regenerated_question(new_question, question["question_type"]):
        return {
            "original_question": data,
            "critique": critique,
            "regenerated": False,
            "final_question": data,
            "error": "Regenerated question failed validation",
        }

    return {
        "original_question": data,
        "critique": critique,
        "regenerated": True,
        "final_question": new_question,
    }


def apply_regeneration(question, new_question):
    question["question"] = new_question.get("question") or question["question"]
    question["correct_answer"] = new_question.get("correct_answer") or question["correct_answer"]

    if question["question_type"] == "MCQ":
        choices = [str(c) for c in new_question.get("choices") or []]
        if choices:
            question["choices"] = choices
    elif question["question_type"] == "True-False":
        question["choices"] = ["True", "False"]
    else:
        question["choices"] = None

    question["origin"] = "regenerated"
    question["grounding"] = None
    question["quality"] = None
    question["stale"] = True
    return question


def generate_new_question(topic, learning_objective, question_type, difficulty):
    require_api_key()
    from generation import generate_one

    raw = generate_one({
        "topic": topic,
        "learning_objective": learning_objective or None,
        "question_type": question_type,
        "difficulty": difficulty,
    })
    raw["origin"] = "generated"
    return raw


def approval_blockers(exam):
    blockers = []
    if not exam["questions"]:
        blockers.append("The exam has no questions.")
    for number, question in enumerate(exam["questions"], start=1):
        for message in structure_errors(question):
            blockers.append(f"Question {number}: {message}")
    return blockers


def build_approved_exam(exam):
    summary = exam_summary(exam)
    questions = []
    for number, question in enumerate(exam["questions"], start=1):
        item = {"number": number}
        item.update(pipeline_question(question))
        item["quality_score"] = (question.get("quality") or {}).get("quality_score")
        item["grounding_verdict"] = (question.get("grounding") or {}).get("verdict")
        questions.append(item)

    return {
        "approved_at": now_iso(),
        "total_questions": len(questions),
        "average_quality": summary["average_quality"],
        "questions": questions,
    }


def approve_exam(exam, path=APPROVED_PATH):
    blockers = approval_blockers(exam)
    if blockers:
        raise ValueError("\n".join(blockers))
    approved = build_approved_exam(exam)
    save_json(approved, path)
    return approved
