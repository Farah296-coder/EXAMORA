import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

_client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1",
)

LLM_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

MAX_WORKERS = 3
LLM_ATTEMPTS = 2
MAX_OUTPUT_TOKENS = 220

_fast_mode = True


def fast_completion(messages, temperature, max_tokens=MAX_OUTPUT_TOKENS):
    global _fast_mode

    if _fast_mode:
        try:
            return _client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body={"reasoning_effort": "low"},
            )
        except Exception as e:
            text = str(e).lower()
            if "rate" in text or "429" in text or "timeout" in text:
                raise
            _fast_mode = False

    return _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def load_questions(path="output/generated_exam.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_source_pages(path="output/extracted_text.json"):
    with open(path, "r", encoding="utf-8") as f:
        pages = json.load(f)
    return {page["page"]: page["text"] for page in pages}


MAX_CHARS_PER_PAGE = 1100
MAX_SOURCE_CHARS = 4000


def get_source_text(source_pages, pages_by_number):
    parts = []
    used = 0

    for page in source_pages or []:
        text = pages_by_number.get(page, "")
        if not text:
            continue

        text = text[:MAX_CHARS_PER_PAGE]

        if used + len(text) > MAX_SOURCE_CHARS:
            text = text[: max(0, MAX_SOURCE_CHARS - used)]

        if not text:
            break

        parts.append(f"[Page {page}]\n{text}")
        used += len(text)

        if used >= MAX_SOURCE_CHARS:
            break

    return "\n\n".join(parts)


def build_prompt(question_data, source_text):
    question_type = question_data.get("question_type")
    topic = question_data.get("topic")
    learning_objective = question_data.get("learning_objective")
    question = question_data.get("question")
    correct_answer = question_data.get("correct_answer")
    choices = question_data.get("choices")

    choices_block = f"\nChoices: {choices}" if choices else ""

    prompt = f"""You are validating an exam question for grounding and correctness.
Use ONLY the SOURCE TEXT below , do not use outside knowledge.

QUESTION TYPE: {question_type}
TOPIC: {topic}
LEARNING OBJECTIVE: {learning_objective}
QUESTION: {question}{choices_block}
MARKED CORRECT ANSWER: {correct_answer}

SOURCE TEXT:
\"\"\"
{source_text}
\"\"\"

Decide a verdict:
- "Correct": the question is grounded in the source text AND the marked answer is correct.
- "Incorrect": the question is grounded in the source text BUT the marked answer is wrong.
- "Unsupported": the question's content is not actually present in the source text (hallucinated/invented), so it cannot be verified.

Respond with STRICT JSON ONLY (no extra text, no markdown fences), in exactly this shape:
{{
  "verdict": "Correct",
  "reason": "why, in at most 25 words",
  "supported_by_source": true
}}
"""
    return prompt


def retry_delay(error, attempt):
    match = re.search(r"try again in ([0-9.]+)s", str(error))
    if match:
        try:
            return min(float(match.group(1)) + 0.5, 25.0)
        except ValueError:
            pass
    return 2.0 * (attempt + 1)


def call_llm(prompt):
    last_error = None

    messages = [
        {"role": "system", "content": "You always respond with strict, valid JSON only. No markdown fences, no extra commentary."},
        {"role": "user", "content": prompt},
    ]

    for attempt in range(LLM_ATTEMPTS):
        try:
            response = fast_completion(messages, 0.2)
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            if attempt + 1 < LLM_ATTEMPTS:
                time.sleep(retry_delay(e, attempt))

    raise last_error


def parse_response(raw_output):
    text = (raw_output or "").strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"model returned no JSON: {text[:120]!r}")
        data = json.loads(text[start:end + 1])

    verdict = data.get("verdict", "Unsupported")
    if verdict not in ("Correct", "Incorrect", "Unsupported"):
        verdict = "Unsupported"

    return {
        "verdict": verdict,
        "reason": data.get("reason", ""),
        "supported_by_source": bool(data.get("supported_by_source", False)),
    }


def validate_question(question_data, pages_by_number):
    source_pages = question_data.get("source_pages") or []
    source_text = get_source_text(source_pages, pages_by_number)

    prompt = build_prompt(question_data, source_text)
    raw_output = call_llm(prompt)
    result = parse_response(raw_output)

    return {
        "question": question_data.get("question"),
        "question_type": question_data.get("question_type"),
        "topic": question_data.get("topic"),
        "learning_objective": question_data.get("learning_objective"),
        "source_pages": source_pages,
        "verdict": result["verdict"],
        "reason": result["reason"],
        "supported_by_source": result["supported_by_source"],
    }


def validate_one_safely(question_data, pages_by_number):
    try:
        return validate_question(question_data, pages_by_number)
    except Exception as e:
        return {
            "question": question_data.get("question"),
            "question_type": question_data.get("question_type"),
            "topic": question_data.get("topic"),
            "learning_objective": question_data.get("learning_objective"),
            "source_pages": question_data.get("source_pages") or [],
            "verdict": "Not evaluated",
            "reason": f"validation failed: {e}",
            "supported_by_source": False,
        }


def validate_exam(questions, pages_by_number):
    print(f"Validating {len(questions)} questions ({MAX_WORKERS} at a time)...")

    def validate(question_data):
        return validate_one_safely(question_data, pages_by_number)

    if len(questions) <= 1:
        results = [validate(question) for question in questions]
    else:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            results = list(pool.map(validate, questions))

    for i, result in enumerate(results, start=1):
        print(f"[{i}/{len(results)}] verdict={result['verdict']} :: {result['question']!r}")

    return results


def save_results(results, path="output/grounding_results.json"):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(results)} results to {path}")


if __name__ == "__main__":
    questions = load_questions("output/generated_exam.json")
    print(f"Loaded {len(questions)} questions.")

    pages_by_number = load_source_pages("output/extracted_text.json")
    print(f"Loaded {len(pages_by_number)} source pages.")

    results = validate_exam(questions, pages_by_number)

    save_results(results)