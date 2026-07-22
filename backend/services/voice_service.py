import asyncio
import base64
import os

from dotenv import load_dotenv
from loguru import logger

load_dotenv(".env")

_asr_model = None
_asr_lock = asyncio.Lock()


def _model_path(name: str, env_key: str) -> str:
    explicit = os.getenv(env_key, "").strip()
    if explicit:
        return explicit
    root = os.getenv("model_root_dir", "").strip() or os.getenv("FUNASR_MODEL_ROOT", "").strip()
    if root:
        return os.path.join(root, name)
    return name


async def transcribe_audio_file(audio_path: str, hotword: str = "") -> str:
    model = await _get_asr_model()
    try:
        result = await asyncio.to_thread(
            model.generate,
            input=audio_path,
            hotword=hotword or "",
            disable_pbar=True,
        )
    except Exception as exc:
        logger.error(f"FunASR 识别失败: {exc}")
        raise RuntimeError(f"FunASR 识别失败: {exc}") from exc

    if not result:
        return ""
    first = result[0] if isinstance(result, list) else result
    if isinstance(first, dict):
        return str(first.get("text") or "").strip()
    return str(first or "").strip()


async def _get_asr_model():
    global _asr_model
    if _asr_model is not None:
        return _asr_model
    async with _asr_lock:
        if _asr_model is not None:
            return _asr_model
        try:
            from funasr import AutoModel
        except ModuleNotFoundError as exc:
            raise RuntimeError("未安装 funasr，请先安装项目语音依赖") from exc

        model = _model_path("paraformer-zh", "FUNASR_MODEL")
        vad_model = _model_path("fsmn-vad", "FUNASR_VAD_MODEL")
        punc_model = _model_path("punc_ct", "FUNASR_PUNC_MODEL")
        logger.info(f"正在加载 FunASR 模型: model={model}, vad={vad_model}, punc={punc_model}")
        _asr_model = await asyncio.to_thread(
            AutoModel,
            model=model,
            vad_model=vad_model,
            punc_model=punc_model,
            trust_remote_code=True,
        )
        logger.info("FunASR 模型加载完成")
        return _asr_model


def _voice_name(voice: str | None = None) -> str:
    return (voice or os.getenv("EDGE_TTS_VOICE") or "zh-CN-XiaoxiaoNeural").strip()


async def synthesize_speech_base64(text: str, voice: str | None = None) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    try:
        import edge_tts
    except ModuleNotFoundError as exc:
        raise RuntimeError("未安装 edge-tts，请先安装项目语音依赖") from exc

    communicate = edge_tts.Communicate(text, voice=_voice_name(voice))
    audio = b""
    try:
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                audio += chunk.get("data", b"")
    except Exception as exc:
        logger.error(f"Edge TTS 合成失败: {exc}")
        raise RuntimeError(f"Edge TTS 合成失败: {exc}") from exc
    return base64.b64encode(audio).decode("utf-8") if audio else ""
