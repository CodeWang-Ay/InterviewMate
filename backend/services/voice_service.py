import asyncio
import base64
import os
import time
from dataclasses import dataclass, field

from dotenv import load_dotenv
from loguru import logger

load_dotenv(".env")

_asr_model = None
_asr_lock = asyncio.Lock()
_streaming_asr_model = None
_streaming_vad_model = None
_streaming_lock = asyncio.Lock()

SAMPLE_RATE = 16000
VAD_CHUNK_MS = 200
ASR_CHUNK_SAMPLES = 9600
CHUNK_SIZE_CFG = [0, 10, 5]
ENCODER_LOOK_BACK = 4
DECODER_LOOK_BACK = 1


@dataclass
class StreamingSessionState:
    vad_cache: dict = field(default_factory=dict)
    is_speaking: bool = False
    asr_cache: dict = field(default_factory=dict)
    asr_pending: list = field(default_factory=list)
    sentence_text: str = ""
    accumulated_text: str = ""
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


@dataclass
class TwoPassASRSession:
    session_id: str
    stream_state: StreamingSessionState = field(default_factory=StreamingSessionState)
    audio_buffer: list = field(default_factory=list)


def _model_path(name: str, env_key: str) -> str:
    explicit = os.getenv(env_key, "").strip()
    if explicit:
        return explicit
    root = os.getenv("model_root_dir", "").strip() or os.getenv("FUNASR_MODEL_ROOT", "").strip()
    if root:
        return os.path.join(root, name)
    return name


async def preload_voice_models() -> None:
    logger.info("开始预加载语音模型：FunASR streaming + VAD + offline + punc")
    await _get_streaming_models()
    await _get_asr_model()
    logger.info("语音模型预加载完成")


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


async def start_two_pass_session(session_id: str) -> TwoPassASRSession:
    await _get_streaming_models()
    logger.info(f"[{session_id}] 2-pass ASR 会话已启动")
    return TwoPassASRSession(session_id=session_id)


async def process_two_pass_chunk(session: TwoPassASRSession, audio_chunk) -> tuple[str, bool]:
    import numpy as np

    if not isinstance(audio_chunk, np.ndarray):
        audio_chunk = np.array(audio_chunk, dtype=np.float32)
    session.audio_buffer.extend(audio_chunk.astype(np.float32).tolist())
    text, sentence_end = await _infer_streaming_chunk(audio_chunk, session.stream_state)
    return text, sentence_end


async def end_two_pass_session(session: TwoPassASRSession) -> str:
    import numpy as np

    stream_text = await _end_streaming_session(session)
    final_text = stream_text
    if session.audio_buffer:
        model = await _get_asr_model()
        audio = np.array(session.audio_buffer, dtype=np.float32)
        try:
            result = await asyncio.to_thread(
                model.generate,
                input=audio,
                hotword="",
                disable_pbar=True,
            )
            if result:
                first = result[0] if isinstance(result, list) else result
                if isinstance(first, dict):
                    final_text = str(first.get("text") or "").strip() or stream_text
                else:
                    final_text = str(first or "").strip() or stream_text
        except Exception as exc:
            logger.error(f"[{session.session_id}] 2-pass 离线精校失败: {exc}")
    logger.info(f"[{session.session_id}] 2-pass ASR 最终结果: {final_text}")
    return final_text


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
            disable_update=True,
        )
        logger.info("FunASR 模型加载完成")
        return _asr_model


async def _get_streaming_models():
    global _streaming_asr_model, _streaming_vad_model
    if _streaming_asr_model is not None and _streaming_vad_model is not None:
        return _streaming_asr_model, _streaming_vad_model
    async with _streaming_lock:
        if _streaming_asr_model is not None and _streaming_vad_model is not None:
            return _streaming_asr_model, _streaming_vad_model
        try:
            from funasr import AutoModel
        except ModuleNotFoundError as exc:
            raise RuntimeError("未安装 funasr，请先安装项目语音依赖") from exc

        model = _model_path("paraformer-zh-streaming", "FUNASR_STREAMING_MODEL")
        vad_model = _model_path("fsmn-vad", "FUNASR_VAD_MODEL")
        logger.info(f"正在加载 FunASR 流式模型: model={model}, vad={vad_model}")
        _streaming_asr_model = await asyncio.to_thread(
            AutoModel,
            model=model,
            model_revision="v2.0.4",
            disable_update=True,
        )
        _streaming_vad_model = await asyncio.to_thread(
            AutoModel,
            model=vad_model,
            model_revision="v2.0.4",
            disable_update=True,
        )
        logger.info("FunASR 流式模型加载完成")
        return _streaming_asr_model, _streaming_vad_model


async def _infer_streaming_chunk(audio_chunk, state: StreamingSessionState) -> tuple[str, bool]:
    asr_model, vad_model = await _get_streaming_models()
    state.last_seen = time.time()
    vad_speech_start = False
    vad_speech_end = False

    try:
        vad_result = await asyncio.to_thread(
            vad_model.generate,
            input=audio_chunk,
            cache=state.vad_cache,
            is_final=False,
            chunk_size=VAD_CHUNK_MS,
            disable_pbar=True,
        )
        if vad_result and vad_result[0].get("value"):
            for seg in vad_result[0]["value"]:
                if seg[0] >= 0:
                    vad_speech_start = True
                if seg[1] >= 0:
                    vad_speech_end = True
    except Exception as exc:
        logger.warning(f"FunASR VAD 异常: {exc}")

    if vad_speech_start and not state.is_speaking:
        state.is_speaking = True
        state.sentence_text = ""
        state.asr_cache = {}
        state.asr_pending = []

    if state.is_speaking:
        state.asr_pending.extend(audio_chunk.astype("float32").tolist())
        if vad_speech_end:
            sentence_text = await _flush_streaming_pending(asr_model, state, is_final=True)
            if sentence_text:
                state.accumulated_text += sentence_text
            state.is_speaking = False
            state.sentence_text = ""
            state.asr_cache = {}
            state.asr_pending = []
            return state.accumulated_text, True

        partial_text = await _flush_streaming_pending(asr_model, state, is_final=False)
        return state.accumulated_text + partial_text, False

    return state.accumulated_text, False


async def _flush_streaming_pending(asr_model, state: StreamingSessionState, is_final: bool) -> str:
    import numpy as np

    if is_final:
        if state.asr_pending:
            audio_chunk = np.array(state.asr_pending, dtype=np.float32)
            state.asr_pending = []
            piece = await _feed_streaming_asr(asr_model, audio_chunk, state.asr_cache, True)
        else:
            piece = await _feed_streaming_asr(asr_model, np.zeros(160, dtype=np.float32), state.asr_cache, True)
        if piece:
            state.sentence_text += piece
    else:
        while len(state.asr_pending) >= ASR_CHUNK_SAMPLES:
            audio_chunk = np.array(state.asr_pending[:ASR_CHUNK_SAMPLES], dtype=np.float32)
            state.asr_pending = state.asr_pending[ASR_CHUNK_SAMPLES:]
            piece = await _feed_streaming_asr(asr_model, audio_chunk, state.asr_cache, False)
            if piece:
                state.sentence_text += piece
    return state.sentence_text


async def _feed_streaming_asr(asr_model, chunk, asr_cache: dict, is_final: bool) -> str:
    try:
        result = await asyncio.to_thread(
            asr_model.generate,
            input=chunk,
            cache=asr_cache,
            is_final=is_final,
            chunk_size=CHUNK_SIZE_CFG,
            encoder_chunk_look_back=ENCODER_LOOK_BACK,
            decoder_chunk_look_back=DECODER_LOOK_BACK,
            disable_pbar=True,
        )
        if result:
            return str(result[0].get("text", "")).strip()
    except Exception as exc:
        logger.warning(f"FunASR 流式识别异常: {exc}")
    return ""


async def _end_streaming_session(session: TwoPassASRSession) -> str:
    asr_model, _ = await _get_streaming_models()
    state = session.stream_state
    if state.is_speaking or state.asr_pending:
        sentence_text = await _flush_streaming_pending(asr_model, state, is_final=True)
        if sentence_text:
            state.accumulated_text += sentence_text
    return state.accumulated_text


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
