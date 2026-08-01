from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.controllers.auth_controller import get_current_identity
from backend.models.schemas import AssistantChatBody, AssistantConversationCreate, AssistantFeedbackBody
from backend.repositories import assistant_conversation_repo
from backend.services.assistant_service import generate_assistant_reply, stream_assistant_reply

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _conversation(body: AssistantChatBody, identity: dict) -> dict:
    conversation = None
    if body.conversation_id:
        conversation = assistant_conversation_repo.owned_conversation(body.conversation_id, identity["kind"], identity["username"])
    if not conversation:
        conversation = assistant_conversation_repo.create_conversation(identity["kind"], identity["username"], body.message[:30] or "新对话")
    return conversation


@router.get("/conversations")
async def conversations(identity: dict = Depends(get_current_identity)):
    return assistant_conversation_repo.list_conversations(identity["kind"], identity["username"])


@router.post("/conversations")
async def create_conversation(body: AssistantConversationCreate, identity: dict = Depends(get_current_identity)):
    return assistant_conversation_repo.create_conversation(identity["kind"], identity["username"], body.title)


@router.get("/conversations/{conversation_id}/messages")
async def conversation_messages(conversation_id: int, identity: dict = Depends(get_current_identity)):
    messages = assistant_conversation_repo.list_messages(conversation_id, identity["kind"], identity["username"])
    if messages is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")
    return messages


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, identity: dict = Depends(get_current_identity)):
    if not assistant_conversation_repo.delete_conversation(conversation_id, identity["kind"], identity["username"]):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"status": "ok"}


@router.post("/messages/{message_id}/feedback")
async def message_feedback(message_id: int, body: AssistantFeedbackBody, identity: dict = Depends(get_current_identity)):
    feedback = body.feedback if body.feedback in {"like", "dislike", ""} else ""
    if not assistant_conversation_repo.set_feedback(message_id, body.conversation_id, identity["kind"], identity["username"], feedback):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="消息不存在")
    return {"status": "ok", "feedback": feedback}


@router.post("/chat")
async def assistant_chat(body: AssistantChatBody, identity: dict = Depends(get_current_identity)):
    message = body.message.strip()
    if not message:
        return {"message": "你发个一句话给我，我就接着聊。"}
    conversation = _conversation(body, identity)
    assistant_conversation_repo.add_message(conversation["id"], "user", message)
    reply = await generate_assistant_reply(
        identity=identity,
        message=message,
        history=[item.model_dump() for item in body.history],
    )
    saved = assistant_conversation_repo.add_message(conversation["id"], "assistant", reply)
    return {"message": reply, "conversation_id": conversation["id"], "message_id": saved["id"]}


@router.post("/chat/stream")
async def assistant_chat_stream(body: AssistantChatBody, identity: dict = Depends(get_current_identity)):
    message = body.message.strip()
    if not message:
        return StreamingResponse(iter(["你发个一句话给我，我就接着聊。"]), media_type="text/plain; charset=utf-8")

    conversation = _conversation(body, identity)
    assistant_conversation_repo.add_message(conversation["id"], "user", message)
    saved = assistant_conversation_repo.add_message(conversation["id"], "assistant", "")

    async def event_stream():
        full_text = ""
        async for chunk in stream_assistant_reply(
            identity=identity,
            message=message,
            history=[item.model_dump() for item in body.history],
        ):
            full_text += chunk
            yield chunk
        assistant_conversation_repo.update_message(saved["id"], full_text)

    return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8", headers={
        "X-Conversation-Id": str(conversation["id"]),
        "X-Assistant-Message-Id": str(saved["id"]),
    })
