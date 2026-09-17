import os
import traceback
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import exam_settings
import exam_blueprint
import rag_search


# ============================================================
# Compatibility Bridge
# ============================================================
# generation.py expects:
#     retrieve_for_question()
#
# But the current rag_search.py provides:
#     search_question()
#
# We create the expected function here without modifying
# rag_search.py or generation.py.
# ============================================================

def retrieve_for_question(
    topic,
    learning_objective="",
    top_k=3
):
    query = topic

    if learning_objective:
        query += f" {learning_objective}"

    results = rag_search.search_question(
        query,
        top_k=top_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    context_parts = []
    source_pages = []

    for document, metadata in zip(documents, metadatas):
        metadata = metadata or {}

        page = metadata.get("page")

        if page is not None:
            context_parts.append(
                f"[Page {page}]\n{document}"
            )

            try:
                page = int(page)
            except (TypeError, ValueError):
                pass

            source_pages.append(page)

        else:
            context_parts.append(str(document))

    return {
        "context": "\n\n".join(context_parts),
        "source_pages": list(dict.fromkeys(source_pages)),
    }


# Make the compatibility function available inside
# the rag_search module before generation.py imports it.
rag_search.retrieve_for_question = retrieve_for_question


# IMPORTANT:
# generation.py must be imported AFTER the bridge above.
import generation
import quality_score
import grounding_validation
import ai_critic


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="GenAI Hackathon — Exam AI API",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request Models
# ============================================================

class TopicIn(BaseModel):
    topic: str
    learning_objectives: List[str] = Field(default_factory=list)


class ExamSettingsIn(BaseModel):
    num_questions: int
    question_types: List[str]
    difficulty_levels: List[str]
    topics: List[TopicIn]


class QuestionIn(BaseModel):
    question_type: str
    topic: Optional[str] = None
    learning_objective: Optional[str] = None
    difficulty: Optional[str] = None
    question: Optional[str] = None
    correct_answer: Optional[str] = None
    choices: Optional[List[str]] = None
    source_page: Optional[int] = None
    source_pages: Optional[List[int]] = None


class QuestionsIn(BaseModel):
    questions: List[dict]


class RegenerateIn(BaseModel):
    question: dict
    quality_result: dict
    topic: str
    learning_objective: Optional[str] = None
    difficulty: str
    question_type: str


class GenerateExamIn(BaseModel):
    settings: Optional[ExamSettingsIn] = None


# ============================================================
# Response Helpers
# ============================================================

def ok(data):
    return {
        "success": True,
        "data": data
    }


def fail(message: str):
    return {
        "success": False,
        "error": message
    }


# ============================================================
# Global Exception Handler
# ============================================================

@app.exception_handler(Exception)
async def all_exceptions(request, exc):
    traceback.print_exc()

    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content=fail(str(exc))
    )


# ============================================================
# Health Check
# ============================================================

@app.get("/api/health")
def health():
    return ok({
        "status": "up",
        "groq_key_set": bool(
            os.environ.get("GROQ_API_KEY")
        ),
    })


# ============================================================
# Exam Settings
# ============================================================

@app.post("/api/exam-settings")
def create_exam_settings(
    payload: ExamSettingsIn
):
    settings = exam_settings.build_exam_settings(
        num_questions=payload.num_questions,
        question_types=payload.question_types,
        difficulty_levels=payload.difficulty_levels,
        topics=[
            topic.model_dump()
            for topic in payload.topics
        ],
    )

    exam_settings.save_exam_settings(settings)

    return ok(settings)


# ============================================================
# Generate Exam
# ============================================================

@app.post("/api/generate-exam")
def generate_exam_endpoint(
    payload: Optional[GenerateExamIn] = None
):
    # --------------------------------------------------------
    # 1. Build and save exam settings if provided
    # --------------------------------------------------------

    if payload and payload.settings is not None:

        settings = exam_settings.build_exam_settings(
            num_questions=payload.settings.num_questions,
            question_types=payload.settings.question_types,
            difficulty_levels=payload.settings.difficulty_levels,
            topics=[
                topic.model_dump()
                for topic in payload.settings.topics
            ],
        )

        exam_settings.save_exam_settings(settings)

    # --------------------------------------------------------
    # 2. Build exam blueprint
    # --------------------------------------------------------

    blueprint = exam_blueprint.build_blueprint_from_file()

    # --------------------------------------------------------
    # 3. Build generation requests
    # --------------------------------------------------------

    requests = exam_blueprint.build_generation_requests(
        blueprint
    )

    # --------------------------------------------------------
    # 4. Generate exam using existing AI pipeline
    # --------------------------------------------------------

    exam = generation.generate_exam(
        requests
    )

    # --------------------------------------------------------
    # 5. Save generated exam
    # --------------------------------------------------------

    generation.save_exam(
        exam
    )

    # --------------------------------------------------------
    # 6. Return frontend-friendly response
    # --------------------------------------------------------

    return ok({
        "blueprint": blueprint,
        "requested_count": len(requests),
        "generated_count": len(exam),
        "exam": exam,
    })


# ============================================================
# Quality Score
# ============================================================

@app.post("/api/quality-score")
def quality_score_endpoint(
    payload: Optional[QuestionsIn] = None
):
    if payload:
        questions = payload.questions
    else:
        questions = quality_score.load_questions()

    results = quality_score.evaluate_exam(
        questions
    )

    quality_score.save_results(
        results
    )

    return ok(results)


# ============================================================
# Duplicate Detection
# ============================================================

@app.post("/api/duplicates")
def duplicates_endpoint(
    payload: QuestionsIn
):
    duplicates = quality_score.detect_duplicates(
        payload.questions
    )

    return ok({
        "duplicates": duplicates
    })


# ============================================================
# Grounding Validation
# ============================================================

@app.post("/api/validate")
def validate_endpoint(
    payload: Optional[QuestionsIn] = None
):
    if payload:
        questions = payload.questions
    else:
        questions = grounding_validation.load_questions()

    # Load source pages from the existing PDF pipeline
    pages_by_number = (
        grounding_validation.load_source_pages()
    )

    # Validate questions against source material
    results = grounding_validation.validate_exam(
        questions,
        pages_by_number
    )

    # Save validation results
    grounding_validation.save_results(
        results
    )

    return ok(results)


# ============================================================
# Regeneration
# ============================================================

@app.post("/api/regenerate")
def regenerate_endpoint(
    payload: RegenerateIn
):
    result = ai_critic.smart_regenerate(
        question=payload.question,
        quality_result=payload.quality_result,
        topic=payload.topic,
        learning_objective=payload.learning_objective,
        difficulty=payload.difficulty,
        question_type=payload.question_type,
    )

    return ok(result)


# ============================================================
# Run Directly
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )