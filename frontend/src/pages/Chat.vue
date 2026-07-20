<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const messages = ref([])
const input = ref('')
const state = ref('READY_CHECK')
const sending = ref(false)
const sessionId = ref('')
const chatBox = ref(null)
const role = ref(safeGetLocalStorage('role', 'user'))
const planInfo = ref(null)
const isAdmin = computed(() => role.value === 'admin')
const backPath = computed(() => isAdmin.value ? '/interviewee' : '/user')
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
  READY_CHECK: '准备确认',
  INTERVIEWING: '面试进行中',
  COMPLETED: '面试已完成',
}[state.value] || state.value)
)

function nowIso() {
  return new Date().toISOString()
}

function withTimestamp(message) {
  return {
    ...message,
    timestamp: message.timestamp || message.created_at || '',
  }
}

function formatMessageTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

function safeGetLocalStorage(key, fallback = '') {
  try {
    return window.localStorage?.getItem(key) || fallback
  } catch (_) {
    return fallback
  }
}

onMounted(async () => {
  const jd = route.query.jd
  const resume = route.query.resume
  const planId = route.query.plan_id
  if (!planId && (!jd || !resume)) {
    messages.value.push(withTimestamp({ role: 'system', content: '缺少 JD 或简历参数，请返回重新生成面试计划。', timestamp: nowIso() }))
    return
  }
  try {
    if (planId) await loadPlanInfo(Number(planId))
    const res = await fetch('/api/chat/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(planId ? { plan_id: Number(planId) } : { jd_filename: jd, resume_filename: resume }),
    })
    const data = await res.json()
    sessionId.value = data.session_id
    messages.value = Array.isArray(data.history) && data.history.length
      ? data.history.map(withTimestamp)
      : [withTimestamp({ role: 'interviewer', content: data.message, timestamp: nowIso() })]
    state.value = data.state
    await scrollDown()
  } catch (e) {
    messages.value.push(withTimestamp({ role: 'system', content: '启动面试失败: ' + e.message, timestamp: nowIso() }))
  }
})

async function loadPlanInfo(planId) {
  try {
    if (isAdmin.value) return
    const res = await fetch('/api/plans/my')
    if (!res.ok) return
    const list = await res.json()
    planInfo.value = Array.isArray(list) ? list.find(item => Number(item.id) === Number(planId)) || null : null
  } catch (_) {
    // ignore
  }
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || sending.value || state.value === 'COMPLETED') return
  messages.value.push(withTimestamp({ role: 'candidate', content: text, timestamp: nowIso() }))
  input.value = ''
  sending.value = true
  await scrollDown()

  try {
    const res = await fetch('/api/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value, message: text }),
    })
    const data = await res.json()
    messages.value.push(withTimestamp({ role: 'interviewer', content: data.message, timestamp: nowIso() }))
    state.value = data.state
    await scrollDown()
  } catch (e) {
    messages.value.push(withTimestamp({ role: 'system', content: '发送失败: ' + e.message, timestamp: nowIso() }))
  } finally {
    sending.value = false
  }
}

async function scrollDown() {
  await nextTick()
  if (chatBox.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight
  }
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
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
          </div>
        </aside>

        <section class="flex min-h-0 flex-col overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-indigo-100/80">
          <header class="flex flex-shrink-0 items-center justify-between border-b border-slate-100 px-6 py-5">
            <div>
              <h2 class="text-xl font-bold text-slate-950">面试对话</h2>
              <p class="mt-1 text-sm text-slate-500">{{ interviewerName }} · {{ roundSummary }} · 每条回答都会自动保存。</p>
            </div>
            <span class="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-500">{{ messages.length }} 条消息</span>
          </header>

          <div ref="chatBox" class="min-h-0 flex-1 overflow-y-auto bg-[#eef2f8] px-6 py-5">
            <div class="space-y-5">
              <div
                v-for="(msg, i) in messages"
                :key="i"
                :class="['flex gap-3', msg.role === 'candidate' ? 'justify-end' : 'justify-start']"
              >
                <div v-if="msg.role !== 'candidate'" class="mt-7 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-base font-bold text-white shadow-sm">
                  {{ roleShort(msg.role) }}
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
                    {{ msg.content }}
                  </div>
                </div>
                <div v-if="msg.role === 'candidate'" class="mt-7 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-emerald-500 text-base font-bold text-white shadow-sm">
                  {{ roleShort(msg.role) }}
                </div>
              </div>

              <div v-if="sending" class="flex justify-start gap-3">
                <div class="mt-1 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-base font-bold text-white shadow-sm">官</div>
                <div class="rounded-2xl rounded-tl-md bg-white px-4 py-3 text-lg text-slate-400 ring-1 ring-slate-100">
                  <span class="inline-flex gap-1">
                    <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay: 0ms"></span>
                    <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay: 150ms"></span>
                    <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay: 300ms"></span>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <footer class="flex-shrink-0 border-t border-slate-100 bg-white px-5 py-4">
            <div class="flex gap-3">
              <textarea
                v-model="input"
                :disabled="state === 'COMPLETED' || sending"
                rows="1"
                placeholder="输入你的回答，Enter 发送，Shift + Enter 换行"
                class="max-h-40 flex-1 resize-none rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-[18px] leading-8 text-slate-800 placeholder-slate-400 outline-none transition focus:border-emerald-400 focus:bg-white disabled:opacity-50"
                @keydown="onKeydown"
                @input="e => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px' }"
              ></textarea>
              <button
                :disabled="!input.trim() || sending || state === 'COMPLETED'"
                class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl bg-emerald-500 text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
                @click="sendMessage"
              >
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                </svg>
              </button>
            </div>
            <p v-if="state === 'COMPLETED'" class="mt-3 text-center text-xs text-slate-500">
              本轮面试已结束
              <template v-if="isAdmin">
                ·
                <router-link :to="{ path: '/report', query: { session_id: sessionId } }" class="font-medium text-emerald-600 hover:text-emerald-700">查看面试报告</router-link>
              </template>
              ·
              <router-link :to="backPath" class="text-blue-500 hover:text-blue-600">返回面试入口</router-link>
            </p>
          </footer>
        </section>
      </div>
    </main>
  </div>
</template>
