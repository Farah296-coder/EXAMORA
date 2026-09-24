import json
import os
import re
from openai import OpenAI


_groq_key = os.environ.get("GROQ_API_KEY", "")
_client = OpenAI(
    api_key=_groq_key or "placeholder_key",
    base_url="https://api.groq.com/openai/v1",
) if _groq_key else None

LLM_MODEL = "openai/gpt-oss-20b"


def get_llm_client():
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return None
    return OpenAI(
        api_key=key,
        base_url="https://api.groq.com/openai/v1",
    )


def critique_question(question, quality_result):
    client = get_llm_client()
    if not client:
        return {
            "has_issues": False,
            "issues": [],
            "suggestions": []
        }

    prompt = f"""
You are an AI exam-quality critic.

Analyze the following exam question.

QUESTION:
{json.dumps(question, indent=2, ensure_ascii=False)}

QUALITY SCORE:
{json.dumps(quality_result, indent=2, ensure_ascii=False)}

Identify any problems related to:
- correctness
- clarity
- relevance
- difficulty
- learning objective alignment
- MCQ distractor quality

Return ONLY valid JSON in this format:

{{
  "has_issues": true,
  "issues": [
    "problem 1"
  ],
  "suggestions": [
    "suggestion 1"
  ]
}}

If there are no meaningful problems, return:

{{
  "has_issues": false,
  "issues": [],
  "suggestions": []
}}
"""
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        return json.loads(content.strip())
    except Exception as e:
        return {
            "has_issues": False,
            "issues": [],
            "suggestions": []
        }


def regenerate_question(
    question,
    critique,
    topic,
    learning_objective,
    difficulty,
    question_type,
):
    client = get_llm_client()
    target_type = question_type or question.get("question_type", "MCQ")
    if target_type == "True-False":
        target_type = "True/False"

    orig_q_text = question.get("question", "")
    orig_ans = question.get("correct_answer", "")
    orig_choices = question.get("choices", [])
    topic = topic or question.get("topic", "General")
    difficulty = difficulty or question.get("difficulty", "Medium")

    prompt = f"""
You are an expert exam-question generator.

Your task is to RE-WRITE and RE-STRUCTURE the question to fit the target Question Type: "{target_type}".
Do NOT simply return the original question wording with a different label. You MUST rewrite the statement/question phrasing so it is fully appropriate for the "{target_type}" format.

ORIGINAL QUESTION DETAILS:
- Question Text: {orig_q_text}
- Original Type: {question.get("question_type")}
- Original Correct Answer: {orig_ans}
- Original Choices: {orig_choices}
- Topic: {topic}
- Difficulty: {difficulty}

TARGET QUESTION TYPE CONSTRAINTS:
1. If Target Type is "True/False" (or "True-False"):
   - Write a clear, unambiguous declarative statement related to the concept.
   - Set "choices": ["True", "False"].
   - Set "correct_answer": "True" or "False" matching the truth value of the statement.

2. If Target Type is "MCQ":
   - Write a clear multiple-choice question phrasing.
   - Set "choices": Array of EXACTLY 4 distinct, plausible options.
   - Set "correct_answer": Must match ONE of the 4 choices EXACTLY.

3. If Target Type is "Short Answer":
   - Write a direct question requiring a concise response.
   - Set "choices": [].
   - Set "correct_answer": A clear, concise answer string.

Return ONLY valid JSON:
{{
  "question_type": "{target_type}",
  "question": "Newly rephrased question or statement...",
  "correct_answer": "...",
  "choices": [...]
}}
"""

    if client:
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            content = response.choices[0].message.content.strip()
            # Clean possible markdown blocks
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            parsed = json.loads(content)
            parsed["question_type"] = target_type
            return parsed
        except Exception as e:
            print(f"LLM regeneration call failed: {e}")

    # Heuristic fallback for offline/no-API key mode
    return fallback_rewrite_question(question, target_type, topic, difficulty)


def fallback_rewrite_question(question, target_type, topic, difficulty):
    orig_text = question.get("question", "")
    orig_ans = question.get("correct_answer", "")
    orig_choices = question.get("choices", [])

    if target_type in ["True/False", "True-False"]:
        # Convert to a True/False statement
        if "?" in orig_text:
            clean_stmt = orig_text.replace("What is", "").replace("Which of the following", "").replace("?", "").strip()
            stmt = f"Regarding {topic}: {clean_stmt} is accurately described by {orig_ans}."
        else:
            stmt = f"{orig_text} ({orig_ans})." if orig_ans and orig_ans not in orig_text else orig_text
        
        return {
            "question_type": "True/False",
            "question": stmt,
            "choices": ["True", "False"],
            "correct_answer": "True",
            "topic": topic,
            "difficulty": difficulty,
        }
    
    elif target_type == "Short Answer":
        # Convert to short answer
        clean_q = orig_text
        if not clean_q.endswith("?"):
            clean_q = f"What is the main role of {orig_text} in {topic}?"
        return {
            "question_type": "Short Answer",
            "question": clean_q,
            "choices": [],
            "correct_answer": orig_ans if orig_ans else f"Key concept of {topic}",
            "topic": topic,
            "difficulty": difficulty,
        }

    else:
        # Default MCQ
        choices = orig_choices if (isinstance(orig_choices, list) and len(orig_choices) == 4) else [
            orig_ans if orig_ans else "Correct Option",
            f"Alternative concept in {topic}",
            f"Secondary option for {topic}",
            f"None of the above"
        ]
        return {
            "question_type": "MCQ",
            "question": orig_text if orig_text.endswith("?") else f"Which of the following best describes {orig_text}?",
            "choices": choices,
            "correct_answer": choices[0],
            "topic": topic,
            "difficulty": difficulty,
        }


def validate_regenerated_question(
    question,
    question_type,
):
    if not isinstance(question, dict):
        return False

    q_type = question.get("question_type")
    if q_type == "True-False":
        q_type = "True/False"
    target_type = question_type
    if target_type == "True-False":
        target_type = "True/False"

    if q_type != target_type:
        question["question_type"] = target_type

    if target_type in ["True/False", "True-False"]:
        question["choices"] = ["True", "False"]
        ans = str(question.get("correct_answer", "")).capitalize()
        if ans not in ["True", "False"]:
            question["correct_answer"] = "True"

    elif target_type == "MCQ":
        choices = question.get("choices", [])
        if len(choices) != 4:
            return False
        if question.get("correct_answer") not in choices:
            question["choices"][0] = question.get("correct_answer", choices[0])

    elif target_type == "Short Answer":
        question["choices"] = []

    return True


def smart_regenerate(
    question,
    quality_result,
    topic,
    learning_objective,
    difficulty,
    question_type,
):
    target_type = question_type or question.get("question_type", "MCQ")
    if target_type == "True-False":
        target_type = "True/False"

    critique = critique_question(question, quality_result)

    new_question = regenerate_question(
        question=question,
        critique=critique,
        topic=topic,
        learning_objective=learning_objective,
        difficulty=difficulty,
        question_type=target_type,
    )

    is_valid = validate_regenerated_question(
        new_question,
        target_type,
    )

    if not is_valid:
        new_question = fallback_rewrite_question(question, target_type, topic, difficulty)

    return {
        "original_question": question,
        "critique": critique,
        "regenerated": True,
        "final_question": new_question,
    }


def process_quality_results(
    quality_results_path="output/quality_score_results.json",
    questions_path="output/generated_exam.json",
    topic="generic classes",
    learning_objective="Explain the purpose and benefits of generic classes",
    difficulty="Medium",
):
    with open(quality_results_path, "r", encoding="utf-8") as f:
        quality_data = json.load(f)

    with open(questions_path, "r", encoding="utf-8") as f:
        questions_data = json.load(f)

    results = []

    for question, quality_item in zip(
        questions_data,
        quality_data.get("questions", [])
    ):
        quality_result = {
            "quality_score": quality_item.get("quality_score"),
            "scores": quality_item.get("scores", {}),
            "feedback": quality_item.get("feedback", ""),
            "distractor_issues": quality_item.get("distractor_issues", []),
        }

        result = smart_regenerate(
            question=question,
            quality_result=quality_result,
            topic=topic,
            learning_objective=learning_objective,
            difficulty=difficulty,
            question_type=question.get("question_type", "MCQ"),
        )
        results.append(result)

    return results


if __name__ == "__main__":
    results = process_quality_results()
    print(json.dumps(results, indent=2, ensure_ascii=False))