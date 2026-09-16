import json
import os
from openai import OpenAI

_client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

LLM_MODEL = "openai/gpt-oss-20b"


def load_questions(path="output/generated_exam.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_source_pages(path="output/extracted_text.json"):
    with open(path, "r", encoding="utf-8") as f:
        pages = json.load(f)
    return {page["page"]: page["text"] for page in pages}


def get_source_text(source_pages, pages_by_number):
    parts = []
    for page in source_pages or []:
        text = pages_by_number.get(page, "")
        if text:
            parts.append(f"[Page {page}]\n{text}")
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
  "reason": "short explanation of why this verdict was chosen",
  "supported_by_source": true
}}
"""
    return prompt


def call_llm(prompt):
    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You always respond with strict, valid JSON only. No markdown fences, no extra commentary."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def parse_response(raw_output):
    data = json.loads(raw_output.strip())

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


def validate_exam(questions, pages_by_number):
    results = []

    for i, question_data in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] Validating: {question_data.get('question')!r}")

        try:
            result = validate_question(question_data, pages_by_number)
            results.append(result)
            print(f"  -> verdict={result['verdict']}")
        except Exception as e:
            print(f"  Skipped -- failed to validate this one: {e}")

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