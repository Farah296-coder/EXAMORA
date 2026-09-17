from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import database

router = APIRouter(prefix="/api", tags=["exams"])


class QuestionIn(BaseModel):
    question_type: str = "MCQ"
    question: str = ""
    correct_answer: Optional[str] = None
    choices: Optional[List[str]] = None
    topic: Optional[str] = None
    learning_objective: Optional[str] = None
    difficulty: Optional[str] = None
    source_pages: Optional[List[int]] = None
    source_page: Optional[int] = None
    points: float = 1
    quality_score: Optional[int] = None
    grounding_verdict: Optional[str] = None


class ExamIn(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    pass_percentage: float = 50
    source_id: Optional[int] = None
    average_quality: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None
    blueprint: Optional[Dict[str, Any]] = None
    questions: List[QuestionIn] = Field(default_factory=list)


class ExamUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    pass_percentage: Optional[float] = None
    source_id: Optional[int] = None


class QuestionsIn(BaseModel):
    questions: List[QuestionIn]


class ImportApprovedIn(BaseModel):
    title: Optional[str] = None
    path: str = "output/approved_exam.json"
    source_id: Optional[int] = None


class PublishIn(BaseModel):
    duration_minutes: Optional[int] = None


class SourceIn(BaseModel):
    filename: str
    path: Optional[str] = None
    total_pages: Optional[int] = None
    extracted_text_path: Optional[str] = None


class AnswerIn(BaseModel):
    question_id: Optional[int] = None
    position: Optional[int] = None
    answer_text: Optional[str] = None


class SubmissionIn(BaseModel):
    student_name: str
    student_email: Optional[str] = None
    started_at: Optional[str] = None
    answers: List[AnswerIn] = Field(default_factory=list)


class GradeIn(BaseModel):
    is_correct: bool
    points: Optional[float] = None
    feedback: Optional[str] = None


def ok(data):
    return {"success": True, "data": data}


def with_share_link(exam):
    exam["share_url"] = database.share_link(exam)
    return exam


def handle(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except database.ExamNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except database.SubmissionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except database.ExamNotAvailable as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/db/health")
def db_health():
    exams = database.list_exams()
    return ok({
        "status": "up",
        "database": database.DB_PATH,
        "exams": len(exams),
        "published": sum(1 for exam in exams if exam["status"] == "published"),
    })


@router.post("/sources", status_code=201)
def create_source(payload: SourceIn):
    source_id = database.save_source(
        filename=payload.filename,
        path=payload.path,
        total_pages=payload.total_pages,
        extracted_text_path=payload.extracted_text_path,
    )
    return ok(database.get_source(source_id))


@router.get("/sources")
def get_sources():
    return ok(database.list_sources())


@router.post("/exams", status_code=201)
def create_exam(payload: ExamIn):
    exam = handle(
        database.create_exam,
        title=payload.title,
        questions=[question.model_dump() for question in payload.questions],
        settings=payload.settings,
        blueprint=payload.blueprint,
        source_id=payload.source_id,
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        pass_percentage=payload.pass_percentage,
        average_quality=payload.average_quality,
    )
    return ok(with_share_link(exam))


@router.post("/exams/import-approved", status_code=201)
def import_approved(payload: Optional[ImportApprovedIn] = None):
    payload = payload or ImportApprovedIn()
    exam = handle(
        database.import_approved_exam,
        path=payload.path,
        title=payload.title,
        source_id=payload.source_id,
    )
    return ok(with_share_link(exam))


@router.get("/exams")
def get_exams(status: Optional[str] = None):
    exams = [with_share_link(exam) for exam in database.list_exams(status)]
    return ok(exams)


@router.get("/exams/{exam_id}")
def get_exam(exam_id: int):
    exam = handle(database.get_exam, exam_id, include_answers=True)
    return ok(with_share_link(exam))


@router.put("/exams/{exam_id}")
def update_exam(exam_id: int, payload: ExamUpdateIn):
    fields = {key: value for key, value in payload.model_dump().items() if value is not None}
    exam = handle(database.update_exam, exam_id, **fields)
    return ok(with_share_link(exam))


@router.put("/exams/{exam_id}/questions")
def replace_questions(exam_id: int, payload: QuestionsIn):
    exam = handle(
        database.replace_questions,
        exam_id,
        [question.model_dump() for question in payload.questions],
    )
    return ok(with_share_link(exam))


@router.delete("/exams/{exam_id}")
def delete_exam(exam_id: int):
    handle(database.delete_exam, exam_id)
    return ok({"deleted": exam_id})


@router.post("/exams/{exam_id}/publish")
def publish_exam(exam_id: int, payload: Optional[PublishIn] = None):
    exam = handle(
        database.publish_exam,
        exam_id,
        payload.duration_minutes if payload else None,
    )
    return ok(with_share_link(exam))


@router.post("/exams/{exam_id}/unpublish")
def unpublish_exam(exam_id: int):
    return ok(with_share_link(handle(database.unpublish_exam, exam_id)))


@router.post("/exams/{exam_id}/close")
def close_exam(exam_id: int):
    return ok(with_share_link(handle(database.close_exam, exam_id)))


@router.get("/exams/{exam_id}/export")
def export_exam(exam_id: int):
    return ok(handle(database.export_exam, exam_id))


@router.get("/exams/{exam_id}/submissions")
def get_submissions(exam_id: int):
    return ok(handle(database.list_submissions, exam_id))


@router.get("/exams/{exam_id}/results")
def get_results(exam_id: int):
    return ok(handle(database.exam_results, exam_id))


@router.get("/public/exams/{token}")
def get_shared_exam(token: str):
    exam = handle(database.get_exam_by_token, token, include_answers=False)
    return ok(exam)


@router.post("/public/exams/{token}/submissions", status_code=201)
def submit_shared_exam(token: str, payload: SubmissionIn):
    submission = handle(
        database.save_submission,
        token=token,
        student_name=payload.student_name,
        student_email=payload.student_email,
        answers=[answer.model_dump() for answer in payload.answers],
        started_at=payload.started_at,
    )
    return ok({
        "id": submission["id"],
        "student_name": submission["student_name"],
        "score": submission["score"],
        "max_score": submission["max_score"],
        "percentage": submission["percentage"],
        "status": submission["status"],
        "passed": submission.get("passed"),
        "pending_review": submission["pending_review"],
    })


@router.get("/submissions/{submission_id}")
def get_submission(submission_id: int):
    return ok(handle(database.get_submission, submission_id))


@router.post("/answers/{answer_id}/grade")
def grade_answer(answer_id: int, payload: GradeIn):
    submission = handle(
        database.grade_answer,
        answer_id,
        is_correct=payload.is_correct,
        points=payload.points,
        feedback=payload.feedback,
    )
    return ok(submission)


app = FastAPI(title="GenAI Hackathon - Exam Backend & Database", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("exam_api:app", host="0.0.0.0", port=8001, reload=True)
