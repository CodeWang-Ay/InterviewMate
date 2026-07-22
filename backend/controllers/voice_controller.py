import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import VOICE_DIR
from backend.controllers.auth_controller import get_current_identity
from backend.services.voice_service import synthesize_speech_base64, transcribe_audio_file

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
