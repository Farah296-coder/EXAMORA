import json
import time
import os
import re

from openai import OpenAI


QUESTION_TYPES = [
    "MCQ",
    "True-False",
    "Short Answer",
]


_client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

LLM_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")


def clean_text(value):
    if not isinstance(value, str):
        return value

    value = value.strip()

    value = re.sub(
        r"```(?:html|json|text)?",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = value.replace("```", "")

    value = re.sub(
        r"</?(?:p|div|span|strong|b|em|i|br|ul|ol|li|code|pre)[^>]*>",
        "",
        value,
        flags=re.IGNORECASE,
    )

    return (
        value
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .strip()
    )

def build_prompt(
    context: str,
    question_type: str,
    topic_hint: str = "",
    difficulty: str = "Medium",
) -> str:

    if question_type not in QUESTION_TYPES:
        raise ValueError(
            f"question_type must be one of {QUESTION_TYPES}"
        )

    if question_type == "MCQ":

        shape = """{
  "question": "string",
  "choices": ["string", "string", "string", "string"],
  "correct_answer": "string"
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
  "correct_answer": "string"
}"""

    topic_line = (
        f"Topic area: {topic_hint}"
        if topic_hint
        else ""
    )

    prompt = f"""
You are an expert educational assessment generator.

Create ONE exam question using ONLY the information in the CONTEXT.

Rules:

- Do not invent information.
- Do not use HTML.
- Do not use Markdown.
- Do not mention the context or PDF.
- Do not use learning objectives.
- Do not simply repeat the topic as a question.
- Prefer testing understanding, application, comparison, behavior,
  examples, or consequences when the context supports it.
- Avoid generating the same question repeatedly.
- Difficulty: {difficulty}
- Question type: {question_type}

{topic_line}

Return STRICT JSON ONLY.

Required shape:

{shape}

CONTEXT:
\"\"\"
{context}
\"\"\"

Generate exactly ONE question.
"""

    return prompt

LLM_ATTEMPTS = 3
MAX_OUTPUT_TOKENS = 600

_fast_mode = True


def fast_completion(client, messages, temperature, max_tokens=MAX_OUTPUT_TOKENS):
    global _fast_mode

    if _fast_mode:
        try:
            return client.chat.completions.create(
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

    return client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def retry_delay(error, attempt):
    match = re.search(r"try again in ([0-9.]+)s", str(error))
    if match:
        try:
            return min(float(match.group(1)) + 0.5, 25.0)
        except ValueError:
            pass
    return 2.0 * (attempt + 1)


def call_llm(prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an exam-generation assistant. "
                "Return strict valid JSON only. "
                "Never return HTML or Markdown."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    last_error = None

    for attempt in range(LLM_ATTEMPTS):
        try:
            response = fast_completion(_client, messages, 0.8)
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            if attempt + 1 < LLM_ATTEMPTS:
                time.sleep(retry_delay(e, attempt))

    raise last_error


def parse_llm_response(
    raw_output: str,
    question_type: str,
    source_page=None,
) -> dict:

    raw_output = raw_output.strip()

    raw_output = re.sub(
        r"^```(?:json)?\s*",
        "",
        raw_output,
        flags=re.IGNORECASE,
    )

    raw_output = re.sub(
        r"\s*```$",
        "",
        raw_output,
    )

    try:
        data = json.loads(raw_output)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"LLM did not return valid JSON: {e}\n"
            f"Raw output:\n{raw_output}"
        )

    structured = {
        "question_type": question_type,
        "question": clean_text(data.get("question")),
        "correct_answer": clean_text(
            data.get("correct_answer")
        ),
    }

    if question_type in ("MCQ", "True-False"):

        choices = data.get("choices", [])

        if isinstance(choices, list):
            choices = [
                clean_text(choice)
                for choice in choices
            ]

        structured["choices"] = choices

    if source_page is not None:
        structured["source_page"] = source_page

    return structured


def generate_question(
    context: str,
    question_type: str,
    source_page=None,
    topic_hint: str = "",
    difficulty: str = "Medium",
) -> dict:

    prompt = build_prompt(
        context=context,
        question_type=question_type,
        topic_hint=topic_hint,
        difficulty=difficulty,
    )

    raw_output = call_llm(prompt)

    return parse_llm_response(
        raw_output,
        question_type,
        source_page,
    )


def generate_from_topic(
    topic: str,
    question_type: str,
    top_k: int = 4,
    difficulty: str = "Medium",
):

    from rag_search import search_question

    results = search_question(
        topic,
        top_k=top_k,
    )

    if not results["documents"]:
        raise ValueError(
            "No relevant content found in the uploaded PDF."
        )

    context_parts = results["documents"][0]

    context = "\n\n".join(context_parts)

    pages = results["metadatas"][0]

    source_page = pages[0]["page"] if pages else None

    return generate_question(
        context=context,
        question_type=question_type,
        source_page=source_page,
        topic_hint=topic,
        difficulty=difficulty,
    )


def generate_quiz(requests: list) -> list:

    quiz = []

    for i, req in enumerate(requests, start=1):

        topic = req["topic"]
        question_type = req["question_type"]
        difficulty = req.get(
            "difficulty",
            "Medium",
        )

        print(
            f"[{i}/{len(requests)}] "
            f"Generating {question_type} "
            f"({difficulty}) on '{topic}'..."
        )

        try:

            question = generate_from_topic(
                topic=topic,
                question_type=question_type,
                difficulty=difficulty,
            )

            quiz.append(question)

        except Exception as e:

            print(
                f"  Skipped — failed to generate this one: {e}"
            )

    return quiz


def save_quiz(
    quiz: list,
    path: str = "output/generated_quiz.json",
):

    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            quiz,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"Saved {len(quiz)} questions to {path}"
    )


if __name__ == "__main__":

    mock_context = (
        "A generic class is a class that is parameterized "
        "over types. Generics allow classes and methods to "
        "operate on objects of various types while providing "
        "compile-time type safety."
    )

    prompt = build_prompt(
        mock_context,
        "MCQ",
        topic_hint="generic classes",
        difficulty="Medium",
    )

    print(prompt)