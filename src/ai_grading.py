import os
import json
from openai import OpenAI

import database

_client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

LLM_MODEL = "openai/gpt-oss-20b"


def score_short_answer(question_text, correct_answer, student_answer):
    prompt = f"""You are grading a student's short-answer exam response.

QUESTION: {question_text}
EXPECTED/CORRECT ANSWER: {correct_answer}
STUDENT'S ANSWER: {student_answer}

Judge if the student's answer is substantively correct, even if worded
differently from the expected answer. Give partial credit if the answer
is partially correct.

Respond with STRICT JSON ONLY:
{{
  "is_correct": true,
  "points_fraction": 1.0,
  "feedback": "short explanation"
}}
"""
    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You always respond with strict, valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    raw_output = response.choices[0].message.content
    try:
        return json.loads(raw_output.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}\nRaw output:\n{raw_output}")


def get_pending_answers(submission_id, db_path=None):
    with database.session(db_path) as conn:
        rows = conn.execute(
            "SELECT a.id AS answer_id, a.answer_text, q.question, q.correct_answer, q.points"
            " FROM answers a JOIN questions q ON q.id = a.question_id"
            " WHERE a.submission_id = ? AND a.graded_by = 'pending'",
            (submission_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def auto_grade_submission(submission_id, db_path=None):
    pending = get_pending_answers(submission_id, db_path)
    results = []

    with database.session(db_path) as conn:
        for item in pending:
            try:
                verdict = score_short_answer(item["question"], item["correct_answer"], item["answer_text"])

                is_correct = bool(verdict.get("is_correct"))
                fraction = float(verdict.get("points_fraction", 1.0 if is_correct else 0.0))
                fraction = max(0.0, min(1.0, fraction))
                points_awarded = round(item["points"] * fraction, 2)
                feedback = verdict.get("feedback", "")

                conn.execute(
                    "UPDATE answers SET is_correct = ?, points_awarded = ?, graded_by = 'ai', feedback = ? WHERE id = ?",
                    (1 if is_correct else 0, points_awarded, feedback, item["answer_id"]),
                )

                results.append({
                    "answer_id": item["answer_id"],
                    "is_correct": is_correct,
                    "points_awarded": points_awarded,
                    "feedback": feedback,
                })
            except Exception as e:
                print(f"  Skipped answer_id={item['answer_id']}: {e}")
                results.append({
                    "answer_id": item["answer_id"],
                    "error": str(e),
                })

        database.recalculate_submission(conn, submission_id)

    return results


if __name__ == "__main__":
    import sys
    submission_id = int(sys.argv[1])
    results = auto_grade_submission(submission_id)
    print(json.dumps(results, indent=2, ensure_ascii=False))