import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.config import chat_sessions
from backend.controllers.auth_controller import get_current_identity
from backend.models.schemas import ChatStart, ChatMessage
from backend.repositories import plan_repo
from backend.repositories.interview_repo import load_record_if_exists
from backend.services.chat_service import start_session, process_message
from backend.repositories.interview_repo import save_record
from backend.services.report_service import generate_report

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/start")
async def chat_start(body: ChatStart, identity: dict = Depends(get_current_identity)):
    if body.plan_id:
        plan = plan_repo.get_by_id(body.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="面试计划不存在")
        if identity["kind"] != "admin" and plan.get("candidate_username") != identity["username"]:
            raise HTTPException(status_code=403, detail="无权访问该面试计划")
    elif identity["kind"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可发起自由面试")

    session_id, message, state, history = await start_session(body.jd_filename, body.resume_filename, body.plan_id)
    save_record(session_id)
    return {"session_id": session_id, "message": message, "state": state, "history": history}


@router.post("/message")
async def chat_message(body: ChatMessage, identity: dict = Depends(get_current_identity)):
    _ensure_session_access(body.session_id, identity)
    reply, state = await process_message(body.session_id, body.message.strip())
    save_record(body.session_id)

    if state == "COMPLETED":
        generate_report(body.session_id)

    return {"message": reply, "state": state}


@router.post("/message/stream")
async def chat_message_stream(body: ChatMessage, identity: dict = Depends(get_current_identity)):
    _ensure_session_access(body.session_id, identity)
    reply, state = await process_message(body.session_id, body.message.strip())
    save_record(body.session_id)

    if state == "COMPLETED":
        generate_report(body.session_id)

    async def reply_stream():
        text = reply or ""
        chunk_size = 4
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]
            await asyncio.sleep(0.018)

    return StreamingResponse(
        reply_stream(),
        media_type="text/plain; charset=utf-8",
        headers={"X-Chat-State": state},
    )


def _ensure_session_access(session_id: str, identity: dict) -> None:
    if identity["kind"] == "admin":
        return

    session = chat_sessions.get(session_id) or load_record_if_exists(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    plan_id = session.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    plan = plan_repo.get_by_id(int(plan_id))
    if not plan or plan.get("candidate_username") != identity["username"]:
        raise HTTPException(status_code=403, detail="无权访问该会话")
