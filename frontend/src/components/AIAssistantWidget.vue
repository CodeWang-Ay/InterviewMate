<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isOpen = ref(false)
const loading = ref(false)
const input = ref('')
const messages = ref([])
const scrollBox = ref(null)

const hiddenPaths = ['/login', '/user/login', '/register']
const isVisible = computed(() => !hiddenPaths.includes(route.path))

const currentRole = computed(() => {
  try {
    return window.localStorage?.getItem('role') || 'guest'
  } catch (_) {
    return 'guest'
  }
})

const storageKey = computed(() => `ai-assistant-history:${currentRole.value}`)
const panelTitle = computed(() => currentRole.value === 'candidate' ? '面试者 AI 助手' : 'AI 聊天助手')
const panelSubtitle = computed(() => currentRole.value === 'candidate' ? '聊聊天，或者问问当前面试与流程问题。' : '平时闲聊、梳理想法、顺手问系统问题都可以。')
const decoder = new TextDecoder('utf-8')

function createMessage(role, content) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    role,
    content,
    timestamp: new Date().toISOString(),
  }
}

function safeReadHistory() {
  try {
    const raw = window.localStorage?.getItem(storageKey.value)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch (_) {
    return []
  }
}

function saveHistory() {
  try {
    window.localStorage?.setItem(storageKey.value, JSON.stringify(messages.value.slice(-30)))
  } catch (_) {
    // ignore
  }
}

function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function scrollToBottom() {
  await nextTick()
  if (scrollBox.value) scrollBox.value.scrollTop = scrollBox.value.scrollHeight
}

function ensureSeedMessage() {
  if (messages.value.length) return
  messages.value = [
    createMessage(
      'assistant',
      currentRole.value === 'candidate'
        ? '你好呀，我是你的 AI 助手。你可以跟我闲聊，也可以问我当前面试流程、进度或者想法整理。'
        : '你好，我在这儿。你可以把我当成一个随手能聊的 AI 助手，平时闲聊、梳理招聘思路、拆问题都可以。'
    ),
  ]
  saveHistory()
}

function loadHistory() {
  messages.value = safeReadHistory()
  ensureSeedMessage()
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push(createMessage('user', text))
  input.value = ''
  saveHistory()
  loading.value = true
  await scrollToBottom()

  try {
    const historyPayload = messages.value.slice(-12).map(item => ({
      role: item.role === 'user' ? 'user' : 'assistant',
      content: item.content,
    }))
    const assistantMessage = createMessage('assistant', '')
    messages.value.push(assistantMessage)
    await scrollToBottom()

    const res = await fetch('/api/assistant/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: historyPayload }),
    })
    if (!res.ok) {
      let errText = '助手暂时没接上'
      try {
        const data = await res.json()
        errText = data.detail || errText
      } catch (_) {
        // ignore
      }
      throw new Error(errText)
    }

    const reader = res.body?.getReader()
    if (!reader) throw new Error('当前浏览器不支持流式响应')

    let fullText = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      if (!chunk) continue
      fullText += chunk
      assistantMessage.content = fullText
      assistantMessage.timestamp = new Date().toISOString()
      messages.value = [...messages.value]
      await scrollToBottom()
    }

    assistantMessage.content = assistantMessage.content || '我刚刚走神了一下，你再说一遍也行。'
  } catch (err) {
    if (messages.value[messages.value.length - 1]?.role === 'assistant' && !messages.value[messages.value.length - 1]?.content) {
      messages.value.pop()
    }
    messages.value.push(createMessage('assistant', err.message || '助手暂时没接上'))
  } finally {
    loading.value = false
    saveHistory()
    await scrollToBottom()
  }
}

function clearChat() {
  messages.value = []
  ensureSeedMessage()
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

watch(storageKey, () => {
  loadHistory()
})

watch(isOpen, async (value) => {
  if (value) {
    loadHistory()
    await scrollToBottom()
  }
})

onMounted(() => {
  loadHistory()
})
</script>

<template>
  <div v-if="isVisible" class="fixed bottom-5 right-5 z-[70]">
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-3 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-2 scale-95"
    >
      <div v-if="isOpen" class="mb-4 w-[380px] max-w-[calc(100vw-24px)] overflow-hidden rounded-[30px] border border-[#d8e6ff] bg-white shadow-[0_30px_80px_rgba(27,61,139,0.20)]">
        <div class="bg-[linear-gradient(135deg,#17305f_0%,#2f6df6_100%)] px-5 py-5 text-white">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="inline-flex items-center gap-2 rounded-full bg-white/14 px-3 py-1.5 text-xs font-semibold tracking-[0.08em] text-white/92">
                <span class="h-2 w-2 rounded-full bg-emerald-300"></span>
                AI ASSISTANT
              </div>
              <h3 class="mt-3 text-[22px] font-bold">{{ panelTitle }}</h3>
              <p class="mt-1 text-sm leading-6 text-white/80">{{ panelSubtitle }}</p>
            </div>
            <button class="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/12 text-white transition hover:bg-white/18" title="收起助手" @click="isOpen = false">
              <i class="fa fa-angle-down text-lg"></i>
            </button>
          </div>
        </div>

        <div ref="scrollBox" class="h-[420px] overflow-y-auto bg-[#f7faff] px-4 py-4">
          <div class="space-y-4">
            <div v-for="item in messages" :key="item.id" :class="['flex', item.role === 'user' ? 'justify-end' : 'justify-start']">
              <div :class="['max-w-[82%] flex flex-col', item.role === 'user' ? 'items-end' : 'items-start']">
                <div class="mb-1.5 px-1 text-[12px] font-medium text-[#8b98af]">{{ item.role === 'user' ? '你' : '助手' }} · {{ formatTime(item.timestamp) }}</div>
                <div
                  :class="[
                    'rounded-[22px] px-4 py-3 text-[14px] leading-7 shadow-sm',
                    item.role === 'user'
                      ? 'rounded-tr-[8px] bg-[linear-gradient(135deg,#17305f_0%,#2f6df6_100%)] text-white'
                      : 'rounded-tl-[8px] border border-[#dfe9fb] bg-white text-[#26324a]'
                  ]"
                >
                  {{ item.content }}
                </div>
              </div>
            </div>

            <div v-if="loading && !messages[messages.length - 1]?.content" class="flex justify-start">
              <div class="rounded-[22px] rounded-tl-[8px] border border-[#dfe9fb] bg-white px-4 py-3 text-sm text-[#8b98af]">
                <span class="inline-flex gap-1.5">
                  <span class="h-2 w-2 animate-bounce rounded-full bg-[#93a6c9]" style="animation-delay: 0ms"></span>
                  <span class="h-2 w-2 animate-bounce rounded-full bg-[#93a6c9]" style="animation-delay: 120ms"></span>
                  <span class="h-2 w-2 animate-bounce rounded-full bg-[#93a6c9]" style="animation-delay: 240ms"></span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="border-t border-[#e6eefc] bg-white px-4 py-4">
          <div class="rounded-[24px] border border-[#d8e5fb] bg-[#f8fbff] p-3">
            <div class="flex items-end gap-3">
              <textarea
                v-model="input"
                rows="1"
                :disabled="loading"
                placeholder="跟 AI 助手聊点什么..."
                class="min-h-[52px] flex-1 resize-none bg-transparent px-3 py-2 text-[14px] leading-7 text-[#1d2941] placeholder:text-[#9aa7bc] focus:outline-none disabled:opacity-60"
                @keydown="onKeydown"
                @input="event => { event.target.style.height = 'auto'; event.target.style.height = `${Math.min(event.target.scrollHeight, 180)}px` }"
              ></textarea>
              <button
                :disabled="!input.trim() || loading"
                class="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#2f6df6] text-white transition hover:bg-[#225ad2] disabled:opacity-45"
                title="发送"
                @click="sendMessage"
              >
                <i class="fa fa-send-o"></i>
              </button>
            </div>
          </div>

            <div class="mt-3 flex items-center justify-between">
              <button class="text-sm font-medium text-[#7c89a2] transition hover:text-[#2f6df6]" @click="clearChat">清空聊天</button>
            <div class="text-[12px] text-[#9aa7bc]">{{ loading ? '流式生成中...' : 'Enter 发送' }}</div>
          </div>
        </div>
      </div>
    </transition>

    <button
      class="group flex h-16 items-center gap-3 rounded-full border border-[#d7e4ff] bg-white px-4 pr-5 shadow-[0_20px_50px_rgba(33,84,197,0.18)] transition hover:translate-y-[-1px] hover:shadow-[0_24px_60px_rgba(33,84,197,0.22)]"
      @click="isOpen = !isOpen"
    >
      <span class="flex h-11 w-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,#17305f_0%,#2f6df6_100%)] text-white shadow-sm">
        <i class="fa fa-commenting-o text-lg"></i>
      </span>
      <span class="flex flex-col items-start">
        <span class="text-sm font-semibold text-[#1f2b45]">AI 助手</span>
        <span class="text-xs text-[#8e9bb0]">{{ isOpen ? '收起聊天窗口' : '点我随便聊聊' }}</span>
      </span>
    </button>
  </div>
</template>
