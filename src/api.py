import os
import shutil
import traceback
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

import exam_settings
import exam_blueprint
import rag_search
import pdf_processor
import rag_indexer


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

UPLOAD_DIR = os.path.join(
    DATA_DIR,
    "uploads"
)

EXTRACTED_JSON_PATH = os.path.join(
    OUTPUT_DIR,
    "extracted_text.json"
)

EXAM_SETTINGS_PATH = os.path.join(
    OUTPUT_DIR,
    "exam_settings.json"
)

GENERATED_EXAM_PATH = os.path.join(
    OUTPUT_DIR,
    "generated_exam.json"
)

QUALITY_RESULTS_PATH = os.path.join(
    OUTPUT_DIR,
    "quality_score_results.json"
)

GROUNDING_RESULTS_PATH = os.path.join(
    OUTPUT_DIR,
    "grounding_results.json"
)


# ============================================================
# QUESTION TYPE NORMALIZATION
# ============================================================
# The exam settings UI uses "True/False".
# The generation pipeline expects "True-False".
# ============================================================

TRUE_FALSE_ALIASES = (
    "true/false",
    "true false",
    "true_false",
    "true-false",
    "t/f",
    "tf",
)


def to_generation_type(question_type):

    if str(question_type).strip().lower() in TRUE_FALSE_ALIASES:
        return "True-False"

    return question_type


os.makedirs(
    DATA_DIR,
    exist_ok=True
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ============================================================
# Compatibility Bridge
# ============================================================
# generation.py expects:
#
#     retrieve_for_question()
#
# rag_search.py provides:
#
#     search_question()
#
# So we create the expected function here.
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

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    context_parts = []
    source_pages = []

    for document, metadata in zip(
        documents,
        metadatas
    ):

        metadata = metadata or {}

        page = metadata.get("page")

        if page is not None:

            context_parts.append(
                f"[Page {page}]\n{document}"
            )

            try:
                page = int(page)
            except (
                TypeError,
                ValueError
            ):
                pass

            source_pages.append(page)

        else:

            context_parts.append(
                str(document)
            )

    return {
        "context": "\n\n".join(
            context_parts
        ),
        "source_pages": list(
            dict.fromkeys(
                source_pages
            )
        ),
    }


# Make compatibility function available
# inside rag_search before generation imports.
rag_search.retrieve_for_question = (
    retrieve_for_question
)


# IMPORTANT:
# generation.py must be imported AFTER
# the bridge above.

import generation
import quality_score
import grounding_validation
import ai_critic


# ============================================================
# FASTAPI APP
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
# REQUEST MODELS
# ============================================================

class TopicIn(BaseModel):

    topic: str

    learning_objectives: List[str] = Field(
        default_factory=list
    )


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
# RESPONSE HELPERS
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
# GLOBAL EXCEPTION HANDLER
# ============================================================

@app.exception_handler(Exception)
async def all_exceptions(
    request,
    exc
):

    traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content=fail(
            str(exc)
        )
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return ok(
        {
            "status": "up",

            "groq_key_set": bool(
                os.environ.get(
                    "GROQ_API_KEY"
                )
            ),
        }
    )


# ============================================================
# UPLOAD PDF
# ============================================================

@app.post("/api/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...)
):

    try:

        # ----------------------------------------------------
        # 1. Validate uploaded file
        # ----------------------------------------------------

        if not file.filename:

            return fail(
                "No file was selected."
            )

        filename = os.path.basename(
            file.filename
        )

        if not filename.lower().endswith(
            ".pdf"
        ):

            return fail(
                "Please upload a PDF file."
            )

        # ----------------------------------------------------
        # 2. Save uploaded PDF
        # ----------------------------------------------------

        pdf_path = os.path.join(
            UPLOAD_DIR,
            filename
        )

        with open(
            pdf_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        # ----------------------------------------------------
        # 3. Extract PDF text
        # ----------------------------------------------------

        print(
            f"Processing uploaded PDF: {filename}"
        )

        pages = pdf_processor.extract_pdf_text(
            pdf_path
        )

        if not pages:

            return fail(
                "The PDF does not contain readable text."
            )

        # ----------------------------------------------------
        # 4. Save extracted text
        # ----------------------------------------------------

        pdf_processor.save_extracted_text(
            pages,
            EXTRACTED_JSON_PATH
        )

        # ----------------------------------------------------
        # 5. Create chunks
        # ----------------------------------------------------

        chunks = rag_indexer.create_chunks(
            pages
        )

        if not chunks:

            return fail(
                "Could not create text chunks from the PDF."
            )

        # ----------------------------------------------------
        # 6. Create embeddings
        # ----------------------------------------------------
        # clear_existing=True means:
        #
        # The previous PDF is removed from Chroma
        # and the newly uploaded PDF becomes the
        # current knowledge source.
        # ----------------------------------------------------

        stored_chunks = rag_indexer.store_chunks(
            chunks,
            clear_existing=True
        )

        # ----------------------------------------------------
        # 7. Return upload information
        # ----------------------------------------------------

        print(
            f"PDF indexed successfully: {filename}"
        )

        print(
            f"Pages: {len(pages)}"
        )

        print(
            f"Chunks: {stored_chunks}"
        )

        return ok(
            {
                "filename": filename,

                "pages": len(pages),

                "chunks": stored_chunks,

                "message": (
                    "PDF uploaded and indexed successfully."
                ),
            }
        )

    except Exception as e:

        traceback.print_exc()

        return fail(
            f"PDF processing failed: {str(e)}"
        )


# ============================================================
# EXAM SETTINGS
# ============================================================

@app.post("/api/exam-settings")
def create_exam_settings(
    payload: ExamSettingsIn
):

    settings = (
        exam_settings.build_exam_settings(
            num_questions=payload.num_questions,

            question_types=(
                payload.question_types
            ),

            difficulty_levels=(
                payload.difficulty_levels
            ),

            topics=[
                topic.model_dump()
                for topic in payload.topics
            ],
        )
    )

    exam_settings.save_exam_settings(
        settings,
        EXAM_SETTINGS_PATH
    )

    return ok(
        settings
    )


# ============================================================
# GENERATE EXAM
# ============================================================

@app.post("/api/generate-exam")
def generate_exam_endpoint(
    payload: Optional[GenerateExamIn] = None
):

    # --------------------------------------------------------
    # 1. Build and save exam settings
    # --------------------------------------------------------

    if (
        payload
        and payload.settings is not None
    ):

        settings = (
            exam_settings.build_exam_settings(
                num_questions=(
                    payload.settings.num_questions
                ),

                question_types=(
                    payload.settings.question_types
                ),

                difficulty_levels=(
                    payload.settings.difficulty_levels
                ),

                topics=[
                    topic.model_dump()
                    for topic
                    in payload.settings.topics
                ],
            )
        )

        exam_settings.save_exam_settings(
            settings,
            EXAM_SETTINGS_PATH
        )

    # --------------------------------------------------------
    # 2. Build exam blueprint
    # --------------------------------------------------------

    blueprint = (
        exam_blueprint.build_blueprint_from_file()
    )

    # --------------------------------------------------------
    # 3. Build generation requests
    # --------------------------------------------------------

    requests = (
        exam_blueprint.build_generation_requests(
            blueprint
        )
    )

    for request in requests:

        request["question_type"] = to_generation_type(
            request["question_type"]
        )

    # --------------------------------------------------------
    # 4. Generate exam
    # --------------------------------------------------------

    exam = generation.generate_exam(
        requests
    )

    # --------------------------------------------------------
    # 5. Save generated exam
    # --------------------------------------------------------

    generation.save_exam(
        exam,
        GENERATED_EXAM_PATH
    )

    # --------------------------------------------------------
    # 6. Return frontend-friendly response
    # --------------------------------------------------------

    return ok(
        {
            "blueprint": blueprint,

            "requested_count": len(
                requests
            ),

            "generated_count": len(
                exam
            ),

            "exam": exam,
        }
    )


# ============================================================
# QUALITY SCORE
# ============================================================

@app.post("/api/quality-score")
def quality_score_endpoint(
    payload: Optional[QuestionsIn] = None
):

    if payload:

        questions = payload.questions

    else:

        questions = (
            quality_score.load_questions(
                GENERATED_EXAM_PATH
            )
        )

    results = (
        quality_score.evaluate_exam(
            questions
        )
    )

    quality_score.save_results(
        results,
        QUALITY_RESULTS_PATH
    )

    return ok(
        results
    )


# ============================================================
# DUPLICATE DETECTION
# ============================================================

@app.post("/api/duplicates")
def duplicates_endpoint(
    payload: QuestionsIn
):

    duplicates = (
        quality_score.detect_duplicates(
            payload.questions
        )
    )

    return ok(
        {
            "duplicates": duplicates
        }
    )


# ============================================================
# GROUNDING VALIDATION
# ============================================================

@app.post("/api/validate")
def validate_endpoint(
    payload: Optional[QuestionsIn] = None
):

    if payload:

        questions = payload.questions

    else:

        questions = (
            grounding_validation.load_questions(
                GENERATED_EXAM_PATH
            )
        )

    # --------------------------------------------------------
    # Load source pages from CURRENT uploaded PDF
    # --------------------------------------------------------

    pages_by_number = (
        grounding_validation.load_source_pages(
            EXTRACTED_JSON_PATH
        )
    )

    # --------------------------------------------------------
    # Validate questions against source
    # --------------------------------------------------------

    results = (
        grounding_validation.validate_exam(
            questions,
            pages_by_number
        )
    )

    # --------------------------------------------------------
    # Save validation results
    # --------------------------------------------------------

    grounding_validation.save_results(
        results,
        GROUNDING_RESULTS_PATH
    )

    return ok(
        results
    )


# ============================================================
# REGENERATION
# ============================================================

@app.post("/api/regenerate")
def regenerate_endpoint(
    payload: RegenerateIn
):

    result = (
        ai_critic.smart_regenerate(
            question=payload.question,

            quality_result=(
                payload.quality_result
            ),

            topic=payload.topic,

            learning_objective=(
                payload.learning_objective
            ),

            difficulty=payload.difficulty,

            question_type=(
                payload.question_type
            ),
        )
    )

    return ok(
        result
    )


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )