import os
import uuid
import base64
import json

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.config import VOICE_DIR
from backend.controllers.auth_controller import get_current_identity
from backend.repositories import admin_repo, candidate_repo
from backend.services.voice_service import (
    end_two_pass_session,
    process_two_pass_chunk,
    start_two_pass_session,
    synthesize_speech_base64,
    transcribe_audio_file,
)

router = APIRouter(prefix="/api/voice", tags=["voice"])

os.makedirs(VOICE_DIR, exist_ok=True)


class TTSBody(BaseModel):
    text: str
    voice: str = ""


@router.post("/asr")
async def voice_asr(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_identity),
):
    suffix = os.path.splitext(file.filename or "audio.wav")[1].lower() or ".wav"
    if suffix not in {".wav", ".mp3", ".m4a", ".webm", ".ogg"}:
        raise HTTPException(status_code=400, detail="仅支持 wav/mp3/m4a/webm/ogg 音频")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="音频内容为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="音频文件不能超过 20MB")

    filename = f"voice_{uuid.uuid4().hex[:12]}{suffix}"
    path = os.path.join(VOICE_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)

    try:
        text = await transcribe_audio_file(path)
        return {"status": "ok", "text": text, "filename": filename}
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@router.post("/tts")
async def voice_tts(body: TTSBody, _: dict = Depends(get_current_identity)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="朗读文本不能为空")
    try:
        audio = await synthesize_speech_base64(body.text, body.voice or None)
        return {"status": "ok", "audio": audio, "format": "audio/mpeg"}
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _is_valid_ws_token(token: str) -> bool:
    token = (token or "").strip()
    return bool(token and (admin_repo.get_admin_by_token(token) or candidate_repo.get_candidate_by_token(token)))


@router.websocket("/asr-stream")
async def voice_asr_stream(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    if not _is_valid_ws_token(token):
        await websocket.close(code=1008, reason="未登录")
        return

    await websocket.accept()
    session = None
    session_id = uuid.uuid4().hex

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "asr_error", "message": "消息格式错误"})
                continue

            msg_type = data.get("type")
            if msg_type == "audio_stream_start":
                session = await start_two_pass_session(session_id)
                await websocket.send_json({"type": "audio_stream_start_reply", "success": True, "session_id": session_id})

            elif msg_type == "audio_stream_chunk":
                if session is None:
                    await websocket.send_json({"type": "asr_error", "message": "流式识别会话未启动"})
                    continue
                chunk_b64 = data.get("data") or ""
                if not chunk_b64:
                    continue
                try:
                    audio = np.frombuffer(base64.b64decode(chunk_b64), dtype=np.float32)
                    text, is_sentence_end = await process_two_pass_chunk(session, audio)
                    if text:
                        await websocket.send_json({
                            "type": "asr_final" if is_sentence_end else "asr_partial",
                            "text": text,
                            "is_sentence_end": is_sentence_end,
                        })
                except Exception as exc:
                    await websocket.send_json({"type": "asr_error", "message": f"流式识别失败: {exc}"})

            elif msg_type == "audio_stream_end":
                if session is None:
                    await websocket.send_json({"type": "asr_error", "message": "流式识别会话未启动"})
                    continue
                final_text = await end_two_pass_session(session)
                await websocket.send_json({"type": "asr_final", "text": final_text, "is_sentence_end": True, "pass": 2})
                session = None

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        return
    except RuntimeError as exc:
        await websocket.send_json({"type": "asr_error", "message": str(exc)})
    except Exception as exc:
        await websocket.send_json({"type": "asr_error", "message": f"语音流连接异常: {exc}"})
