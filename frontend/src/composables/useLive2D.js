import { ref, nextTick } from 'vue'

const LIVE2D_MODEL_URL = '/hiyori_pro_zh/runtime/hiyori_pro_t11.model3.json'
const LIVE2D_SCRIPT_URLS = ['/js/live2dcubismcore.min.js', '/js/pixi.js', '/js/cubism4.min.js']
const AVATAR_WIDTH = 860
const AVATAR_HEIGHT = 1000
const AVATAR_VISUAL_CENTER_X = AVATAR_WIDTH / 2
const AVATAR_VISUAL_CENTER_Y = AVATAR_HEIGHT / 2
const VIEWPORT_SAFE_MARGIN = 120

export function useLive2D() {
  const avatarPosition = ref({ x: 0, y: 0 })
  const avatarDragging = ref(false)
  const avatarDragOffset = ref({ x: 0, y: 0 })
  const live2dCanvas = ref(null)
  const live2dReady = ref(false)
  const live2dError = ref('')
  const live2dApp = ref(null)
  const live2dModel = ref(null)
  const live2dAudioContext = ref(null)
  const live2dAudioSource = ref(null)
  const live2dAnalyser = ref(null)
  const live2dAudioData = ref(null)
  const live2dMouthFrame = ref(0)
  const currentAudio = ref(null)
  let live2dInitPromise = null

  // ── avatar position ────────────────────────────────────────

  function defaultAvatarPosition() {
    return {
      x: Math.max(16, window.innerWidth - 590),
      y: Math.max(16, window.innerHeight - 790),
    }
  }

  function restoreAvatarPosition() {
    const fallback = defaultAvatarPosition()
    try {
      const saved = JSON.parse(window.localStorage?.getItem('interview_avatar_position') || 'null')
      avatarPosition.value = saved && Number.isFinite(saved.x) && Number.isFinite(saved.y) ? clampAvatarPosition(saved) : fallback
    } catch (_) { avatarPosition.value = fallback }
  }

  function clampAvatarPosition(pos) {
    // 约束人物主体（画布中心）而非透明画布边缘，避免看似仍在屏幕内、实际人物已经消失。
    const minX = VIEWPORT_SAFE_MARGIN - AVATAR_VISUAL_CENTER_X
    const minY = VIEWPORT_SAFE_MARGIN - AVATAR_VISUAL_CENTER_Y
    const maxX = Math.max(minX, window.innerWidth - VIEWPORT_SAFE_MARGIN - AVATAR_VISUAL_CENTER_X)
    const maxY = Math.max(minY, window.innerHeight - VIEWPORT_SAFE_MARGIN - AVATAR_VISUAL_CENTER_Y)
    return {
      x: Math.min(Math.max(minX, Number(pos?.x) || 0), maxX),
      y: Math.min(Math.max(minY, Number(pos?.y) || 0), maxY),
    }
  }

  function keepAvatarInViewport() {
    avatarPosition.value = clampAvatarPosition(avatarPosition.value)
  }

  function startAvatarDrag(event) {
    if (event.button !== undefined && event.button !== 0) return
    const rect = event.currentTarget.getBoundingClientRect()
    avatarDragging.value = true
    avatarDragOffset.value = { x: event.clientX - rect.left, y: event.clientY - rect.top }
    event.currentTarget.setPointerCapture?.(event.pointerId)
  }

  function moveAvatar(event) {
    if (!avatarDragging.value) return
    avatarPosition.value = clampAvatarPosition({ x: event.clientX - avatarDragOffset.value.x, y: event.clientY - avatarDragOffset.value.y })
  }

  function endAvatarDrag(event) {
    if (!avatarDragging.value) return
    avatarDragging.value = false
    event.currentTarget.releasePointerCapture?.(event.pointerId)
    try { window.localStorage?.setItem('interview_avatar_position', JSON.stringify(avatarPosition.value)) } catch (_) {}
  }

  // ── script loading ─────────────────────────────────────────

  function loadExternalScript(src) {
    if (document.querySelector(`script[data-live2d-src="${src}"]`)) return Promise.resolve()
    return new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = src; script.async = false; script.dataset.live2dSrc = src
      script.onload = resolve; script.onerror = () => reject(new Error(`加载 Live2D 脚本失败: ${src}`))
      document.head.appendChild(script)
    })
  }

  async function ensureLive2DRuntime() {
    if (window.PIXI?.live2d?.Live2DModel) return
    for (const src of LIVE2D_SCRIPT_URLS) await loadExternalScript(src)
    if (!window.PIXI?.live2d?.Live2DModel) throw new Error('Live2D 运行时未就绪')
  }

  // ── init / destroy ─────────────────────────────────────────

  async function initLive2D() {
    if (live2dReady.value || live2dInitPromise) return live2dInitPromise
    live2dInitPromise = (async () => {
      try {
      await nextTick()
      if (!live2dCanvas.value) throw new Error('数字人画布尚未就绪')
      await ensureLive2DRuntime()
      const PIXI = window.PIXI
      const width = AVATAR_WIDTH; const height = AVATAR_HEIGHT
      const app = new PIXI.Application({
        view: live2dCanvas.value, width, height,
        resolution: window.devicePixelRatio || 1, autoDensity: true, antialias: true, backgroundAlpha: 0,
      })
      const model = await PIXI.live2d.Live2DModel.from(LIVE2D_MODEL_URL)
      app.stage.addChild(model)
      const scale = Math.min((width / model.width) * 1.05, (height / model.height) * 0.92)
      model.scale.set(scale)
      if (model.anchor?.set) { model.anchor.set(0.5, 0.5); model.x = width / 2; model.y = height / 2 }
      else { model.x = (width - model.width) / 2; model.y = height - model.height + 8 }
      model.interactive = false
      live2dApp.value = app; live2dModel.value = model; live2dReady.value = true; live2dError.value = ''
      model.motion?.('Idle')
      } catch (error) {
        live2dReady.value = false
        live2dError.value = error.message || 'Live2D 加载失败'
      } finally {
        live2dInitPromise = null
      }
    })()
    return live2dInitPromise
  }

  function destroyLive2D() {
    stopLive2DLipSync()
    live2dApp.value?.destroy?.(true)
    live2dModel.value = null; live2dApp.value = null; live2dReady.value = false
  }

  // ── lip sync ───────────────────────────────────────────────

  function setLive2DMouth(value) {
    const coreModel = live2dModel.value?.internalModel?.coreModel
    if (!coreModel) return
    coreModel.setParameterValueById('ParamMouthOpenY', Math.max(0, Math.min(1, value)), 0.85)
  }

  function startLive2DLipSync(audio) {
    if (!live2dReady.value || !audio) return
    stopLive2DLipSync(false)
    try {
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext
      if (!AudioContextCtor) return
      const audioCtx = new AudioContextCtor()
      const source = audioCtx.createMediaElementSource(audio)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      const data = new Uint8Array(analyser.frequencyBinCount)
      source.connect(analyser); analyser.connect(audioCtx.destination)
      live2dAudioContext.value = audioCtx; live2dAudioSource.value = source; live2dAnalyser.value = analyser; live2dAudioData.value = data
      audioCtx.resume?.()
      const tick = () => {
        if (!currentAudio.value || currentAudio.value !== audio || audio.paused || audio.ended) { stopLive2DLipSync(); return }
        analyser.getByteFrequencyData(data)
        const average = data.reduce((sum, item) => sum + item, 0) / data.length
        setLive2DMouth(Math.min(1, Math.pow((average / 255) * 3.2, 1.45)))
        live2dMouthFrame.value = requestAnimationFrame(tick)
      }
      live2dMouthFrame.value = requestAnimationFrame(tick)
    } catch (_) {
      let phase = 0
      const tick = () => {
        if (!currentAudio.value || currentAudio.value !== audio || audio.paused || audio.ended) { stopLive2DLipSync(); return }
        phase += 0.26; setLive2DMouth(0.18 + Math.abs(Math.sin(phase)) * 0.65)
        live2dMouthFrame.value = requestAnimationFrame(tick)
      }
      live2dMouthFrame.value = requestAnimationFrame(tick)
    }
  }

  function stopLive2DLipSync(resetMouth = true) {
    if (live2dMouthFrame.value) { cancelAnimationFrame(live2dMouthFrame.value); live2dMouthFrame.value = 0 }
    try { live2dAudioSource.value?.disconnect(); live2dAnalyser.value?.disconnect(); live2dAudioContext.value?.close() } catch (_) {}
    live2dAudioContext.value = null; live2dAudioSource.value = null; live2dAnalyser.value = null; live2dAudioData.value = null
    if (resetMouth) setLive2DMouth(0)
  }

  // ── TTS & speaking ─────────────────────────────────────────

  function stripMarkdown(text) {
    return String(text || '').replace(/```[\s\S]*?```/g, ' ').replace(/[#>*_`[\]()]/g, '').replace(/\s+/g, ' ').trim()
  }

  function playAudioToEnd(src) {
    return new Promise((resolve, reject) => {
      const audio = new Audio(src)
      const cleanup = () => { stopLive2DLipSync(); if (currentAudio.value === audio) currentAudio.value = null }
      audio.onended = () => { cleanup(); resolve() }
      audio.onerror = () => { cleanup(); reject(new Error('语音播放失败')) }
      currentAudio.value = audio; startLive2DLipSync(audio)
      audio.play().catch((error) => { cleanup(); reject(error) })
    })
  }

  async function speakText(text) {
    if (!text) return
    stopSpeaking()
    try {
      const res = await fetch('/api/voice/tts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: stripMarkdown(text) }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data.audio) throw new Error(data.detail || '语音合成失败')
      await playAudioToEnd(`data:${data.format || 'audio/mpeg'};base64,${data.audio}`)
    } catch (error) {
      stopLive2DLipSync(); currentAudio.value = null
    }
  }

  function stopSpeaking() {
    stopLive2DLipSync()
    if (!currentAudio.value) return
    currentAudio.value.pause(); currentAudio.value.currentTime = 0; currentAudio.value = null
  }

  return {
    avatarPosition, avatarDragging, live2dCanvas, live2dReady, live2dError, currentAudio,
    restoreAvatarPosition, keepAvatarInViewport, initLive2D, destroyLive2D,
    startAvatarDrag, moveAvatar, endAvatarDrag,
    speakText, stopSpeaking, playAudioToEnd, stripMarkdown,
  }
}
