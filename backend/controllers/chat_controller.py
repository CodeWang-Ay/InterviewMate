from fastapi import APIRouter

from backend.models.schemas import ChatStart, ChatMessage
from backend.services.chat_service import start_session, process_message
from backend.repositories.interview_repo import save_record
from backend.services.report_service import generate_report

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/start")
async def chat_start(body: ChatStart):
    session_id, message, state, history = start_session(body.jd_filename, body.resume_filename, body.plan_id)
    save_record(session_id)
    return {"session_id": session_id, "message": message, "state": state, "history": history}


@router.post("/message")
async def chat_message(body: ChatMessage):
    reply, state = process_message(body.session_id, body.message.strip())
    save_record(body.session_id)

    if state == "COMPLETED":
        generate_report(body.session_id)

    return {"message": reply, "state": state}
