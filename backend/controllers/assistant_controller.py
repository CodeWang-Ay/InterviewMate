from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.controllers.auth_controller import get_current_identity
from backend.models.schemas import AssistantChatBody
from backend.services.assistant_service import generate_assistant_reply, stream_assistant_reply

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat")
async def assistant_chat(body: AssistantChatBody, identity: dict = Depends(get_current_identity)):
    message = body.message.strip()
    if not message:
        return {"message": "你发个一句话给我，我就接着聊。"}
    reply = await generate_assistant_reply(
        identity=identity,
        message=message,
        history=[item.model_dump() for item in body.history],
    )
    return {"message": reply}


@router.post("/chat/stream")
async def assistant_chat_stream(body: AssistantChatBody, identity: dict = Depends(get_current_identity)):
    message = body.message.strip()
    if not message:
        return StreamingResponse(iter(["你发个一句话给我，我就接着聊。"]), media_type="text/plain; charset=utf-8")

    async def event_stream():
        async for chunk in stream_assistant_reply(
            identity=identity,
            message=message,
            history=[item.model_dump() for item in body.history],
        ):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8")
