import { ref } from 'vue'

const TARGET_SAMPLE_RATE = 16000
const STREAM_CHUNK_MS = 200

export function useVoice({ state, sending, input, onRecognized }) {
  const voiceMode = ref(false)
  const autoSpeak = ref(true)
  const isRecording = ref(false)
  const voiceText = ref('')
  const voiceError = ref('')
  const voiceBusy = ref(false)
  const mediaStream = ref(null)
  const audioContext = ref(null)
  const scriptProcessor = ref(null)
  const audioBuffers = ref([])
  const recordStartedAt = ref(0)
  const voiceSocket = ref(null)
  const voiceStreamReady = ref(false)
  const streamingAudioBuffer = ref([])
  const activeVoicePointerId = ref(null)
  const pendingVoiceRelease = ref(false)

  const voiceSupported = typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)

  function safeGetToken() {
    try { return window.localStorage?.getItem('token') || '' } catch (_) { return '' }
  }

  // ── audio helpers ──────────────────────────────────────────

  function resampleLinear(input, srcSr, dstSr) {
    if (srcSr === dstSr) return input
    const ratio = dstSr / srcSr
    const outLen = Math.max(0, Math.round(input.length * ratio))
    const out = new Float32Array(outLen)
    for (let i = 0; i < outLen; i += 1) {
      const x = i / ratio
      const x0 = Math.floor(x)
      const x1 = Math.min(x0 + 1, input.length - 1)
      const t = x - x0
      out[i] = input[x0] * (1 - t) + input[x1] * t
    }
    return out
  }

  function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    const chunkSize = 0x8000
    for (let i = 0; i < bytes.length; i += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize))
    }
    return window.btoa(binary)
  }

  // ── WebSocket streaming ASR ────────────────────────────────

  function openVoiceStream() {
    return new Promise((resolve, reject) => {
      const token = safeGetToken()
      if (!token) { reject(new Error('未登录，无法使用语音识别')); return }
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/api/voice/asr-stream?token=${encodeURIComponent(token)}`)
      voiceSocket.value = ws
      voiceStreamReady.value = false

      const timer = window.setTimeout(() => { reject(new Error('语音流连接超时')); closeVoiceStream() }, 8000)

      ws.onopen = () => ws.send(JSON.stringify({ type: 'audio_stream_start' }))
      ws.onerror = () => { window.clearTimeout(timer); reject(new Error('语音流连接失败')) }
      ws.onclose = () => {
        voiceStreamReady.value = false
        if (voiceBusy.value && isRecording.value) {
          voiceBusy.value = false
          voiceError.value = '语音流连接已断开，请重新按住说话。'
        }
      }
      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data || '{}')
        if (data.type === 'audio_stream_start_reply') { window.clearTimeout(timer); voiceStreamReady.value = true; resolve(); return }
        if (data.type === 'asr_partial' && data.text) { voiceText.value = data.text; if (input) input.value = data.text; return }
        if (data.type === 'asr_final') {
          const text = String(data.text || '').trim()
          if (text) {
            voiceText.value = text; if (input) input.value = text
            if (data.pass === 2) { voiceBusy.value = false; closeVoiceStream(); voiceText.value = ''; onRecognized(text) }
          } else { voiceError.value = 'FunASR 没有识别到有效文字'; voiceText.value = ''; voiceBusy.value = false; closeVoiceStream() }
          return
        }
        if (data.type === 'asr_error') { voiceError.value = data.message || '语音识别失败'; voiceBusy.value = false }
      }
    })
  }

  function closeVoiceStream() {
    const ws = voiceSocket.value
    voiceSocket.value = null
    voiceStreamReady.value = false
    if (ws && [WebSocket.CONNECTING, WebSocket.OPEN].includes(ws.readyState)) ws.close()
  }

  function sendVoiceChunk(audioChunk) {
    const ws = voiceSocket.value
    if (!ws || ws.readyState !== WebSocket.OPEN || !voiceStreamReady.value) return
    ws.send(JSON.stringify({ type: 'audio_stream_chunk', data: arrayBufferToBase64(audioChunk.buffer) }))
  }

  function sendVoiceStreamEnd() {
    const ws = voiceSocket.value
    if (!ws || ws.readyState !== WebSocket.OPEN || !voiceStreamReady.value) {
      voiceBusy.value = false; voiceError.value = '语音流未连接，请重新按住说话。'; return
    }
    ws.send(JSON.stringify({ type: 'audio_stream_end' }))
  }

  function flushVoiceTailChunk() {
    if (!streamingAudioBuffer.value.length) return
    sendVoiceChunk(new Float32Array(streamingAudioBuffer.value))
    streamingAudioBuffer.value = []
  }

  // ── audio capture ──────────────────────────────────────────

  function releaseAudioResources() {
    if (scriptProcessor.value) { try { scriptProcessor.value.disconnect() } catch (_) {}; scriptProcessor.value = null }
    if (mediaStream.value) { mediaStream.value.getTracks().forEach(track => track.stop()); mediaStream.value = null }
    if (audioContext.value) { try { audioContext.value.close() } catch (_) {}; audioContext.value = null }
  }

  async function startRecording() {
    if (state.value === 'COMPLETED' || sending.value || voiceBusy.value || isRecording.value) return false
    if (!voiceSupported) { voiceError.value = '当前浏览器无法访问麦克风，请检查浏览器权限或使用 Chrome / Edge。'; return false }
    try {
      voiceText.value = ''; voiceError.value = ''; audioBuffers.value = []; voiceBusy.value = true
      await openVoiceStream()
      mediaStream.value = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      audioContext.value = new AudioCtx({ sampleRate: TARGET_SAMPLE_RATE })
      const source = audioContext.value.createMediaStreamSource(mediaStream.value)
      scriptProcessor.value = audioContext.value.createScriptProcessor(4096, 1, 1)
      streamingAudioBuffer.value = []
      const chunkSamples = Math.round(TARGET_SAMPLE_RATE * (STREAM_CHUNK_MS / 1000))
      scriptProcessor.value.onaudioprocess = (event) => {
        if (!isRecording.value) return
        const inputData = event.inputBuffer.getChannelData(0)
        const resampled = audioContext.value.sampleRate === TARGET_SAMPLE_RATE ? inputData : resampleLinear(inputData, audioContext.value.sampleRate, TARGET_SAMPLE_RATE)
        audioBuffers.value.push(new Float32Array(resampled))
        streamingAudioBuffer.value.push(...resampled)
        while (streamingAudioBuffer.value.length >= chunkSamples) {
          sendVoiceChunk(new Float32Array(streamingAudioBuffer.value.splice(0, chunkSamples)))
        }
      }
      source.connect(scriptProcessor.value); scriptProcessor.value.connect(audioContext.value.destination)
      recordStartedAt.value = Date.now(); isRecording.value = true; voiceBusy.value = false; voiceText.value = '正在录音...'
      return true
    } catch (error) {
      voiceError.value = `无法启动语音识别：${error.message || '请确认麦克风权限和语音服务'}`; voiceBusy.value = false; closeVoiceStream(); releaseAudioResources()
      return false
    }
  }

  async function stopRecording() {
    if (!isRecording.value || voiceBusy.value) return
    isRecording.value = false
    const duration = Date.now() - recordStartedAt.value
    if (duration < 600) { voiceError.value = '录音时间太短，请至少说 1 秒。'; voiceText.value = ''; closeVoiceStream(); releaseAudioResources(); return }
    voiceText.value = voiceText.value && voiceText.value !== '正在录音...' ? voiceText.value : '录音完成，正在做二次精校...'
    voiceBusy.value = true; flushVoiceTailChunk(); sendVoiceStreamEnd(); releaseAudioResources()
  }

  // ── hold-to-speak gesture ──────────────────────────────────

  async function startHoldRecording(event) {
    if (event?.type === 'pointerdown' && event.button !== 0) return
    event?.preventDefault?.()
    if (activeVoicePointerId.value !== null || voiceBusy.value || sending.value) return
    if (!voiceMode.value) voiceMode.value = true
    pendingVoiceRelease.value = false; activeVoicePointerId.value = event?.pointerId ?? 'keyboard'
    try { event?.currentTarget?.setPointerCapture?.(event.pointerId) } catch (_) {}
    const started = await startRecording()
    if (!started) { activeVoicePointerId.value = null; pendingVoiceRelease.value = false; return }
    if (pendingVoiceRelease.value) await finishHoldRecording(event)
  }

  async function finishHoldRecording(event) {
    if (activeVoicePointerId.value === null) return
    if (event?.pointerId !== undefined && activeVoicePointerId.value !== event.pointerId) return
    event?.preventDefault?.()
    if (!isRecording.value) { pendingVoiceRelease.value = true; return }
    try { event?.currentTarget?.releasePointerCapture?.(event.pointerId) } catch (_) {}
    activeVoicePointerId.value = null; pendingVoiceRelease.value = false
    await stopRecording()
  }

  async function leaveHoldRecording(event) {
    if (event?.pointerType === 'mouse') await finishHoldRecording(event)
  }

  function cancelHoldRecording(event) {
    if (activeVoicePointerId.value === null) return
    event?.preventDefault?.(); activeVoicePointerId.value = null; pendingVoiceRelease.value = false
    isRecording.value = false; voiceText.value = ''; voiceError.value = '录音已取消，请重新按住说话。'
    closeVoiceStream(); releaseAudioResources()
  }

  function toggleVoiceMode() {
    voiceMode.value = !voiceMode.value
    voiceError.value = ''
    if (!voiceMode.value) { stopRecording() }
  }

  // ── keyboard support ───────────────────────────────────────

  function isTypingTarget(target) {
    const tagName = target?.tagName?.toLowerCase?.()
    return ['input', 'textarea', 'select'].includes(tagName) || Boolean(target?.isContentEditable)
  }

  async function handleGlobalVoiceKeydown(event) {
    if (event.code !== 'Space' || event.repeat || isTypingTarget(event.target)) return
    if (event.ctrlKey || event.metaKey || event.altKey) return
    await startHoldRecording(event)
  }

  async function handleGlobalVoiceKeyup(event) {
    if (event.code !== 'Space' || isTypingTarget(event.target)) return
    await finishHoldRecording(event)
  }

  // ── file-based ASR fallback ────────────────────────────────

  async function transcribeVoice(blob) {
    voiceBusy.value = true; voiceError.value = ''
    try {
      const formData = new FormData(); formData.append('file', blob, `interview-${Date.now()}.wav`)
      const res = await fetch('/api/voice/asr', { method: 'POST', body: formData })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || '语音识别失败')
      const text = String(data.text || '').trim()
      if (!text) throw new Error('FunASR 没有识别到有效文字')
      voiceText.value = text
    } catch (error) { voiceError.value = error.message || '语音识别失败'; voiceText.value = '' }
    finally { voiceBusy.value = false }
  }

  return {
    voiceMode, autoSpeak, isRecording, voiceText, voiceError, voiceBusy,
    voiceSupported, voiceSocket, voiceStreamReady,
    activeVoicePointerId, pendingVoiceRelease,
    startRecording, stopRecording, startHoldRecording, finishHoldRecording,
    leaveHoldRecording, cancelHoldRecording, toggleVoiceMode, transcribeVoice,
    releaseAudioResources, handleGlobalVoiceKeydown, handleGlobalVoiceKeyup,
    closeVoiceStream, stopRecording,
  }
}
