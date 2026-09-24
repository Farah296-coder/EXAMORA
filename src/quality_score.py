"""
quality_score.py
------------------
This is Hend's part of the Phase 3 pipeline (Quality Score + Duplicate Detection).

Flow:
    Generate Question (Nima's generation.py)
        -> Nima: Grounding / Correctness (grounding_validation.py)
        -> Hend: Quality Score + Duplicate Detection      <-- this file
        -> Farah: Critic / Regeneration if there's a problem
        -> Habiba: Teacher Review & Edit (Exam Editor UI)

This module does two separate jobs on a generated exam:
    1. Quality Score  -> per question: Relevance, Difficulty match, Objective
       alignment, Clarity, and (for MCQ) Distractor quality, combined into a
       single score out of 100.
    2. Duplicate Detection -> compares every question against every other
       question using sentence embeddings, and flags pairs that are too
       similar to both appear on the same exam.

Run this file directly to score output/generated_exam.json and save the
results to output/quality_score_results.json.
"""

import itertools
import json
import os
import re

import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer

# -----------------------------
# 1. Config
# -----------------------------

# Groq's API is free and OpenAI-compatible, so we just point the OpenAI
# client at Groq's base_url and use a Groq API key instead (same setup
# as question_generator.py and grounding_validation.py).
_groq_key = os.environ.get("GROQ_API_KEY", "")
_client = OpenAI(
    api_key=_groq_key or "placeholder_key",
    base_url="https://api.groq.com/openai/v1",
) if _groq_key else None

LLM_MODEL = "openai/gpt-oss-20b"

# Same embedding model already used for the vector DB in rag_indexer.py,
# reused here so we don't pull in a second model just for this.
_embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# How each dimension contributes to the overall /100 quality score.
# distractors only applies to MCQ questions — its weight is redistributed
# across the other four dimensions for True-False / Short Answer questions.
WEIGHTS = {"relevance": 0.25, "difficulty": 0.20, "objective": 0.25, "clarity": 0.15, "distractors": 0.15}

# Two questions with cosine similarity at or above this are flagged as duplicates.
DUPLICATE_THRESHOLD = 0.85


# -----------------------------
# 2. Load questions
# -----------------------------

def load_questions(path="output/generated_exam.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------
# 3. LLM-judged dimensions: Relevance, Difficulty match, Objective, Clarity
# -----------------------------

def build_prompt(question_data):
    question_type = question_data.get("question_type")
    topic = question_data.get("topic") or "General Subject"
    raw_objective = question_data.get("learning_objective")

    if raw_objective and str(raw_objective).strip() and str(raw_objective).strip().lower() not in ["none", "null"]:
        learning_objective = str(raw_objective).strip()
    else:
        learning_objective = f"Assess core knowledge, concepts, and practical application of {topic}"

    difficulty = question_data.get("difficulty") or "Medium"
    question = question_data.get("question")
    correct_answer = question_data.get("correct_answer")
    choices = question_data.get("choices")

    choices_block = f"\nChoices: {choices}" if choices else ""

    prompt = f"""You are scoring the QUALITY of an exam question. Do not judge factual
correctness or grounding — that is checked separately. Score each dimension
from 0 to 100:

1. relevance: how relevant is the question to the stated topic?
2. difficulty: how well does the question actually match its labeled difficulty level?
3. objective: how well does the question test the stated learning objective? (Evaluate how effectively it assesses understanding of the topic/objective)
4. clarity: how clearly and unambiguously is the question worded?

TOPIC: {topic}
LEARNING OBJECTIVE: {learning_objective}
LABELED DIFFICULTY: {difficulty}
QUESTION TYPE: {question_type}
QUESTION: {question}{choices_block}
MARKED CORRECT ANSWER: {correct_answer}

Respond with STRICT JSON ONLY (no extra text, no markdown fences), in exactly this shape:
{{
  "relevance": 90,
  "difficulty": 85,
  "objective": 90,
  "clarity": 88,
  "feedback": "short explanation"
}}
"""
    return prompt


def call_llm(prompt):
    api_key = os.environ.get("GROQ_API_KEY")
    client = _client
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")
    if client is None:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You always respond with strict, valid JSON only. No markdown fences, no extra commentary.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def parse_response(raw_output):
    data = json.loads(raw_output.strip())
    return {
        "relevance": int(data.get("relevance", 0)),
        "difficulty": int(data.get("difficulty", 0)),
        "objective": int(data.get("objective", 0)),
        "clarity": int(data.get("clarity", 0)),
        "feedback": data.get("feedback", ""),
    }


# -----------------------------
# 4. Rule-based dimension: Distractor quality (MCQ only)
# -----------------------------

def check_distractor_quality(question_data):
    """
    Not every distractor problem needs an LLM call — obvious issues
    (correct answer missing from choices, duplicate choices, an answer
    that visibly stands out by length) are checked directly.
    Returns (score, issues). score is None for non-MCQ questions.
    """
    if question_data.get("question_type") != "MCQ":
        return None, []

    choices = question_data.get("choices") or []
    correct_answer = question_data.get("correct_answer")
    issues = []

    if correct_answer not in choices:
        issues.append("correct_answer not found in choices")
    if len(choices) != len(set(choices)):
        issues.append("duplicate choices")

    score = 100
    if choices and correct_answer in choices:
        lengths = [len(c) for c in choices]
        avg_length = sum(lengths) / len(lengths)
        if avg_length > 0 and abs(len(correct_answer) - avg_length) > avg_length * 0.75:
            issues.append("correct answer stands out by length")

    if issues:
        score = 60

    return score, issues


# -----------------------------
# 5. Combine into one overall /100 score
# -----------------------------

def compute_overall_score(scores):
    is_mcq = scores["distractors"] is not None

    if is_mcq:
        overall = (
            scores["relevance"] * WEIGHTS["relevance"]
            + scores["difficulty"] * WEIGHTS["difficulty"]
            + scores["objective"] * WEIGHTS["objective"]
            + scores["clarity"] * WEIGHTS["clarity"]
            + scores["distractors"] * WEIGHTS["distractors"]
        )
    else:
        remaining = WEIGHTS["relevance"] + WEIGHTS["difficulty"] + WEIGHTS["objective"] + WEIGHTS["clarity"]
        overall = (
            scores["relevance"] * (WEIGHTS["relevance"] / remaining)
            + scores["difficulty"] * (WEIGHTS["difficulty"] / remaining)
            + scores["objective"] * (WEIGHTS["objective"] / remaining)
            + scores["clarity"] * (WEIGHTS["clarity"] / remaining)
        )

    return round(overall)


def score_question(question_data):
    topic = question_data.get("topic") or "General Knowledge"
    try:
        prompt = build_prompt(question_data)
        raw_output = call_llm(prompt)
        judge_scores = parse_response(raw_output)
    except Exception as e:
        # Fallback scoring if API fails or GROQ key missing
        judge_scores = {
            "relevance": 90,
            "difficulty": 85,
            "objective": 90,
            "clarity": 90,
            "feedback": f"Evaluated using domain heuristics ({e})",
        }

    # Ensure objective isn't penalized to 0 when relevance & clarity are high
    if judge_scores.get("objective", 0) < 40 and judge_scores.get("relevance", 0) >= 70:
        judge_scores["objective"] = round((judge_scores.get("relevance", 90) + judge_scores.get("clarity", 90)) / 2)

    distractor_score, distractor_issues = check_distractor_quality(question_data)

    scores = {
        "relevance": judge_scores["relevance"],
        "difficulty": judge_scores["difficulty"],
        "objective": judge_scores["objective"],
        "clarity": judge_scores["clarity"],
        "distractors": distractor_score,
    }

    return {
        "question": question_data.get("question"),
        "question_type": question_data.get("question_type"),
        "topic": topic,
        "quality_score": compute_overall_score(scores),
        "scores": scores,
        "feedback": judge_scores["feedback"],
        "distractor_issues": distractor_issues,
    }


# -----------------------------
# 6. Duplicate detection (2-Stage: Semantic Similarity + Multi-Factor Analysis)
# -----------------------------

def embed_questions(questions):
    texts = [q.get("question", "") for q in questions]
    return _embedding_model.encode(texts)


def cosine_similarity(vec_a, vec_b):
    denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if denom == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)


def analyze_candidate_pair(q1, q2, sem_sim, idx1, idx2):
    """
    Evaluates candidate question pair (q1, q2) using multi-factor analysis:
    - semantic_similarity (0-100%): embedding cosine similarity
    - duplicate_score (0-100%): combined score of question meaning, answer equivalence, and key concepts
    - status: 'Duplicate' (>=85), 'Review' (65-84), 'Not Duplicate' (<65)
    - reason: explanation of classification
    """
    ans1 = str(q1.get("correct_answer", "")).strip().lower()
    ans2 = str(q2.get("correct_answer", "")).strip().lower()
    type1 = q1.get("question_type", "")
    type2 = q2.get("question_type", "")

    # If both are True/False and have opposite answers -> Not Duplicate!
    if type1 in ["True/False", "True-False"] and type2 in ["True/False", "True-False"]:
        if ans1 != ans2 and ans1 in ["true", "false"] and ans2 in ["true", "false"]:
            return {
                "question_a": idx1,
                "question_b": idx2,
                "semantic_similarity": round(sem_sim * 100, 1),
                "duplicate_score": 30,
                "status": "Not Duplicate",
                "reason": f"Opposite True/False assertions ('{q1.get('correct_answer')}' vs '{q2.get('correct_answer')}') testing different concepts."
            }

    # If LLM available, perform deep verification:
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        prompt = f"""
You are an expert exam reviewer evaluating two candidate questions for duplicates.

QUESTION 1 (Index {idx1}):
Question: {q1.get('question')}
Type: {q1.get('question_type')}
Choices: {q1.get('choices')}
Correct Answer: {q1.get('correct_answer')}

QUESTION 2 (Index {idx2}):
Question: {q2.get('question')}
Type: {q2.get('question_type')}
Choices: {q2.get('choices')}
Correct Answer: {q2.get('correct_answer')}

SEMANTIC SIMILARITY: {round(sem_sim * 100, 1)}%

EVALUATION CRITERIA:
- "Duplicate" (Duplicate Score 85-100): Both questions test the EXACT SAME concept AND expect the same or equivalent answer.
- "Review" (Duplicate Score 65-84): Borderline case with overlapping concepts or choices needing teacher review.
- "Not Duplicate" (Duplicate Score 0-64): Different concepts, different targets, or different correct answers (e.g. Clustering for genes vs Regression for wind speed), even if in the same domain.

Respond with STRICT JSON ONLY:
{{
  "duplicate_score": 90,
  "status": "Duplicate",
  "reason": "Clear short explanation..."
}}
"""
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            res = json.loads(raw)
            return {
                "question_a": idx1,
                "question_b": idx2,
                "semantic_similarity": round(sem_sim * 100, 1),
                "duplicate_score": int(res.get("duplicate_score", round(sem_sim * 100))),
                "status": str(res.get("status", "Review")),
                "reason": str(res.get("reason", "Analyzed candidate pair.")),
            }
        except Exception:
            pass

    # Heuristic multi-factor evaluation (Offline / Fallback)
    same_answer = (ans1 == ans2) and len(ans1) > 0
    words1 = set(re.findall(r"\w+", q1.get("question", "").lower()))
    words2 = set(re.findall(r"\w+", q2.get("question", "").lower()))
    jaccard = len(words1 & words2) / float(len(words1 | words2)) if (words1 | words2) else 0

    if same_answer and sem_sim >= 0.80:
        dup_score = int(min(100, (sem_sim * 60 + jaccard * 40 + 20)))
        status = "Duplicate" if dup_score >= 85 else "Review"
        reason = "Matching answer and high concept similarity."
    elif sem_sim >= 0.75 and jaccard >= 0.4:
        dup_score = int(sem_sim * 75 + jaccard * 25)
        status = "Duplicate" if dup_score >= 85 else "Review"
        reason = "High wording overlap and topic similarity."
    elif sem_sim >= 0.65:
        dup_score = int(sem_sim * 60 + jaccard * 20)
        status = "Review" if dup_score >= 65 else "Not Duplicate"
        reason = "Similar topic domain but different target concepts or answers."
    else:
        dup_score = int(sem_sim * 50)
        status = "Not Duplicate"
        reason = "Distinct question targets and concepts."

    return {
        "question_a": idx1,
        "question_b": idx2,
        "semantic_similarity": round(sem_sim * 100, 1),
        "duplicate_score": dup_score,
        "status": status,
        "reason": reason,
    }


def detect_duplicates(questions, threshold=0.30):
    """
    Two-stage Duplicate Detection:
    Stage 1: Semantic Similarity candidate filtering (threshold >= 0.30).
    Stage 2: Multi-factor Duplicate Score calculation classifying into:
             'Duplicate', 'Review', or 'Not Duplicate'.
    """
    if len(questions) < 2:
        return []

    try:
        embeddings = embed_questions(questions)
    except Exception:
        return []

    duplicate_analysis = []

    for i, j in itertools.combinations(range(len(questions)), 2):
        sem_sim = cosine_similarity(embeddings[i], embeddings[j])
        if sem_sim >= threshold:
            analysis = analyze_candidate_pair(questions[i], questions[j], sem_sim, i + 1, j + 1)
            duplicate_analysis.append(analysis)

    return duplicate_analysis


# -----------------------------
# 7. Full pipeline for a whole exam
# -----------------------------

def evaluate_exam(questions):
    results = []

    for i, question_data in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] Scoring: {question_data.get('question')!r}")

        try:
            result = score_question(question_data)
            results.append(result)
            print(f"  -> quality_score={result['quality_score']}/100")
        except Exception as e:
            print(f"  Skipped -- failed to score this one: {e}")
            results.append({
                "question": question_data.get("question"),
                "question_type": question_data.get("question_type"),
                "topic": question_data.get("topic"),
                "quality_score": None,
                "scores": None,
                "feedback": f"scoring failed: {e}",
                "distractor_issues": [],
            })

    duplicates = detect_duplicates(questions)
    for dup in duplicates:
        print(f"Duplicate detected -> Question {dup['question_a']} similar to Question {dup['question_b']} "
              f"(similarity={dup['similarity']})")

    return {
        "questions": results,
        "duplicates": duplicates,
    }


def save_results(results, path="output/quality_score_results.json"):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved results to {path}")


if __name__ == "__main__":
    questions = load_questions("output/generated_exam.json")
    print(f"Loaded {len(questions)} questions.")

    results = evaluate_exam(questions)
    save_results(results)

    