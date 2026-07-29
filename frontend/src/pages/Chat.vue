<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVoice } from '../composables/useVoice.js'
import { useLive2D } from '../composables/useLive2D.js'

const route = useRoute()
const router = useRouter()
const messages = ref([])
const input = ref('')
const state = ref('READY_CHECK')
const sending = ref(false)
const sessionId = ref('')
const chatBox = ref(null)
const answerInputRef = ref(null)
const role = ref(safeGetLocalStorage('role', 'user'))
const planInfo = ref(null)
const completionDialogVisible = ref(false)
const endingEarly = ref(false)
const endedEarly = ref(false)
const textDecoder = new TextDecoder('utf-8')

// ── composables ──────────────────────────────────────────────

async function handleRecognized(text) {
  input.value = text
  await sendMessage()
}

const voice = useVoice({ state, sending, input, onRecognized: handleRecognized })
const live2d = useLive2D()

// ── computed ─────────────────────────────────────────────────

const isAdmin = computed(() => role.value === 'admin')
const backPath = computed(() => isAdmin.value ? '/admin' : '/user')
const candidateName = computed(() => planInfo.value?.candidate_name || safeGetLocalStorage('nickname', '我'))
const jobName = computed(() => planInfo.value?.jd_name || '目标岗位')
const interviewerName = computed(() => planInfo.value?.interviewer || 'AI 面试官')
const roundName = computed(() => planInfo.value?.interview_round || '当前面试')
const roundSummary = computed(() => {
  const current = Number(planInfo.value?.stage_order || 0)
  const total = Number(planInfo.value?.stage_count || 0)
  if (current && total) return `${roundName.value} · ${current}/${total}`
  return roundName.value
})
const interviewerCount = computed(() => messages.value.filter(item => item.role !== 'candidate').length)
const candidateCount = computed(() => messages.value.filter(item => item.role === 'candidate').length)
const statusText = computed(() => ({
  READY_CHECK: '准备确认', INTERVIEWING: '面试进行中', COMPLETED: '面试已完成',
}[state.value] || state.value))
const interviewerMood = computed(() => {
  if (state.value === 'COMPLETED') return '已完成'
  if (voice.voiceBusy.value) return '正在理解你的回答'
  if (voice.isRecording.value) return '正在聆听'
  if (sending.value) return '正在思考'
  return '在线候场'
})

watch(input, () => nextTick(resizeAnswerInput))

// ── helpers ──────────────────────────────────────────────────

function nowIso() { return new Date().toISOString() }

function resizeAnswerInput() {
  const el = answerInputRef.value
  if (!el) return
  el.style.height = 'auto'
  const nextHeight = Math.min(Math.max(el.scrollHeight, 56), 220)
  el.style.height = `${nextHeight}px`
  el.style.overflowY = el.scrollHeight > 220 ? 'auto' : 'hidden'
}

function withTimestamp(message) {
  return { ...message, timestamp: message.timestamp || message.created_at || '' }
}

function formatMessageTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

function safeGetLocalStorage(key, fallback = '') {
  try { return window.localStorage?.getItem(key) || fallback } catch (_) { return fallback }
}

async function scrollDown() {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

function roleLabel(roleName) {
  if (roleName === 'candidate') return '我'
  if (roleName === 'system') return '系统'
  return interviewerName.value
}

function roleShort(roleName) {
  if (roleName === 'candidate') return '我'
  if (roleName === 'system') return '!'
  return '官'
}

// ── lifecycle ────────────────────────────────────────────────

onMounted(async () => {
  window.addEventListener('keydown', voice.handleGlobalVoiceKeydown)
  window.addEventListener('keyup', voice.handleGlobalVoiceKeyup)
  window.addEventListener('resize', live2d.keepAvatarInViewport)
  live2d.restoreAvatarPosition()
  live2d.initLive2D()
  const jd = route.query.jd
  const resume = route.query.resume
  const planId = route.query.plan_id
  if (!planId && (!jd || !resume)) {
    messages.value.push(withTimestamp({ role: 'system', content: '缺少 JD 或简历参数，请返回重新生成面试计划。', timestamp: nowIso() }))
    return
  }
  try {
    if (planId) await loadPlanInfo(Number(planId))
    const token = safeGetLocalStorage('token', '')
    const res = await fetch('/api/chat/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(planId ? { plan_id: Number(planId) } : { jd_filename: jd, resume_filename: resume }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '当前暂不能开始面试')
    sessionId.value = data.session_id
    messages.value = Array.isArray(data.history) && data.history.length
      ? data.history.map(withTimestamp)
      : [withTimestamp({ role: 'interviewer', content: data.message, timestamp: nowIso() })]
    state.value = data.state
    if (state.value === 'COMPLETED') {
      if (voice.autoSpeak.value) await live2d.speakText(messages.value.at(-1)?.content || '')
      showCompletionDialog()
    } else if (voice.autoSpeak.value) {
      live2d.speakText(messages.value.at(-1)?.content || '')
    }
    await scrollDown()
  } catch (e) {
    messages.value.push(withTimestamp({ role: 'system', content: '启动面试失败: ' + e.message, timestamp: nowIso() }))
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', voice.handleGlobalVoiceKeydown)
  window.removeEventListener('keyup', voice.handleGlobalVoiceKeyup)
  window.removeEventListener('resize', live2d.keepAvatarInViewport)
  voice.isRecording.value = false
  voice.activeVoicePointerId.value = null
  voice.pendingVoiceRelease.value = false
  voice.releaseAudioResources()
  live2d.stopSpeaking()
  live2d.destroyLive2D()
})

// ── plan info ────────────────────────────────────────────────

async function loadPlanInfo(planId) {
  try {
    if (isAdmin.value) return
    const token = safeGetLocalStorage('token', '')
    const res = await fetch('/api/plans/my', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) return
    const list = await res.json()
    planInfo.value = Array.isArray(list) ? list.find(item => Number(item.id) === Number(planId)) || null : null
  } catch (_) {}
}

// ── messaging ────────────────────────────────────────────────

async function sendMessage() {
  const text = input.value.trim()
  if (!text || sending.value || state.value === 'COMPLETED') return
  messages.value.push(withTimestamp({ role: 'candidate', content: text, timestamp: nowIso() }))
  input.value = ''
  sending.value = true
  await scrollDown()

  try {
    const interviewerMessage = withTimestamp({ role: 'interviewer', content: '', timestamp: nowIso() })
    messages.value.push(interviewerMessage)
    await scrollDown()

    const res = await fetch('/api/chat/message/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${safeGetLocalStorage('token', '')}`,
      },
      body: JSON.stringify({ session_id: sessionId.value, message: text }),
    })
    if (!res.ok) {
      let errText = '发送失败'
      try { const data = await res.json(); errText = data.detail || errText } catch (_) {}
      throw new Error(errText)
    }

    const reader = res.body?.getReader()
    if (!reader) throw new Error('当前浏览器不支持流式响应')

    let fullText = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const chunk = textDecoder.decode(value, { stream: true })
      if (!chunk) continue
      fullText += chunk
      interviewerMessage.content = fullText
      interviewerMessage.timestamp = nowIso()
      messages.value = [...messages.value]
      await scrollDown()
    }
    const tail = textDecoder.decode()
    if (tail) { fullText += tail; interviewerMessage.content = fullText; messages.value = [...messages.value] }

    const nextState = res.headers.get('X-Chat-State')
    if (nextState) state.value = nextState
    if (!interviewerMessage.content) interviewerMessage.content = '我刚刚没能正常生成回复，我们继续。'
    if (state.value === 'COMPLETED') {
      if (voice.autoSpeak.value) await live2d.speakText(interviewerMessage.content)
      showCompletionDialog()
    } else if (voice.autoSpeak.value) {
      live2d.speakText(interviewerMessage.content)
    }
    await scrollDown()
  } catch (e) {
    if (messages.value[messages.value.length - 1]?.role === 'interviewer' && !messages.value[messages.value.length - 1]?.content) {
      messages.value.pop()
    }
    messages.value.push(withTimestamp({ role: 'system', content: '发送失败: ' + e.message, timestamp: nowIso() }))
  } finally {
    sending.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
}

function showCompletionDialog() {
  voice.stopRecording()
  live2d.stopSpeaking()
  voice.closeVoiceStream()
  completionDialogVisible.value = true
}

async function endInterviewEarly() {
  if (!sessionId.value || !['READY_CHECK', 'INTERVIEWING'].includes(state.value) || sending.value || endingEarly.value) return
  const confirmed = await window.appConfirm(
    '确认提前结束本轮面试吗？已完成的回答会保留并提交招聘方评估，未回答的问题将不再继续。',
    { title: '提前结束面试', confirmText: '确认结束' },
  )
  if (!confirmed) return
  endingEarly.value = true
  try {
    voice.stopRecording()
    live2d.stopSpeaking()
    const token = safeGetLocalStorage('token', '')
    const res = await fetch('/api/chat/end', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ session_id: sessionId.value }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || '提前结束面试失败')
    endedEarly.value = true
    state.value = data.state || 'COMPLETED'
    messages.value.push(withTimestamp({
      role: 'interviewer',
      content: data.message || '本轮面试已提前结束，已完成的回答已经保存。',
      timestamp: nowIso(),
    }))
    await scrollDown()
    showCompletionDialog()
  } catch (error) {
    messages.value.push(withTimestamp({ role: 'system', content: error.message || '提前结束面试失败', timestamp: nowIso() }))
  } finally {
    endingEarly.value = false
  }
}

function returnAfterCompletion() {
  completionDialogVisible.value = false
  router.push(backPath.value)
}
</script>

<template>
  <div class="h-screen overflow-hidden bg-[#eef2ff] text-slate-900">
    <main class="h-full overflow-y-auto px-6 py-8">
      <div class="mx-auto grid h-full max-w-[1760px] grid-cols-1 gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-indigo-100/80">
          <router-link :to="backPath" class="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-indigo-600 no-underline">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            返回面试入口
          </router-link>

          <div class="mt-8">
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
              <svg class="h-9 w-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm3.75 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm3.75 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 12c0 4.142-4.03 7.5-9 7.5a10.5 10.5 0 0 1-3.151-.477L3 21l1.58-4.214A6.9 6.9 0 0 1 3 12c0-4.142 4.03-7.5 9-7.5s9 3.358 9 7.5Z" />
              </svg>
            </div>
            <p class="mt-5 text-xs font-bold uppercase tracking-[0.2em] text-emerald-400">Candidate interview</p>
            <h1 class="mt-2 text-2xl font-bold text-slate-950">我的面试</h1>
            <p class="mt-2 text-sm leading-6 text-slate-500">请按面试官的问题逐条回答，系统会自动保存当前对话进度。</p>
          </div>

          <div class="mt-8 space-y-3">
            <div class="rounded-2xl bg-slate-50 p-4">
              <p class="text-xs font-semibold text-slate-400">候选人</p>
              <p class="mt-1 text-base font-bold leading-6 text-slate-900">{{ candidateName }}</p>
            </div>
            <div class="rounded-2xl bg-slate-50 p-4">
              <p class="text-xs font-semibold text-slate-400">应聘岗位</p>
              <p class="mt-1 line-clamp-2 text-base font-bold text-slate-900">{{ jobName }}</p>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="rounded-2xl bg-indigo-50 p-4">
                <p class="text-xs font-semibold text-indigo-400">面试官</p>
                <p class="mt-1 text-base font-bold leading-6 text-indigo-700">{{ interviewerName }}</p>
              </div>
              <div class="rounded-2xl bg-violet-50 p-4">
                <p class="text-xs font-semibold text-violet-400">当前轮次</p>
                <p class="mt-1 text-base font-bold leading-6 text-violet-700">{{ roundSummary }}</p>
              </div>
            </div>
          </div>

          <div class="mt-6 grid grid-cols-3 gap-3">
            <div class="rounded-2xl bg-indigo-50 p-3 text-center">
              <p class="text-lg font-black text-indigo-600">{{ messages.length }}</p>
              <p class="text-xs font-semibold text-indigo-400">消息</p>
            </div>
            <div class="rounded-2xl bg-blue-50 p-3 text-center">
              <p class="text-lg font-black text-blue-600">{{ interviewerCount }}</p>
              <p class="text-xs font-semibold text-blue-400">提问</p>
            </div>
            <div class="rounded-2xl bg-emerald-50 p-3 text-center">
              <p class="text-lg font-black text-emerald-600">{{ candidateCount }}</p>
              <p class="text-xs font-semibold text-emerald-400">回答</p>
            </div>
          </div>

          <div class="mt-6 rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
            <p class="text-xs font-semibold text-emerald-500">当前状态</p>
            <p class="mt-1 text-lg font-black text-emerald-700">{{ statusText }}</p>
            <p class="mt-2 text-xs leading-5 text-emerald-600">离开页面后可从面试入口继续当前轮次。</p>
            <button
              v-if="state !== 'COMPLETED'"
              :disabled="sending || endingEarly"
              class="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-amber-200 bg-white px-4 py-2.5 text-sm font-bold text-amber-700 transition hover:border-amber-300 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
              @click="endInterviewEarly"
            >
              <i class="fa fa-stop-circle-o" aria-hidden="true"></i>
              {{ endingEarly ? '正在结束…' : '提前结束面试' }}
            </button>
          </div>

          <div class="mt-4 rounded-2xl border border-indigo-100 bg-indigo-50 p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-xs font-semibold text-indigo-500">语音输入</p>
                <p class="mt-1 text-sm leading-5 text-indigo-700">{{ voice.voiceMode.value ? '已开启 FunASR 语音识别' : '文字输入为主，可开启语音识别' }}</p>
              </div>
              <button
                :class="[voice.voiceMode.value ? 'bg-indigo-600 text-white' : 'bg-white text-indigo-600 ring-1 ring-indigo-100']"
                @click="voice.toggleVoiceMode"
              >
                {{ voice.voiceMode.value ? '已开启' : '开启' }}
              </button>
            </div>
            <label class="mt-3 flex items-center gap-2 text-xs font-semibold text-indigo-600">
              <input :checked="voice.autoSpeak.value" @change="voice.autoSpeak.value = $event.target.checked" type="checkbox" class="h-4 w-4 rounded border-indigo-200">
              面试官回复自动朗读
            </label>
            <p v-if="voice.voiceMode.value && !voice.voiceSupported" class="mt-3 rounded-xl bg-white px-3 py-2 text-xs leading-5 text-amber-600">当前浏览器无法访问麦克风，请检查麦克风权限或使用 Chrome / Edge。</p>
          </div>
        </aside>

        <section class="flex min-h-0 flex-col overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-indigo-100/80">
          <header class="flex flex-shrink-0 items-center justify-between border-b border-slate-100 px-6 py-5">
            <div>
              <h2 class="text-xl font-bold text-slate-950">面试对话</h2>
              <p class="mt-1 text-sm text-slate-500">{{ interviewerName }} · {{ roundSummary }} · 每条回答都会自动保存。</p>
            </div>
            <div class="flex items-center gap-2">
              <button
                class="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-50"
                @click="live2d.stopSpeaking"
              >
                停止朗读
              </button>
              <span class="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-500">{{ messages.length }} 条消息</span>
            </div>
          </header>

          <div class="flex-shrink-0 border-b border-slate-100 bg-white/95 px-6 py-4 backdrop-blur">
            <div class="rounded-[24px] border border-indigo-100 bg-slate-50 px-5 py-4">
              <div class="flex items-center gap-5">
                <div class="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-lg font-black text-indigo-600">AI</div>
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="text-xs font-black uppercase tracking-[0.22em] text-indigo-400">Digital interviewer</p>
                    <span class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-600">{{ interviewerMood }}</span>
                  </div>
                  <h3 class="mt-1 text-xl font-black text-slate-950">{{ interviewerName }}</h3>
                  <p class="mt-1 truncate text-sm font-semibold text-slate-500">{{ roundSummary }} · 面向「{{ jobName }}」的结构化面试</p>
                </div>
                <div class="rounded-2xl bg-indigo-50 px-4 py-3 text-right">
                  <p class="text-xs font-bold text-indigo-400">当前进度</p>
                  <p class="mt-1 text-lg font-black text-indigo-700">{{ candidateCount }} / {{ interviewerCount }}</p>
                </div>
              </div>
            </div>
          </div>

          <div class="relative min-h-0 flex-1 bg-[#eef2f8]">
            <div ref="chatBox" class="h-full overflow-y-auto px-6 py-5 pb-28">
              <div class="space-y-5">
                <div
                  v-for="(msg, i) in messages"
                  :key="i"
                  :class="['flex gap-3', msg.role === 'candidate' ? 'justify-end' : 'justify-start']"
                >
                  <div v-if="msg.role !== 'candidate'" class="mt-7 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-base font-bold text-white shadow-sm">
                    <div v-if="msg.role !== 'system'" class="digital-interviewer-mini">
                      <span></span>
                      <span></span>
                    </div>
                    <span v-else>{{ roleShort(msg.role) }}</span>
                  </div>
                  <div :class="['max-w-[68%]', msg.role === 'candidate' ? 'text-right' : 'text-left']">
                    <div :class="['mb-1.5 flex items-center gap-2', msg.role === 'candidate' ? 'justify-end' : 'justify-start']">
                      <span class="text-[17px] font-bold text-slate-700">{{ roleLabel(msg.role) }}</span>
                      <span v-if="formatMessageTime(msg.timestamp)" class="text-[15px] font-semibold text-slate-400">{{ formatMessageTime(msg.timestamp) }}</span>
                    </div>
                    <div
                      :class="[
                        'inline-block rounded-2xl px-4 py-3 text-left text-[19px] leading-9 whitespace-pre-wrap shadow-sm',
                        msg.role === 'candidate'
                          ? 'rounded-tr-md bg-[#95ec69] text-slate-950 shadow-emerald-100'
                          : msg.role === 'system'
                            ? 'rounded-tl-md bg-red-50 text-red-600 ring-1 ring-red-100'
                            : 'rounded-tl-md bg-white text-slate-700 ring-1 ring-slate-100'
                      ]"
                    >
                      <span v-if="msg.content">{{ msg.content }}</span>
                      <span v-else-if="msg.role === 'interviewer' && sending" class="inline-flex gap-1 align-middle">
                        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay: 0ms"></span>
                        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay: 150ms"></span>
                        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay: 300ms"></span>
                      </span>
                    </div>
                  </div>
                  <div v-if="msg.role === 'candidate'" class="mt-7 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-emerald-500 text-base font-bold text-white shadow-sm">
                    {{ roleShort(msg.role) }}
                  </div>
                </div>
              </div>
            </div>

          </div>

          <footer class="flex-shrink-0 border-t border-slate-100 bg-white px-5 py-4">
            <div class="rounded-3xl border border-slate-200 bg-slate-50 p-2">
              <div v-if="voice.isRecording.value || voice.voiceBusy.value || voice.voiceError.value" class="mb-2 flex items-center gap-2 px-4 py-2 text-sm font-semibold">
                <span :class="['h-2.5 w-2.5 rounded-full', voice.isRecording.value ? 'animate-pulse bg-red-500' : voice.voiceBusy.value ? 'animate-pulse bg-indigo-500' : 'bg-red-500']"></span>
                <span :class="voice.voiceError.value ? 'text-red-500' : 'text-slate-500'">
                  {{ voice.voiceError.value || (voice.isRecording.value ? '正在听你说话，松开后自动写入输入框并发送。' : '正在识别语音，识别结果会出现在下方输入框。') }}
                </span>
              </div>
              <div class="flex items-end gap-3">
                <textarea
                  ref="answerInputRef"
                  v-model="input"
                  :disabled="state === 'COMPLETED' || sending"
                  rows="1"
                  placeholder="输入你的回答，Enter 发送，Shift + Enter 换行"
                  class="max-h-[220px] min-h-14 flex-1 resize-none rounded-2xl border-0 bg-transparent px-5 py-3 text-[18px] leading-8 text-slate-800 placeholder-slate-400 outline-none transition disabled:opacity-50"
                  @keydown="onKeydown"
                  @input="resizeAnswerInput"
                ></textarea>
                <button
                  :disabled="!input.trim() || sending || state === 'COMPLETED'"
                  class="flex h-12 min-w-[78px] flex-shrink-0 items-center justify-center rounded-full bg-emerald-500 px-5 text-sm font-bold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
                  @click="sendMessage"
                >
                  发送
                </button>
                <button
                  :disabled="!voice.voiceSupported || state === 'COMPLETED' || sending || voice.voiceBusy.value"
                  :aria-pressed="voice.isRecording.value"
                  :class="[
                    'flex h-12 min-w-[106px] touch-none select-none items-center justify-center gap-1.5 rounded-full px-5 text-sm font-bold shadow-sm transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40',
                    voice.isRecording.value ? 'bg-red-500 text-white shadow-red-100 ring-4 ring-red-100' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                  ]"
                  @pointerdown="voice.startHoldRecording"
                  @pointerup="voice.finishHoldRecording"
                  @pointerleave="voice.leaveHoldRecording"
                  @pointercancel="voice.cancelHoldRecording"
                  @lostpointercapture="voice.finishHoldRecording"
                  @keydown="voice.startHoldRecording"
                  @keyup="voice.finishHoldRecording"
                  @contextmenu.prevent
                >
                  <span class="text-base">{{ voice.isRecording.value ? '●' : '🎤' }}</span>
                  {{ voice.voiceBusy.value ? '识别中' : voice.isRecording.value ? '松开' : '按住说话' }}
                </button>
              </div>
            </div>
          </footer>
        </section>
      </div>
    </main>

    <div
      v-if="completionDialogVisible"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-6 backdrop-blur-sm"
    >
      <div class="w-full max-w-md rounded-[28px] bg-white p-7 text-center shadow-2xl shadow-slate-900/20 ring-1 ring-white/70">
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-emerald-50 text-3xl text-emerald-500">
          ✓
        </div>
        <p class="mt-5 text-sm font-black uppercase tracking-[0.22em] text-emerald-400">Interview complete</p>
        <h3 class="mt-2 text-2xl font-black text-slate-950">{{ endedEarly ? '本轮面试已提前结束' : '本轮面试已结束' }}</h3>
        <p class="mx-auto mt-3 max-w-sm text-sm font-medium leading-7 text-slate-500">
          {{ endedEarly ? '已完成的回答已经保存并提交招聘方评估，未回答的问题不会影响记录保存。' : '感谢你的参与，本轮回答已经保存。你可以回到面试入口查看后续安排。' }}
        </p>
        <div class="mt-7 flex flex-col gap-3">
          <button
            class="h-12 rounded-2xl bg-emerald-500 px-5 text-base font-black text-white transition hover:bg-emerald-600"
            @click="returnAfterCompletion"
          >
            返回面试入口
          </button>
          <router-link
            v-if="isAdmin"
            :to="{ path: '/admin/report', query: { session_id: sessionId } }"
            class="inline-flex h-11 items-center justify-center rounded-2xl bg-slate-100 text-sm font-bold text-slate-600 no-underline hover:bg-slate-200"
          >
            查看面试报告
          </router-link>
        </div>
      </div>
    </div>

    <div
      class="floating-interviewer"
      :class="{ 'floating-interviewer--dragging': live2d.avatarDragging.value, 'floating-interviewer--active': sending || voice.voiceBusy.value, 'floating-interviewer--listening': voice.isRecording.value }"
      :style="{ left: `${live2d.avatarPosition.value.x}px`, top: `${live2d.avatarPosition.value.y}px` }"
      @pointerdown="live2d.startAvatarDrag"
      @pointermove="live2d.moveAvatar"
      @pointerup="live2d.endAvatarDrag"
      @pointercancel="live2d.endAvatarDrag"
    >
      <canvas
        :ref="(el) => { live2d.live2dCanvas.value = el }"
        v-show="live2d.live2dReady.value"
        class="live2d-avatar__canvas"
        aria-label="Live2D AI 面试官"
      ></canvas>
      <div v-if="!live2d.live2dReady.value" class="live2d-avatar__fallback" :title="live2d.live2dError.value || '数字人加载中'">
        <div class="digital-interviewer" aria-label="AI 面试官">
          <span class="digital-interviewer__antenna"></span>
          <span class="digital-interviewer__face">
            <i class="digital-interviewer__eye"></i>
            <i class="digital-interviewer__eye"></i>
            <i class="digital-interviewer__mouth"></i>
          </span>
          <span class="digital-interviewer__body"></span>
        </div>
        <span>{{ live2d.live2dError.value ? '数字人加载失败，点击重试' : '数字人加载中…' }}</span>
        <button v-if="live2d.live2dError.value" type="button" @pointerdown.stop @click.stop="live2d.initLive2D">重新加载</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.digital-interviewer {
  position: relative;
  width: 86px;
  height: 104px;
  flex: 0 0 auto;
  filter: drop-shadow(0 18px 24px rgba(79, 70, 229, 0.18));
}

.digital-interviewer__antenna {
  position: absolute;
  left: 39px;
  top: 0;
  width: 8px;
  height: 18px;
  border-radius: 999px;
  background: #6366f1;
}

.digital-interviewer__antenna::after {
  content: "";
  position: absolute;
  left: 50%;
  top: -7px;
  width: 14px;
  height: 14px;
  transform: translateX(-50%);
  border-radius: 999px;
  background: #34d399;
  box-shadow: 0 0 0 7px rgba(52, 211, 153, 0.14);
}

.digital-interviewer__face {
  position: absolute;
  left: 8px;
  top: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  width: 70px;
  height: 62px;
  border: 4px solid #ffffff;
  border-radius: 26px;
  background: linear-gradient(145deg, #4f46e5 0%, #7c3aed 55%, #06b6d4 100%);
}

.digital-interviewer__eye {
  width: 9px;
  height: 16px;
  border-radius: 999px;
  background: #e0f2fe;
  box-shadow: 0 0 12px rgba(224, 242, 254, 0.85);
}

.digital-interviewer__mouth {
  position: absolute;
  left: 28px;
  bottom: 14px;
  width: 18px;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
}

.digital-interviewer__body {
  position: absolute;
  left: 18px;
  bottom: 0;
  width: 50px;
  height: 34px;
  border-radius: 20px 20px 18px 18px;
  background: linear-gradient(180deg, #dbeafe 0%, #ffffff 100%);
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.15);
}

.digital-interviewer--active .digital-interviewer__eye,
.digital-interviewer--listening .digital-interviewer__eye {
  animation: digital-eye-pulse 1s ease-in-out infinite;
}

.digital-interviewer--listening .digital-interviewer__antenna::after {
  animation: digital-listening 0.9s ease-in-out infinite;
}

.digital-interviewer-mini {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  width: 24px;
  height: 22px;
  border-radius: 9px;
  background: linear-gradient(145deg, #eef2ff 0%, #e0f2fe 100%);
}

.digital-interviewer-mini span {
  width: 4px;
  height: 8px;
  border-radius: 999px;
  background: #4f46e5;
}

.floating-interviewer {
  position: fixed;
  z-index: 40;
  width: 860px;
  height: 1000px;
  cursor: grab;
  user-select: none;
  touch-action: none;
  background: transparent;
  transition: transform 0.18s ease, filter 0.18s ease;
}

.floating-interviewer--dragging {
  cursor: grabbing;
  transform: scale(1.03);
  filter: drop-shadow(0 24px 32px rgba(79, 70, 229, 0.2));
}

.live2d-avatar__canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  filter: drop-shadow(0 24px 30px rgba(15, 23, 42, 0.16));
}

.live2d-avatar__fallback {
  position: absolute;
  left: 50%;
  top: 50%;
  display: flex;
  width: 190px;
  min-height: 170px;
  transform: translate(-50%, -50%);
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1px solid rgba(99, 102, 241, 0.16);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.14);
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  backdrop-filter: blur(12px);
}

.live2d-avatar__fallback button {
  border: 0;
  border-radius: 999px;
  background: #4f46e5;
  padding: 7px 14px;
  color: white;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.floating-interviewer--listening {
  filter: drop-shadow(0 22px 30px rgba(16, 185, 129, 0.24));
}

@keyframes digital-eye-pulse {
  0%, 100% {
    transform: scaleY(1);
    opacity: 1;
  }
  50% {
    transform: scaleY(0.55);
    opacity: 0.82;
  }
}

@keyframes digital-listening {
  0%, 100% {
    box-shadow: 0 0 0 7px rgba(52, 211, 153, 0.14);
  }
  50% {
    box-shadow: 0 0 0 14px rgba(52, 211, 153, 0.04);
  }
}
</style>
