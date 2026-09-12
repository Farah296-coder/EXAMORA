import json
import os

from exam_blueprint import build_blueprint_from_file, build_generation_requests
from question_generator import QUESTION_TYPES, call_llm
from rag_search import retrieve_for_question


def get_context(request: dict, top_k: int = 3):
    learning_objective = request.get("learning_objective") or ""
    retrieval = retrieve_for_question(
        topic=request["topic"],
        learning_objective=learning_objective,
        top_k=top_k,
    )
    return retrieval["context"], retrieval["source_pages"]


def build_prompt(context: str, request: dict) -> str:
    question_type = request["question_type"]
    difficulty = request["difficulty"]
    topic = request["topic"]
    objective = request.get("learning_objective")

    if question_type not in QUESTION_TYPES:
        raise ValueError(f"question_type must be one of {QUESTION_TYPES}")

    objective_line = f"Learning objective: {objective}\n" if objective else ""

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

    prompt = f"""You are an assistant that writes exam questions for a teacher.
Use ONLY the information in the CONTEXT below. Do not invent facts that are not in it.
The context may include multiple [Page N] sections from different pages.

Topic: {topic}
{objective_line}Question type required: {question_type}
Difficulty required: {difficulty}

Respond with STRICT JSON ONLY (no extra text, no markdown fences), matching exactly
this shape:
{shape}

CONTEXT:
\"\"\"
{context}
\"\"\"
"""
    return prompt


def parse_response(raw_output: str, request: dict, source_pages: list) -> dict:
    try:
        data = json.loads(raw_output.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}\nRaw output:\n{raw_output}")

    structured = {
        "topic": request["topic"],
        "learning_objective": request.get("learning_objective"),
        "question_type": request["question_type"],
        "difficulty": request["difficulty"],
        "question": data.get("question"),
        "correct_answer": data.get("correct_answer"),
        "source_pages": source_pages,
    }

    if request["question_type"] in ("MCQ", "True-False"):
        structured["choices"] = data.get("choices")

    return structured


def generate_one(request: dict) -> dict:
    context, source_pages = get_context(request)
    prompt = build_prompt(context, request)
    raw_output = call_llm(prompt)
    return parse_response(raw_output, request, source_pages)


def generate_exam(requests: list) -> list:
    exam = []
    for i, request in enumerate(requests, start=1):
        print(f"[{i}/{len(requests)}] Generating {request['question_type']} "
              f"({request['difficulty']}) on '{request['topic']}'...")
        try:
            question = generate_one(request)
            exam.append(question)
        except Exception as e:
            print(f"  Skipped, failed to generate this one: {e}")
    return exam


def save_exam(exam: list, path: str = "output/generated_exam.json"):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(exam, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(exam)} questions to {path}")


if __name__ == "__main__":
    blueprint = build_blueprint_from_file()
    requests = build_generation_requests(blueprint)

    exam = generate_exam(requests)
    save_exam(exam)