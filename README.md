# Prompt + Question Generation

This module covers the **Prompt + Question Generation** part of the pipeline: turning retrieved context into a structured, ready-to-use exam question.

## Where it fits in the pipeline

## File

- `src/question_generator.py`

## Setup

Install dependencies:

```bash
pip install openai chromadb sentence-transformers pymupdf
```

This module uses **Groq** (free, OpenAI-compatible API) as the LLM provider. You'll need a free API key from [console.groq.com/keys](https://console.groq.com/keys).

Set it as an environment variable:

```bash
# macOS / Linux
export GROQ_API_KEY="gsk_..."

# Windows (PowerShell / cmd)
setx GROQ_API_KEY "gsk_..."
```

> Model in use: `openai/gpt-oss-20b`.

## How it works

| Function | What it does |
|---|---|
| `build_prompt(context, question_type, topic_hint)` | Builds the instruction prompt sent to the LLM, embedding the retrieved context and specifying the exact JSON shape expected back. |
| `call_llm(prompt)` | Sends the prompt to Groq and returns the raw text response. |
| `parse_llm_response(raw_output, question_type, source_page)` | Parses the LLM's response into a fixed dict structure. Raises a clear error if the LLM didn't return valid JSON. |
| `generate_question(context, question_type, source_page, topic_hint)` | Runs the full pipeline for one piece of context: prompt → LLM → parsed output. |
| `generate_from_topic(topic, question_type, top_k)` | Same as above, but pulls the context automatically from Habiba's `rag_search.search_question()` given just a topic string. |
| `generate_quiz(requests)` | Generates multiple questions at once from a list of `{topic, question_type}` requests. Skips and logs any individual question that fails instead of crashing the whole batch. |
| `save_quiz(quiz, path)` | Saves a generated quiz to a JSON file for handoff. |

Supported question types: `MCQ`, `True-False`, `Short Answer`.

## Example usage

Generate one question:

```python
from question_generator import generate_from_topic

question = generate_from_topic("generic classes and methods", "MCQ")
print(question)
```

Generate a full quiz and save it:

```python
from question_generator import generate_quiz, save_quiz

quiz_requests = [
    {"topic": "generic classes", "question_type": "MCQ"},
    {"topic": "generic classes", "question_type": "True-False"},
    {"topic": "generic methods", "question_type": "Short Answer"},
]

quiz = generate_quiz(quiz_requests)
save_quiz(quiz)  # -> output/generated_quiz.json
```

## Output format

Every generated question follows this structure:

**MCQ**
```json
{
  "question_type": "MCQ",
  "question": "What is a generic class?",
  "choices": ["...", "...", "...", "..."],
  "correct_answer": "...",
  "source_page": 2
}
```

**True-False**
```json
{
  "question_type": "True-False",
  "question": "Generics provide compile-time type safety.",
  "choices": ["True", "False"],
  "correct_answer": "True",
  "source_page": 2
}
```

**Short Answer**
```json
{
  "question_type": "Short Answer",
  "question": "What do generics allow a class to operate on?",
  "correct_answer": "Objects of various types",
  "source_page": 2
}
```

## Notes

- `correct_answer` for MCQ/True-False always matches one of the entries in `choices` exactly, so it can be used directly for automated grading.
- Groq's free tier has rate limits — if you hit a `rate_limit_exceeded` error while batch-generating a quiz, wait a bit and retry.





# Phase 4 — AI Integration + APIs

## Overview

Phase 4 integrates the existing AI pipeline with a FastAPI backend and provides API endpoints that can be used by the frontend.

The main implementation is in:

`src/api.py`

The API layer connects the existing project modules without reimplementing their AI logic.

## What Was Implemented

Phase 4 provides the following functionality:

- Connects Exam Settings with the AI pipeline.
- Generates exams through an API endpoint.
- Connects the Quality Score module.
- Detects duplicate questions.
- Validates generated questions against the source material.
- Supports question regeneration using the AI Critic.
- Provides a health-check endpoint.
- Returns a consistent response format for frontend integration.

## Connected Modules

`api.py` integrates the following existing modules:

- `exam_settings.py`
- `exam_blueprint.py`
- `generation.py`
- `rag_search.py`
- `quality_score.py`
- `grounding_validation.py`
- `ai_critic.py`

`api.py` acts as the integration layer between the frontend and these modules.

## Compatibility Bridge

During integration, `generation.py` expected a function called `retrieve_for_question()`, while the existing `rag_search.py` provided `search_question()`.

To avoid modifying teammate-owned files, a small compatibility bridge was implemented inside `api.py`.

The bridge uses the existing `search_question()` function and converts its results into the format expected by the generation pipeline.

Therefore, only `api.py` was modified for this integration.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Checks whether the API is running and whether the GROQ API key is available |
| POST | `/api/exam-settings` | Creates and saves exam settings |
| POST | `/api/generate-exam` | Runs the AI exam-generation pipeline |
| POST | `/api/quality-score` | Evaluates the quality of generated questions |
| POST | `/api/duplicates` | Detects duplicate or highly similar questions |
| POST | `/api/validate` | Validates questions against the source material |
| POST | `/api/regenerate` | Regenerates a question when improvement is required |

## API Response Format

All endpoints follow a consistent response structure.

Successful response:

```json
{
  "success": true,
  "data": {}
}


How to Run

From the project root, activate the virtual environment:

source .venv/bin/activate

Make sure the GROQ API key is available:

export GROQ_API_KEY="YOUR_GROQ_API_KEY"

Then verify the API import:

python -c "import sys; sys.path.insert(0, 'src'); import api; print('API IMPORT OK')"

Expected output:

API IMPORT OK

Start the FastAPI server:

uvicorn api:app --app-dir src --reload --port 8000
Swagger UI

After starting the server, open the following URL in Chrome:

http://127.0.0.1:8000/docs

This opens the Swagger UI, where all API endpoints can be viewed and tested directly from the browser.

For example, the first endpoint to test is:

GET /api/health

Click Try it out → Execute.

A successful response should look like:

{
  "success": true,
  "data": {
    "status": "up",
    "groq_key_set": true
  }
}
Important Note

http://127.0.0.1:8000/docs is a local URL. It works only while the FastAPI server is running on the current computer.

To access the Swagger UI again:

Activate the virtual environment.
Set the GROQ API key.
Start the FastAPI server.
Open http://127.0.0.1:8000/docs in Chrome.
Phase 4 Result

Phase 4 provides a working FastAPI layer that exposes the existing AI functionality through frontend-ready APIs.

The final integration connects:

Exam Settings → AI Generation → Quality Score → Duplicate Detection → Validation → Regeneration

and makes the complete AI pipeline accessible through the FastAPI backend.
