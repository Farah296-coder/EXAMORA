import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("EXAM_DB_PATH", "output/exam_platform.db")

EXAM_STATUSES = ["draft", "published", "closed"]
SUBMISSION_STATUSES = ["submitted", "needs_review", "graded"]
AUTO_GRADED_TYPES = ["MCQ", "True-False"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    path TEXT,
    total_pages INTEGER,
    extracted_text_path TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exam_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    num_questions INTEGER,
    question_types TEXT,
    difficulty_levels TEXT,
    topics TEXT,
    blueprint TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    settings_id INTEGER REFERENCES exam_settings(id) ON DELETE SET NULL,
    share_token TEXT UNIQUE,
    duration_minutes INTEGER,
    pass_percentage REAL DEFAULT 50,
    average_quality INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    question_type TEXT NOT NULL,
    topic TEXT,
    learning_objective TEXT,
    difficulty TEXT,
    question TEXT NOT NULL,
    correct_answer TEXT,
    choices TEXT,
    source_pages TEXT,
    points REAL NOT NULL DEFAULT 1,
    quality_score INTEGER,
    grounding_verdict TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_name TEXT NOT NULL,
    student_email TEXT,
    status TEXT NOT NULL DEFAULT 'submitted',
    score REAL NOT NULL DEFAULT 0,
    max_score REAL NOT NULL DEFAULT 0,
    percentage REAL NOT NULL DEFAULT 0,
    started_at TEXT,
    submitted_at TEXT NOT NULL,
    graded_at TEXT
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    answer_text TEXT,
    is_correct INTEGER,
    points_awarded REAL NOT NULL DEFAULT 0,
    graded_by TEXT NOT NULL DEFAULT 'auto',
    feedback TEXT
);

CREATE INDEX IF NOT EXISTS idx_questions_exam ON questions(exam_id, position);
CREATE INDEX IF NOT EXISTS idx_submissions_exam ON submissions(exam_id);
CREATE INDEX IF NOT EXISTS idx_answers_submission ON answers(submission_id);
CREATE INDEX IF NOT EXISTS idx_exams_token ON exams(share_token);
"""

_initialized = set()


class ExamNotFound(Exception):
    pass


class ExamNotAvailable(Exception):
    pass


class SubmissionNotFound(Exception):
    pass


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path=None):
    path = db_path or DB_PATH
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    if path not in _initialized:
        conn.executescript(SCHEMA)
        conn.commit()
        _initialized.add(path)

    return conn


@contextmanager
def session(db_path=None):
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path=None):
    with session(db_path) as conn:
        conn.executescript(SCHEMA)
    return db_path or DB_PATH


def dump_json(value):
    return json.dumps(value, ensure_ascii=False) if value is not None else None


def parse_json(value, default=None):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def normalize_answer(value):
    text = " ".join(str(value or "").split()).strip().lower()
    return text.rstrip(".!?").strip()


def new_share_token():
    return secrets.token_urlsafe(9)


def source_to_dict(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "filename": row["filename"],
        "path": row["path"],
        "total_pages": row["total_pages"],
        "extracted_text_path": row["extracted_text_path"],
        "created_at": row["created_at"],
    }


def settings_to_dict(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "num_questions": row["num_questions"],
        "question_types": parse_json(row["question_types"], []),
        "difficulty_levels": parse_json(row["difficulty_levels"], []),
        "topics": parse_json(row["topics"], []),
        "blueprint": parse_json(row["blueprint"]),
        "created_at": row["created_at"],
    }


def question_to_dict(row, include_answer=True):
    data = {
        "id": row["id"],
        "exam_id": row["exam_id"],
        "position": row["position"],
        "question_type": row["question_type"],
        "topic": row["topic"],
        "learning_objective": row["learning_objective"],
        "difficulty": row["difficulty"],
        "question": row["question"],
        "choices": parse_json(row["choices"]),
        "source_pages": parse_json(row["source_pages"], []),
        "points": row["points"],
    }
    if include_answer:
        data["correct_answer"] = row["correct_answer"]
        data["quality_score"] = row["quality_score"]
        data["grounding_verdict"] = row["grounding_verdict"]
    return data


def exam_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "source_id": row["source_id"],
        "settings_id": row["settings_id"],
        "share_token": row["share_token"],
        "duration_minutes": row["duration_minutes"],
        "pass_percentage": row["pass_percentage"],
        "average_quality": row["average_quality"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "published_at": row["published_at"],
        "closed_at": row["closed_at"],
    }


def submission_to_dict(row):
    return {
        "id": row["id"],
        "exam_id": row["exam_id"],
        "student_name": row["student_name"],
        "student_email": row["student_email"],
        "status": row["status"],
        "score": row["score"],
        "max_score": row["max_score"],
        "percentage": row["percentage"],
        "started_at": row["started_at"],
        "submitted_at": row["submitted_at"],
        "graded_at": row["graded_at"],
    }


def answer_to_dict(row, include_correct=True):
    data = {
        "id": row["id"],
        "question_id": row["question_id"],
        "answer_text": row["answer_text"],
        "is_correct": None if row["is_correct"] is None else bool(row["is_correct"]),
        "points_awarded": row["points_awarded"],
        "graded_by": row["graded_by"],
        "feedback": row["feedback"],
    }
    if include_correct:
        keys = row.keys()
        if "question" in keys:
            data["question"] = row["question"]
        if "question_type" in keys:
            data["question_type"] = row["question_type"]
        if "correct_answer" in keys:
            data["correct_answer"] = row["correct_answer"]
        if "points" in keys:
            data["points"] = row["points"]
    return data


def save_source(filename, path=None, total_pages=None, extracted_text_path=None, db_path=None):
    with session(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO sources (filename, path, total_pages, extracted_text_path, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (filename, path, total_pages, extracted_text_path, now_iso()),
        )
        return cursor.lastrowid


def register_source_from_extracted_text(
    pdf_path,
    extracted_text_path="output/extracted_text.json",
    db_path=None,
):
    total_pages = None
    if os.path.exists(extracted_text_path):
        with open(extracted_text_path, "r", encoding="utf-8") as f:
            total_pages = len(json.load(f))

    return save_source(
        filename=os.path.basename(pdf_path),
        path=pdf_path,
        total_pages=total_pages,
        extracted_text_path=extracted_text_path if os.path.exists(extracted_text_path) else None,
        db_path=db_path,
    )


def get_source(source_id, db_path=None):
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return source_to_dict(row)


def list_sources(db_path=None):
    with session(db_path) as conn:
        rows = conn.execute("SELECT * FROM sources ORDER BY id DESC").fetchall()
        return [source_to_dict(row) for row in rows]


def save_exam_settings(settings, blueprint=None, db_path=None):
    settings = settings or {}
    with session(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO exam_settings (num_questions, question_types, difficulty_levels, topics, blueprint, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                settings.get("num_questions"),
                dump_json(settings.get("question_types")),
                dump_json(settings.get("difficulty_levels")),
                dump_json(settings.get("topics")),
                dump_json(blueprint),
                now_iso(),
            ),
        )
        return cursor.lastrowid


def get_exam_settings(settings_id, db_path=None):
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM exam_settings WHERE id = ?", (settings_id,)).fetchone()
        return settings_to_dict(row)


def question_values(question, position, timestamp):
    source_pages = question.get("source_pages")
    if source_pages is None and question.get("source_page") is not None:
        source_pages = [question.get("source_page")]

    choices = question.get("choices")
    if question.get("question_type") == "Short Answer":
        choices = None

    return (
        position,
        question.get("question_type") or "MCQ",
        question.get("topic"),
        question.get("learning_objective"),
        question.get("difficulty"),
        question.get("question") or "",
        question.get("correct_answer"),
        dump_json(choices),
        dump_json(list(source_pages or [])),
        float(question.get("points") or 1),
        question.get("quality_score"),
        question.get("grounding_verdict"),
        timestamp,
        timestamp,
    )


def insert_questions(conn, exam_id, questions):
    timestamp = now_iso()
    for position, question in enumerate(questions, start=1):
        conn.execute(
            "INSERT INTO questions (exam_id, position, question_type, topic, learning_objective, difficulty,"
            " question, correct_answer, choices, source_pages, points, quality_score, grounding_verdict,"
            " created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (exam_id,) + question_values(question, position, timestamp),
        )


def create_exam(
    title,
    questions,
    settings=None,
    blueprint=None,
    source_id=None,
    description=None,
    duration_minutes=None,
    pass_percentage=50,
    average_quality=None,
    db_path=None,
):
    settings_id = save_exam_settings(settings, blueprint, db_path) if (settings or blueprint) else None
    timestamp = now_iso()

    with session(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO exams (title, description, status, source_id, settings_id, duration_minutes,"
            " pass_percentage, average_quality, created_at, updated_at)"
            " VALUES (?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?)",
            (
                title,
                description,
                source_id,
                settings_id,
                duration_minutes,
                pass_percentage,
                average_quality,
                timestamp,
                timestamp,
            ),
        )
        exam_id = cursor.lastrowid
        insert_questions(conn, exam_id, questions or [])

    return get_exam(exam_id, db_path=db_path)


def import_approved_exam(
    path="output/approved_exam.json",
    title=None,
    settings_path="output/exam_settings.json",
    blueprint_path="output/exam_blueprint.json",
    source_id=None,
    db_path=None,
):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Approved exam file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        approved = json.load(f)

    questions = approved.get("questions") if isinstance(approved, dict) else approved
    settings = None
    blueprint = None

    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    if os.path.exists(blueprint_path):
        with open(blueprint_path, "r", encoding="utf-8") as f:
            blueprint = json.load(f)

    return create_exam(
        title=title or f"Exam {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        questions=questions or [],
        settings=settings,
        blueprint=blueprint,
        source_id=source_id,
        average_quality=approved.get("average_quality") if isinstance(approved, dict) else None,
        db_path=db_path,
    )


def fetch_exam_row(conn, exam_id):
    row = conn.execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()
    if row is None:
        raise ExamNotFound(f"Exam {exam_id} was not found.")
    return row


def get_exam(exam_id, include_answers=True, db_path=None):
    with session(db_path) as conn:
        exam = exam_to_dict(fetch_exam_row(conn, exam_id))

        rows = conn.execute(
            "SELECT * FROM questions WHERE exam_id = ? ORDER BY position", (exam_id,)
        ).fetchall()
        exam["questions"] = [question_to_dict(row, include_answers) for row in rows]
        exam["total_questions"] = len(exam["questions"])
        exam["total_points"] = round(sum(row["points"] for row in rows), 2)

        if exam["settings_id"]:
            settings_row = conn.execute(
                "SELECT * FROM exam_settings WHERE id = ?", (exam["settings_id"],)
            ).fetchone()
            exam["settings"] = settings_to_dict(settings_row)
        else:
            exam["settings"] = None

        if exam["source_id"]:
            source_row = conn.execute("SELECT * FROM sources WHERE id = ?", (exam["source_id"],)).fetchone()
            exam["source"] = source_to_dict(source_row)
        else:
            exam["source"] = None

        exam["submission_count"] = conn.execute(
            "SELECT COUNT(*) FROM submissions WHERE exam_id = ?", (exam_id,)
        ).fetchone()[0]

    return exam


def list_exams(status=None, db_path=None):
    query = (
        "SELECT e.*,"
        " (SELECT COUNT(*) FROM questions q WHERE q.exam_id = e.id) AS question_count,"
        " (SELECT COUNT(*) FROM submissions s WHERE s.exam_id = e.id) AS submission_count"
        " FROM exams e"
    )
    params = ()
    if status:
        query += " WHERE e.status = ?"
        params = (status,)
    query += " ORDER BY e.created_at DESC, e.id DESC"

    with session(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

    exams = []
    for row in rows:
        exam = exam_to_dict(row)
        exam["question_count"] = row["question_count"]
        exam["submission_count"] = row["submission_count"]
        exams.append(exam)
    return exams


def update_exam(exam_id, db_path=None, **fields):
    allowed = ["title", "description", "duration_minutes", "pass_percentage", "source_id", "average_quality"]
    updates = {key: value for key, value in fields.items() if key in allowed}

    with session(db_path) as conn:
        fetch_exam_row(conn, exam_id)
        if updates:
            assignments = ", ".join(f"{key} = ?" for key in updates)
            conn.execute(
                f"UPDATE exams SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(updates.values()) + (now_iso(), exam_id),
            )

    return get_exam(exam_id, db_path=db_path)


def replace_questions(exam_id, questions, db_path=None):
    with session(db_path) as conn:
        fetch_exam_row(conn, exam_id)
        conn.execute("DELETE FROM questions WHERE exam_id = ?", (exam_id,))
        insert_questions(conn, exam_id, questions or [])
        conn.execute("UPDATE exams SET updated_at = ? WHERE id = ?", (now_iso(), exam_id))

    return get_exam(exam_id, db_path=db_path)


def delete_exam(exam_id, db_path=None):
    with session(db_path) as conn:
        fetch_exam_row(conn, exam_id)
        conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    return True


def publish_exam(exam_id, duration_minutes=None, db_path=None):
    with session(db_path) as conn:
        row = fetch_exam_row(conn, exam_id)

        question_count = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE exam_id = ?", (exam_id,)
        ).fetchone()[0]
        if question_count == 0:
            raise ExamNotAvailable("An exam with no questions cannot be published.")

        token = row["share_token"] or new_share_token()
        timestamp = now_iso()

        conn.execute(
            "UPDATE exams SET status = 'published', share_token = ?, published_at = ?, closed_at = NULL,"
            " duration_minutes = COALESCE(?, duration_minutes), updated_at = ? WHERE id = ?",
            (token, row["published_at"] or timestamp, duration_minutes, timestamp, exam_id),
        )

    return get_exam(exam_id, db_path=db_path)


def unpublish_exam(exam_id, db_path=None):
    with session(db_path) as conn:
        fetch_exam_row(conn, exam_id)
        conn.execute(
            "UPDATE exams SET status = 'draft', updated_at = ? WHERE id = ?",
            (now_iso(), exam_id),
        )
    return get_exam(exam_id, db_path=db_path)


def close_exam(exam_id, db_path=None):
    timestamp = now_iso()
    with session(db_path) as conn:
        fetch_exam_row(conn, exam_id)
        conn.execute(
            "UPDATE exams SET status = 'closed', closed_at = ?, updated_at = ? WHERE id = ?",
            (timestamp, timestamp, exam_id),
        )
    return get_exam(exam_id, db_path=db_path)


def share_link(exam, base_url=None):
    if not exam.get("share_token"):
        return None
    base = base_url or os.environ.get("SHARE_BASE_URL", "http://localhost:8000/api/public/exams")
    return f"{base.rstrip('/')}/{exam['share_token']}"


def get_exam_by_token(token, include_answers=False, require_published=True, db_path=None):
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM exams WHERE share_token = ?", (token,)).fetchone()
        if row is None:
            raise ExamNotFound("This exam link is not valid.")
        exam_id = row["id"]
        status = row["status"]

    if require_published and status != "published":
        raise ExamNotAvailable(
            "This exam is closed." if status == "closed" else "This exam is not published yet."
        )

    exam = get_exam(exam_id, include_answers=include_answers, db_path=db_path)
    if not include_answers:
        exam.pop("settings", None)
        exam.pop("source", None)
    return exam


def grade_answer_row(question_row, answer_text):
    question_type = question_row["question_type"]
    correct_answer = question_row["correct_answer"]
    points = question_row["points"]

    given = normalize_answer(answer_text)
    expected = normalize_answer(correct_answer)

    if not given:
        return {"is_correct": 0, "points_awarded": 0.0, "graded_by": "auto"}

    if question_type in AUTO_GRADED_TYPES:
        is_correct = 1 if given == expected else 0
        return {"is_correct": is_correct, "points_awarded": points if is_correct else 0.0, "graded_by": "auto"}

    if given == expected:
        return {"is_correct": 1, "points_awarded": points, "graded_by": "auto"}

    return {"is_correct": None, "points_awarded": 0.0, "graded_by": "pending"}


def recalculate_submission(conn, submission_id):
    rows = conn.execute(
        "SELECT a.points_awarded, a.is_correct, a.graded_by, q.points"
        " FROM answers a JOIN questions q ON q.id = a.question_id"
        " WHERE a.submission_id = ?",
        (submission_id,),
    ).fetchall()

    score = round(sum(row["points_awarded"] for row in rows), 2)
    max_score = round(sum(row["points"] for row in rows), 2)
    percentage = round(score / max_score * 100, 1) if max_score else 0.0
    pending = any(row["graded_by"] == "pending" for row in rows)
    status = "needs_review" if pending else "graded"

    conn.execute(
        "UPDATE submissions SET score = ?, max_score = ?, percentage = ?, status = ?, graded_at = ? WHERE id = ?",
        (score, max_score, percentage, status, None if pending else now_iso(), submission_id),
    )

    return {"score": score, "max_score": max_score, "percentage": percentage, "status": status}


def save_submission(
    exam_id=None,
    token=None,
    student_name="",
    student_email=None,
    answers=None,
    started_at=None,
    db_path=None,
):
    if not str(student_name or "").strip():
        raise ValueError("Student name is required.")

    if exam_id is None and token is None:
        raise ValueError("Either exam_id or token is required.")

    with session(db_path) as conn:
        if exam_id is None:
            row = conn.execute("SELECT * FROM exams WHERE share_token = ?", (token,)).fetchone()
            if row is None:
                raise ExamNotFound("This exam link is not valid.")
        else:
            row = fetch_exam_row(conn, exam_id)

        if row["status"] != "published":
            raise ExamNotAvailable("This exam is not accepting submissions.")

        exam_id = row["id"]

        question_rows = conn.execute(
            "SELECT * FROM questions WHERE exam_id = ? ORDER BY position", (exam_id,)
        ).fetchall()
        questions_by_id = {question["id"]: question for question in question_rows}
        questions_by_position = {question["position"]: question for question in question_rows}

        cursor = conn.execute(
            "INSERT INTO submissions (exam_id, student_name, student_email, status, started_at, submitted_at)"
            " VALUES (?, ?, ?, 'submitted', ?, ?)",
            (exam_id, str(student_name).strip(), student_email, started_at, now_iso()),
        )
        submission_id = cursor.lastrowid

        given_by_question = {}
        for answer in answers or []:
            question = None
            if answer.get("question_id") is not None:
                question = questions_by_id.get(answer["question_id"])
            elif answer.get("position") is not None:
                question = questions_by_position.get(answer["position"])
            if question is not None:
                given_by_question[question["id"]] = answer.get("answer_text", answer.get("answer"))

        for question in question_rows:
            answer_text = given_by_question.get(question["id"])
            grade = grade_answer_row(question, answer_text)
            conn.execute(
                "INSERT INTO answers (submission_id, question_id, answer_text, is_correct, points_awarded, graded_by)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    submission_id,
                    question["id"],
                    answer_text,
                    grade["is_correct"],
                    grade["points_awarded"],
                    grade["graded_by"],
                ),
            )

        recalculate_submission(conn, submission_id)

    return get_submission(submission_id, db_path=db_path)


def get_submission(submission_id, include_correct=True, db_path=None):
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
        if row is None:
            raise SubmissionNotFound(f"Submission {submission_id} was not found.")

        submission = submission_to_dict(row)

        answer_rows = conn.execute(
            "SELECT a.*, q.question, q.question_type, q.correct_answer, q.points, q.position"
            " FROM answers a JOIN questions q ON q.id = a.question_id"
            " WHERE a.submission_id = ? ORDER BY q.position",
            (submission_id,),
        ).fetchall()

        submission["answers"] = [answer_to_dict(answer_row, include_correct) for answer_row in answer_rows]
        submission["pending_review"] = sum(1 for a in answer_rows if a["graded_by"] == "pending")

        exam_row = conn.execute(
            "SELECT title, pass_percentage FROM exams WHERE id = ?", (submission["exam_id"],)
        ).fetchone()
        if exam_row is not None:
            submission["exam_title"] = exam_row["title"]
            submission["passed"] = submission["percentage"] >= (exam_row["pass_percentage"] or 0)

    return submission


def list_submissions(exam_id, db_path=None):
    with session(db_path) as conn:
        fetch_exam_row(conn, exam_id)
        rows = conn.execute(
            "SELECT * FROM submissions WHERE exam_id = ? ORDER BY submitted_at DESC, id DESC", (exam_id,)
        ).fetchall()
    return [submission_to_dict(row) for row in rows]


def grade_answer(answer_id, is_correct, points=None, feedback=None, db_path=None):
    with session(db_path) as conn:
        row = conn.execute(
            "SELECT a.*, q.points AS question_points FROM answers a"
            " JOIN questions q ON q.id = a.question_id WHERE a.id = ?",
            (answer_id,),
        ).fetchone()
        if row is None:
            raise SubmissionNotFound(f"Answer {answer_id} was not found.")

        awarded = points if points is not None else (row["question_points"] if is_correct else 0.0)

        conn.execute(
            "UPDATE answers SET is_correct = ?, points_awarded = ?, graded_by = 'teacher', feedback = ? WHERE id = ?",
            (1 if is_correct else 0, float(awarded), feedback, answer_id),
        )
        recalculate_submission(conn, row["submission_id"])
        submission_id = row["submission_id"]

    return get_submission(submission_id, db_path=db_path)


def exam_results(exam_id, db_path=None):
    with session(db_path) as conn:
        exam_row = fetch_exam_row(conn, exam_id)
        pass_percentage = exam_row["pass_percentage"] or 0

        submission_rows = conn.execute(
            "SELECT * FROM submissions WHERE exam_id = ?", (exam_id,)
        ).fetchall()

        question_rows = conn.execute(
            "SELECT id, position, question, question_type, points FROM questions WHERE exam_id = ? ORDER BY position",
            (exam_id,),
        ).fetchall()

        per_question = []
        for question in question_rows:
            stats = conn.execute(
                "SELECT COUNT(*) AS answered,"
                " SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,"
                " SUM(CASE WHEN graded_by = 'pending' THEN 1 ELSE 0 END) AS pending"
                " FROM answers WHERE question_id = ?",
                (question["id"],),
            ).fetchone()

            answered = stats["answered"] or 0
            correct = stats["correct"] or 0
            per_question.append({
                "question_id": question["id"],
                "position": question["position"],
                "question": question["question"],
                "question_type": question["question_type"],
                "answered": answered,
                "correct": correct,
                "pending_review": stats["pending"] or 0,
                "correct_rate": round(correct / answered * 100, 1) if answered else None,
            })

    percentages = [row["percentage"] for row in submission_rows]
    scores = [row["score"] for row in submission_rows]

    return {
        "exam_id": exam_id,
        "exam_title": exam_row["title"],
        "status": exam_row["status"],
        "submissions": len(submission_rows),
        "average_percentage": round(sum(percentages) / len(percentages), 1) if percentages else None,
        "highest_score": max(scores) if scores else None,
        "lowest_score": min(scores) if scores else None,
        "passed": sum(1 for p in percentages if p >= pass_percentage),
        "pass_percentage": pass_percentage,
        "needs_review": sum(1 for row in submission_rows if row["status"] == "needs_review"),
        "questions": per_question,
    }


def export_exam(exam_id, db_path=None):
    exam = get_exam(exam_id, include_answers=True, db_path=db_path)
    questions = []
    for question in exam["questions"]:
        item = {
            "number": question["position"],
            "topic": question["topic"],
            "learning_objective": question["learning_objective"],
            "question_type": question["question_type"],
            "difficulty": question["difficulty"],
            "question": question["question"],
            "correct_answer": question["correct_answer"],
            "source_pages": question["source_pages"],
            "quality_score": question["quality_score"],
            "grounding_verdict": question["grounding_verdict"],
        }
        if question["choices"] is not None:
            item["choices"] = question["choices"]
        questions.append(item)

    return {
        "exam_id": exam["id"],
        "title": exam["title"],
        "status": exam["status"],
        "total_questions": exam["total_questions"],
        "average_quality": exam["average_quality"],
        "questions": questions,
    }
