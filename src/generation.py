import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

from exam_blueprint import build_blueprint_from_file, build_generation_requests
from question_generator import QUESTION_TYPES, call_llm
from rag_search import retrieve_for_question


def clean_text(value):
    """
    Removes accidental HTML/markdown formatting from generated text.
    Keeps normal text such as Java generics: <T>.
    """
    if not isinstance(value, str):
        return value

    value = value.strip()

    # Remove markdown code fences
    value = re.sub(r"```(?:html|json|text)?", "", value, flags=re.IGNORECASE)
    value = value.replace("```", "")

    # Remove common HTML tags only
    value = re.sub(
        r"</?(?:p|div|span|strong|b|em|i|br|ul|ol|li|code|pre)[^>]*>",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Decode a few common HTML entities
    value = (
        value.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )

    return value.strip()


def clean_choices(choices):
    if not isinstance(choices, list):
        return choices

    return [clean_text(choice) for choice in choices]


def get_context(request: dict, top_k: int = 4):
    """
    Retrieve relevant PDF context using only the topic.
    Learning objectives are intentionally NOT used.
    """
    topic = request.get("topic", "").strip()

    retrieval = retrieve_for_question(
        topic=topic,
        learning_objective="",
        top_k=top_k,
    )

    return retrieval["context"], retrieval["source_pages"]


def build_prompt(context: str, request: dict) -> str:
    question_type = request["question_type"]
    difficulty = request["difficulty"]
    topic = request["topic"]

    if question_type not in QUESTION_TYPES:
        raise ValueError(
            f"question_type must be one of {QUESTION_TYPES}"
        )

    if question_type == "MCQ":
        shape = """{
  "question": "string",
  "choices": ["string", "string", "string", "string"],
  "correct_answer": "string (must exactly match one of the choices)"
}"""

    elif question_type == "True-False":
        shape = """{
  "question": "string",
  "choices": ["True", "False"],
  "correct_answer": "True or False"
}"""

    else:
        shape = """{
  "question": "string",
  "correct_answer": "string (a short, direct answer)"
}"""

    prompt = f"""
You are an expert exam-question generator helping a teacher.

Your job is to create ONE high-quality exam question from the provided
educational PDF context.

IMPORTANT RULES:

1. Use ONLY information supported by the CONTEXT.
2. Do NOT invent facts.
3. Do NOT mention the PDF, context, source, or these instructions.
4. Do NOT use a learning objective.
5. Do NOT simply repeat the topic as the question.
6. The question must test understanding of the material, not just repeat
   the phrase "{topic}".
7. Make the question meaningfully different from a simple definition question.
8. Avoid asking "What is {topic}?" unless the context genuinely requires
   a definition and there is no better question.
9. For MCQs, create plausible distractors based on common misunderstandings,
   but every option must be supported by the context or clearly incorrect
   according to the context.
10. Return STRICT JSON ONLY.
11. Do NOT return HTML.
12. Do NOT return Markdown.
13. Do NOT wrap the JSON in ```.

Topic: {topic}

Question type: {question_type}

Difficulty: {difficulty}

Required JSON shape:

{shape}

CONTEXT:
\"\"\"
{context}
\"\"\"

Generate exactly ONE question.
"""

    return prompt


def parse_response(raw_output: str, request: dict, source_pages: list) -> dict:
    raw_output = raw_output.strip()

    # Remove accidental markdown fences before JSON parsing
    raw_output = re.sub(
        r"^```(?:json)?\s*",
        "",
        raw_output,
        flags=re.IGNORECASE,
    )
    raw_output = re.sub(r"\s*```$",
                        "",
                        raw_output)

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as first_error:
        start = raw_output.find("{")
        end = raw_output.rfind("}")

        if start == -1 or end <= start:
            raise ValueError(
                f"LLM did not return valid JSON: {first_error}\n"
                f"Raw output:\n{raw_output}"
            )

        try:
            data = json.loads(raw_output[start:end + 1])
        except json.JSONDecodeError as second_error:
            raise ValueError(
                f"LLM did not return valid JSON: {second_error}\n"
                f"Raw output:\n{raw_output}"
            )

    structured = {
        "topic": request["topic"],
        "question_type": request["question_type"],
        "difficulty": request["difficulty"],
        "question": clean_text(data.get("question")),
        "correct_answer": clean_text(data.get("correct_answer")),
        "source_pages": source_pages,
    }

    if request["question_type"] in ("MCQ", "True-False"):
        structured["choices"] = clean_choices(data.get("choices"))

    return structured


def generate_one(request: dict) -> dict:
    context, source_pages = get_context(request)

    prompt = build_prompt(context, request)

    raw_output = call_llm(prompt)

    return parse_response(
        raw_output,
        request,
        source_pages,
    )


MAX_WORKERS = 6


def try_generate(request: dict):
    try:
        return generate_one(request), None
    except Exception as e:
        return None, e


def run_batch(requests: list, label: str):
    if not requests:
        return [], []

    print(f"{label}: {len(requests)} questions, {MAX_WORKERS} at a time...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        outcomes = list(pool.map(try_generate, requests))

    done = []
    failed = []

    for request, (question, error) in zip(requests, outcomes):
        if question is not None:
            done.append(question)
        else:
            print(f"  {request['question_type']} on '{request['topic']}' failed: {error}")
            failed.append(request)

    return done, failed


def generate_exam(requests: list) -> list:
    exam, failed = run_batch(requests, "Generating")

    if failed:
        recovered, dropped = run_batch(failed, "Retrying")
        exam.extend(recovered)

        for request in dropped:
            print(f"  Dropped after retry: {request['question_type']} on '{request['topic']}'")

    return exam


def save_exam(exam: list, path: str = "output/generated_exam.json"):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            exam,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Saved {len(exam)} questions to {path}")


if __name__ == "__main__":
    blueprint = build_blueprint_from_file()
    requests = build_generation_requests(blueprint)

    exam = generate_exam(requests)

    save_exam(exam)
