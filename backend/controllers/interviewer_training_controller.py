from fastapi import APIRouter, Depends, HTTPException

from backend.controllers.auth_controller import require_admin
from backend.models.schemas import InterviewerTrainingMessage, InterviewerTrainingStart
from backend.repositories import jd_repo, resume_repo
from backend.repositories.interview_repo import save_record
from backend.services.interviewer_training_service import (
    finish_training_session,
    get_training_session,
    process_training_message,
    start_training_session,
)
from backend.services.report_service import generate_report

router = APIRouter(prefix="/api/interviewer-training", tags=["interviewer-training"])


@router.get("/resources")
async def training_resources(_: dict = Depends(require_admin)):
    jds, _ = jd_repo.list_all_paged(page=1, page_size=999)
    resumes = resume_repo.list_all()
    return {"jds": jds, "resumes": resumes}


@router.post("/start")
async def training_start(body: InterviewerTrainingStart, _: dict = Depends(require_admin)):
    try:
        result = start_training_session(body.jd_id, body.resume_id, body.training_mode, body.candidate_style)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_record(result["session_id"])
    return result


@router.get("/session/{session_id}")
async def training_session(session_id: str, _: dict = Depends(require_admin)):
    session = get_training_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="训练会话不存在")
    return session


@router.post("/message")
async def training_message(body: InterviewerTrainingMessage, _: dict = Depends(require_admin)):
    try:
        reply, state = await process_training_message(body.session_id, body.message.strip())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    save_record(body.session_id)
    return {"message": reply, "state": state}


@router.post("/finish/{session_id}")
async def training_finish(session_id: str, _: dict = Depends(require_admin)):
    session = finish_training_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="训练会话不存在")
    save_record(session_id)
    report = generate_report(session_id)
    return {"status": "ok", "report": report}
