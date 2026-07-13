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
const isAdmin = computed(() => role.value === 'admin')
const backPath = computed(() => isAdmin.value ? '/interviewee' : '/user')

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
    messages.value.push({ role: 'system', content: '缺少 JD 或简历参数，请返回重新生成面试计划。' })
    return
  }
  try {
    const res = await fetch('/api/chat/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(planId ? { plan_id: Number(planId) } : { jd_filename: jd, resume_filename: resume }),
    })
    const data = await res.json()
    sessionId.value = data.session_id
    messages.value = Array.isArray(data.history) && data.history.length
      ? data.history
      : [{ role: 'interviewer', content: data.message }]
    state.value = data.state
    await scrollDown()
  } catch (e) {
    messages.value.push({ role: 'system', content: '启动面试失败: ' + e.message })
  }
})

async function sendMessage() {
  const text = input.value.trim()
  if (!text || sending.value || state.value === 'COMPLETED') return
  messages.value.push({ role: 'candidate', content: text })
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
    messages.value.push({ role: 'interviewer', content: data.message })
    state.value = data.state
    await scrollDown()
  } catch (e) {
    messages.value.push({ role: 'system', content: '发送失败: ' + e.message })
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
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
    <!-- 固定大小的聊天卡片 -->
    <div class="w-full max-w-6xl h-[75vh] bg-slate-900/60 backdrop-blur-sm border border-slate-700/50 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="flex-shrink-0 border-b border-slate-700/50 px-5 py-3 flex items-center gap-3 bg-slate-800/30 rounded-t-2xl">
        <router-link :to="backPath" class="text-slate-400 hover:text-white transition-colors">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
        </router-link>
        <div>
          <h1 class="text-white font-semibold text-sm">模拟面试</h1>
          <p class="text-slate-500 text-xs">
            {{ state === 'READY_CHECK' ? '准备阶段' : state === 'INTERVIEWING' ? '面试中' : '已结束' }}
          </p>
        </div>
      </header>

      <!-- Messages (可滚动区域) -->
      <div ref="chatBox" class="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <div
          v-for="(msg, i) in messages"
          :key="i"
          :class="[
            'flex',
            msg.role === 'candidate' ? 'justify-end' : 'justify-start'
          ]"
        >
          <!-- Interviewer avatar -->
          <div v-if="msg.role === 'interviewer'" class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mr-2 mt-1">
            <span class="text-white text-xs font-bold">官</span>
          </div>

          <div
            :class="[
              'rounded-2xl px-4 py-3 max-w-[75%] text-sm leading-relaxed whitespace-pre-wrap',
              msg.role === 'interviewer'
                ? 'bg-slate-700/80 text-slate-200 rounded-tl-sm'
                : msg.role === 'candidate'
                  ? 'bg-emerald-600 text-white rounded-tr-sm'
                  : 'bg-red-900/50 text-red-300 text-xs'
            ]"
          >
            {{ msg.content }}
          </div>

          <!-- Candidate avatar -->
          <div v-if="msg.role === 'candidate'" class="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0 ml-2 mt-1">
            <span class="text-white text-xs font-bold">我</span>
          </div>
        </div>

        <!-- Typing indicator -->
        <div v-if="sending" class="flex justify-start">
          <div class="bg-slate-700/80 text-slate-400 rounded-2xl rounded-tl-sm px-4 py-3 text-sm">
            <span class="inline-flex gap-1">
              <span class="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
              <span class="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </span>
          </div>
        </div>
      </div>

      <!-- Input (固定在底部) -->
      <footer class="flex-shrink-0 border-t border-slate-700/50 px-4 py-3 bg-slate-800/30 rounded-b-2xl">
        <div class="flex gap-3">
          <textarea
            v-model="input"
            :disabled="state === 'COMPLETED' || sending"
            rows="1"
            placeholder="输入你的回答... (Enter 发送)"
            class="flex-1 rounded-xl bg-slate-800 border border-slate-600 text-white text-sm px-4 py-3 resize-none placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors disabled:opacity-50"
            @keydown="onKeydown"
            @input="e => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px' }"
          ></textarea>
          <button
            :disabled="!input.trim() || sending || state === 'COMPLETED'"
            class="flex-shrink-0 w-11 h-11 rounded-xl bg-emerald-600 text-white hover:bg-emerald-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center"
            @click="sendMessage"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
            </svg>
          </button>
        </div>
        <p v-if="state === 'COMPLETED'" class="text-slate-500 text-xs text-center mt-2">
          面试已结束
          <template v-if="isAdmin">
            ·
            <router-link :to="{ path: '/report', query: { session_id: sessionId } }" class="text-emerald-400 hover:text-emerald-300 font-medium ml-1">查看面试报告</router-link>
          </template>
          ·
          <router-link :to="backPath" class="text-blue-400 hover:text-blue-300 ml-1">返回</router-link>
        </p>
      </footer>
    </div>
  </div>
</template>
