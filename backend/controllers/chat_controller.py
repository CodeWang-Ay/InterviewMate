from fastapi import APIRouter

from backend.models.schemas import ChatStart, ChatMessage
from backend.services.chat_service import start_session, process_message
from backend.repositories.interview_repo import save_record
from backend.services.report_service import generate_report

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/start")
async def chat_start(body: ChatStart):
    session_id, message, state = start_session(body.jd_filename, body.resume_filename, body.plan_id)
    return {"session_id": session_id, "message": message, "state": state}


@router.post("/message")
async def chat_message(body: ChatMessage):
    reply, state = process_message(body.session_id, body.message.strip())

    if state == "COMPLETED":
        save_record(body.session_id)
        generate_report(body.session_id)

    return {"message": reply, "state": state}
