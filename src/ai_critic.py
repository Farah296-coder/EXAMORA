import json
import os
from openai import OpenAI


_client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

LLM_MODEL = "openai/gpt-oss-20b"


def critique_question(question, quality_result):
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
    "problem 1",
    "problem 2"
  ],
  "suggestions": [
    "suggestion 1",
    "suggestion 2"
  ]
}}

If there are no meaningful problems, return:

{{
  "has_issues": false,
  "issues": [],
  "suggestions": []
}}
"""

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content

    return json.loads(content)


def regenerate_question(
    question,
    critique,
    topic,
    learning_objective,
    difficulty,
    question_type,
):
    prompt = f"""
You are an expert exam-question generator.

Regenerate the question based on the critic feedback.

ORIGINAL QUESTION:
{json.dumps(question, indent=2, ensure_ascii=False)}

CRITIQUE:
{json.dumps(critique, indent=2, ensure_ascii=False)}

You MUST preserve these constraints:

Topic:
{topic}

Learning Objective:
{learning_objective}

Difficulty:
{difficulty}

Question Type:
{question_type}

Fix the problems identified by the critic.

For an MCQ:
- Provide exactly 4 choices.
- Provide one correct answer.
- Make distractors plausible.
- Do not reveal the answer through wording.
- Keep the question clear and unambiguous.

Return ONLY valid JSON:

{{
  "question_type": "{question_type}",
  "question": "...",
  "correct_answer": "...",
  "choices": [
    "...",
    "...",
    "...",
    "..."
  ]
}}
"""

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.4,
    )

    content = response.choices[0].message.content

    return json.loads(content)


def validate_regenerated_question(
    question,
    question_type,
):
    if question.get("question_type") != question_type:
        return False

    if question_type == "MCQ":
        choices = question.get("choices", [])

        if len(choices) != 4:
            return False

        if question.get("correct_answer") not in choices:
            return False

    return True


def smart_regenerate(
    question,
    quality_result,
    topic,
    learning_objective,
    difficulty,
    question_type,
):
    critique = critique_question(
        question,
        quality_result
    )

    if not critique["has_issues"]:
        return {
            "original_question": question,
            "critique": critique,
            "regenerated": False,
            "final_question": question,
        }

    new_question = regenerate_question(
        question=question,
        critique=critique,
        topic=topic,
        learning_objective=learning_objective,
        difficulty=difficulty,
        question_type=question_type,
    )

    is_valid = validate_regenerated_question(
        new_question,
        question_type,
    )

    if not is_valid:
        return {
            "original_question": question,
            "critique": critique,
            "regenerated": False,
            "final_question": question,
            "error": "Regenerated question failed validation",
        }

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
            "distractor_issues": quality_item.get(
                "distractor_issues", []
            ),
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

    print(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False
        )
    )