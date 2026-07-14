<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isOpen = ref(false)
const isExpanded = ref(false)
const loading = ref(false)
const input = ref('')
const messages = ref([])
const scrollBox = ref(null)
const floatingShell = ref(null)
const dragState = ref({
  active: false,
  pointerId: null,
  startX: 0,
  startY: 0,
  originX: 0,
  originY: 0,
  moved: false,
})
const suppressBubbleClick = ref(false)
const floatingPosition = ref({ x: 0, y: 0, ready: false })

const hiddenPaths = ['/login', '/user/login', '/register']
const isVisible = computed(() => !hiddenPaths.includes(route.path))
const floatingStyle = computed(() => {
  if (isExpanded.value || !floatingPosition.value.ready) return {}
  return {
    left: `${floatingPosition.value.x}px`,
    top: `${floatingPosition.value.y}px`,
  }
})

const currentRole = computed(() => {
  try {
    return window.localStorage?.getItem('role') || 'guest'
  } catch (_) {
    return 'guest'
  }
})

const storageKey = computed(() => `ai-assistant-history:${currentRole.value}`)
const positionStorageKey = 'ai-assistant-floating-position'
const panelTitle = computed(() => currentRole.value === 'candidate' ? '面试者 AI 助手' : 'AI 聊天助手')
const panelSubtitle = computed(() => currentRole.value === 'candidate' ? '聊聊天，或者问问当前面试与流程问题。' : '平时闲聊、梳理想法、顺手问系统问题都可以。')
const decoder = new TextDecoder('utf-8')
const quickPrompts = computed(() => currentRole.value === 'candidate'
  ? ['我现在这轮面试该怎么准备', '帮我整理下一个自我介绍', '我有点紧张，陪我聊两句']
  : ['帮我想几个一面追问', '这份 JD 应该重点考什么', '今天有点累，陪我随便聊聊'])

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderInlineMarkdown(text) {
  let html = escapeHtml(text)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
  html = html.replace(/\n/g, '<br>')
  return html
}

function renderMarkdown(content) {
  const source = String(content || '')
  if (!source.trim()) return ''

  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let paragraph = []
  let listItems = []
  let inCodeBlock = false
  let codeLines = []

  const flushParagraph = () => {
    if (!paragraph.length) return
    blocks.push(`<p>${renderInlineMarkdown(paragraph.join('\n'))}</p>`)
    paragraph = []
  }

  const flushList = () => {
    if (!listItems.length) return
    blocks.push(`<ul>${listItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`)
    listItems = []
  }

  const flushCode = () => {
    if (!codeLines.length) return
    blocks.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
    codeLines = []
  }

  for (const rawLine of lines) {
    const line = rawLine ?? ''

    if (line.trim().startsWith('```')) {
      flushParagraph()
      flushList()
      if (inCodeBlock) {
        flushCode()
        inCodeBlock = false
      } else {
        inCodeBlock = true
      }
      continue
    }

    if (inCodeBlock) {
      codeLines.push(line)
      continue
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      const level = Math.min(headingMatch[1].length, 4)
      blocks.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`)
      continue
    }

    const listMatch = line.match(/^\s*[-*]\s+(.+)$/)
    if (listMatch) {
      flushParagraph()
      listItems.push(listMatch[1])
      continue
    }

    if (!line.trim()) {
      flushParagraph()
      flushList()
      continue
    }

    flushList()
    paragraph.push(line)
  }

  if (inCodeBlock) flushCode()
  flushParagraph()
  flushList()
  return blocks.join('')
}

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

async function copyMessage(content) {
  const text = String(content || '').trim()
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
  } catch (_) {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', 'true')
    textarea.style.position = 'absolute'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  }
}

function closePanel() {
  isOpen.value = false
  isExpanded.value = false
}

function toggleExpanded() {
  isExpanded.value = !isExpanded.value
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

function saveFloatingPosition() {
  try {
    if (!floatingPosition.value.ready) return
    window.localStorage?.setItem(positionStorageKey, JSON.stringify({
      x: floatingPosition.value.x,
      y: floatingPosition.value.y,
    }))
  } catch (_) {
    // ignore
  }
}

function clampFloatingPosition(x, y) {
  const shell = floatingShell.value
  const width = shell?.offsetWidth || 320
  const height = shell?.offsetHeight || 72
  const maxX = Math.max(16, window.innerWidth - width - 16)
  const maxY = Math.max(16, window.innerHeight - height - 16)
  return {
    x: Math.min(Math.max(16, x), maxX),
    y: Math.min(Math.max(16, y), maxY),
  }
}

function ensureFloatingPosition() {
  if (isExpanded.value) return
  let next = null
  if (!floatingPosition.value.ready) {
    try {
      const raw = window.localStorage?.getItem(positionStorageKey)
      next = raw ? JSON.parse(raw) : null
    } catch (_) {
      next = null
    }
  } else {
    next = floatingPosition.value
  }

  const fallbackWidth = 320
  const fallbackHeight = 72
  const baseX = typeof next?.x === 'number' ? next.x : window.innerWidth - fallbackWidth - 20
  const baseY = typeof next?.y === 'number' ? next.y : window.innerHeight - fallbackHeight - 20
  const clamped = clampFloatingPosition(baseX, baseY)
  floatingPosition.value = { ...clamped, ready: true }
  saveFloatingPosition()
}

function stopDrag() {
  dragState.value = {
    active: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    originX: 0,
    originY: 0,
    moved: false,
  }
}

function onDragPointerDown(event) {
  if (isExpanded.value || event.button !== 0) return
  ensureFloatingPosition()
  dragState.value = {
    active: true,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: floatingPosition.value.x,
    originY: floatingPosition.value.y,
    moved: false,
  }
  event.currentTarget?.setPointerCapture?.(event.pointerId)
}

function onDragPointerMove(event) {
  if (!dragState.value.active || dragState.value.pointerId !== event.pointerId || isExpanded.value) return
  const dx = event.clientX - dragState.value.startX
  const dy = event.clientY - dragState.value.startY
  if (!dragState.value.moved && (Math.abs(dx) > 4 || Math.abs(dy) > 4)) {
    dragState.value.moved = true
  }
  const next = clampFloatingPosition(dragState.value.originX + dx, dragState.value.originY + dy)
  floatingPosition.value = { ...next, ready: true }
}

function onDragPointerUp(event) {
  if (dragState.value.pointerId !== event.pointerId) return
  suppressBubbleClick.value = dragState.value.moved
  saveFloatingPosition()
  stopDrag()
}

function toggleOpenFromBubble() {
  if (suppressBubbleClick.value) {
    suppressBubbleClick.value = false
    return
  }
  isOpen.value = !isOpen.value
}

function handleWindowResize() {
  if (!floatingPosition.value.ready || isExpanded.value) return
  ensureFloatingPosition()
}

watch(storageKey, () => {
  loadHistory()
})

watch(isOpen, async (value) => {
  if (value) {
    loadHistory()
    await scrollToBottom()
  } else {
    isExpanded.value = false
  }
})

onMounted(() => {
  loadHistory()
  nextTick(() => ensureFloatingPosition())
  window.addEventListener('resize', handleWindowResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWindowResize)
})
</script>

<template>
  <div
    v-if="isVisible"
    ref="floatingShell"
    :class="isExpanded ? 'fixed inset-0 z-[80]' : 'fixed z-[70]'"
    :style="floatingStyle"
  >
    <div
      v-if="isOpen && isExpanded"
      class="absolute inset-0 bg-[rgba(12,22,42,0.20)]"
    ></div>

    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-3 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-2 scale-95"
    >
      <div
        v-if="isOpen"
        :class="[
          'overflow-hidden border border-[#d8e6ff] bg-white shadow-[0_30px_80px_rgba(27,61,139,0.20)]',
          isExpanded
            ? 'absolute inset-0 flex h-screen w-screen rounded-none border-0'
            : 'absolute bottom-[calc(100%+16px)] left-0 w-[380px] max-w-[calc(100vw-24px)] rounded-[30px]'
        ]"
      >
        <div v-if="isExpanded" class="hidden w-[320px] flex-col border-r border-[#e7eefc] bg-[linear-gradient(180deg,#f8fbff_0%,#edf4ff_100%)] xl:flex">
          <div class="border-b border-[#e3edff] px-6 py-6">
            <div class="inline-flex items-center gap-2 rounded-full bg-[#17305f] px-3 py-1.5 text-xs font-semibold tracking-[0.08em] text-white">
              <span class="h-2 w-2 rounded-full bg-emerald-300"></span>
              CHAT MODE
            </div>
            <h3 class="mt-4 text-[26px] font-bold text-[#18233e]">{{ panelTitle }}</h3>
            <p class="mt-2 text-sm leading-7 text-[#62718c]">{{ panelSubtitle }}</p>
          </div>

          <div class="px-6 py-6">
            <div class="text-sm font-semibold text-[#1d2941]">可以直接这样开聊</div>
            <div class="mt-4 space-y-3">
              <button
                v-for="prompt in quickPrompts"
                :key="prompt"
                type="button"
                class="w-full rounded-2xl border border-[#d8e5fb] bg-white px-4 py-3 text-left text-sm leading-6 text-[#56657f] transition hover:border-[#98b8ff] hover:bg-[#f8fbff]"
                @click="input = prompt"
              >
                {{ prompt }}
              </button>
            </div>
          </div>

          <div class="mt-auto border-t border-[#e3edff] px-6 py-5">
            <div class="rounded-2xl bg-white px-4 py-4 shadow-sm">
              <div class="text-sm font-semibold text-[#1d2941]">聊天记录</div>
              <p class="mt-2 text-sm leading-6 text-[#7785a0]">当前会按角色保存在本地，刷新页面不会立刻丢。后面我们也可以继续升级成服务端会话历史。</p>
            </div>
          </div>
        </div>

        <div :class="isExpanded ? 'flex min-w-0 flex-1 flex-col' : ''">
        <div
          :class="[
            'bg-[linear-gradient(135deg,#17305f_0%,#2f6df6_100%)] px-5 py-5 text-white',
            isExpanded ? '' : 'cursor-grab active:cursor-grabbing select-none'
          ]"
          @pointerdown="onDragPointerDown"
          @pointermove="onDragPointerMove"
          @pointerup="onDragPointerUp"
          @pointercancel="onDragPointerUp"
        >
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="inline-flex items-center gap-2 rounded-full bg-white/14 px-3 py-1.5 text-xs font-semibold tracking-[0.08em] text-white/92">
                <span class="h-2 w-2 rounded-full bg-emerald-300"></span>
                AI ASSISTANT
              </div>
              <h3 class="mt-3 text-[22px] font-bold">{{ panelTitle }}</h3>
              <p class="mt-1 text-sm leading-6 text-white/80">{{ panelSubtitle }}</p>
            </div>
            <div class="flex items-center gap-2">
              <button
                class="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/12 text-white transition hover:bg-white/18"
                :title="isExpanded ? '退出全屏' : '展开全屏'"
                @click="toggleExpanded"
              >
                <i :class="['fa text-base', isExpanded ? 'fa-compress' : 'fa-expand']"></i>
              </button>
              <button class="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/12 text-white transition hover:bg-white/18" title="收起助手" @click="closePanel">
                <i :class="['fa', isExpanded ? 'fa-times' : 'fa-angle-down', isExpanded ? 'text-base' : 'text-lg']"></i>
              </button>
            </div>
          </div>
        </div>

        <div
          ref="scrollBox"
          :class="[
            'overflow-y-auto bg-[#f7faff] px-4 py-4',
            isExpanded ? 'flex-1 px-6 py-6' : 'h-[420px]'
          ]"
        >
          <div class="space-y-4">
            <div v-for="item in messages" :key="item.id" :class="['flex', item.role === 'user' ? 'justify-end' : 'justify-start']">
              <div :class="[isExpanded ? 'max-w-[78%]' : 'max-w-[82%]', 'flex flex-col', item.role === 'user' ? 'items-end' : 'items-start']">
                <div class="mb-1.5 flex items-center gap-2 px-1 text-[12px] font-medium text-[#8b98af]">
                  <span>{{ item.role === 'user' ? '你' : '助手' }} · {{ formatTime(item.timestamp) }}</span>
                  <button
                    class="rounded-lg px-2 py-1 text-[11px] text-[#7b89a4] transition hover:bg-[#e9f0ff] hover:text-[#2f6df6]"
                    title="复制内容"
                    @click="copyMessage(item.content)"
                  >
                    复制
                  </button>
                </div>
                <div
                  :class="[
                    'group relative rounded-[22px] px-4 py-3 shadow-sm',
                    isExpanded ? 'text-[15px] leading-8' : 'text-[14px] leading-7',
                    item.role === 'user'
                      ? 'rounded-tr-[8px] bg-[linear-gradient(135deg,#17305f_0%,#2f6df6_100%)] text-white'
                      : 'rounded-tl-[8px] border border-[#dfe9fb] bg-white text-[#26324a]'
                  ]"
                >
                  <button
                    class="absolute right-3 top-3 inline-flex h-8 items-center justify-center rounded-xl border border-white/20 bg-white/10 px-2 text-[11px] text-white opacity-0 transition group-hover:opacity-100"
                    v-if="item.role === 'user'"
                    title="复制内容"
                    @click="copyMessage(item.content)"
                  >
                    复制
                  </button>
                  <button
                    class="absolute right-3 top-3 inline-flex h-8 items-center justify-center rounded-xl border border-[#d8e5fb] bg-white px-2 text-[11px] text-[#6481c3] opacity-0 transition group-hover:opacity-100"
                    v-else
                    title="复制内容"
                    @click="copyMessage(item.content)"
                  >
                    复制
                  </button>
                  <div
                    v-if="item.role === 'assistant'"
                    class="assistant-markdown"
                    v-html="renderMarkdown(item.content)"
                  ></div>
                  <div v-else class="whitespace-pre-wrap break-words">{{ item.content }}</div>
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

        <div :class="['border-t border-[#e6eefc] bg-white', isExpanded ? 'px-6 py-5' : 'px-4 py-4']">
          <div :class="['rounded-[24px] border border-[#d8e5fb] bg-[#f8fbff] p-3', isExpanded ? 'shadow-sm' : '']">
            <div class="flex items-end gap-3">
              <textarea
                v-model="input"
                rows="1"
                :disabled="loading"
                placeholder="跟 AI 助手聊点什么..."
                :class="[
                  'flex-1 resize-none bg-transparent px-3 py-2 text-[#1d2941] placeholder:text-[#9aa7bc] focus:outline-none disabled:opacity-60',
                  isExpanded ? 'min-h-[64px] text-[15px] leading-8' : 'min-h-[52px] text-[14px] leading-7'
                ]"
                @keydown="onKeydown"
                @input="event => { event.target.style.height = 'auto'; event.target.style.height = `${Math.min(event.target.scrollHeight, 180)}px` }"
              ></textarea>
              <button
                :disabled="!input.trim() || loading"
                :class="[
                  'flex items-center justify-center rounded-2xl bg-[#2f6df6] text-white transition hover:bg-[#225ad2] disabled:opacity-45',
                  isExpanded ? 'h-14 w-14' : 'h-12 w-12'
                ]"
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
      </div>
    </transition>

    <button
      v-if="!isExpanded"
      class="group flex h-16 items-center gap-3 rounded-full border border-[#d7e4ff] bg-white px-4 pr-5 shadow-[0_20px_50px_rgba(33,84,197,0.18)] transition hover:translate-y-[-1px] hover:shadow-[0_24px_60px_rgba(33,84,197,0.22)] select-none"
      :class="dragState.active ? 'cursor-grabbing' : 'cursor-grab'"
      @pointerdown="onDragPointerDown"
      @pointermove="onDragPointerMove"
      @pointerup="onDragPointerUp"
      @pointercancel="onDragPointerUp"
      @click="toggleOpenFromBubble"
    >
      <span class="flex h-11 w-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,#17305f_0%,#2f6df6_100%)] text-white shadow-sm">
        <i class="fa fa-commenting-o text-lg"></i>
      </span>
      <span class="flex flex-col items-start">
        <span class="text-sm font-semibold text-[#1f2b45]">AI 助手</span>
        <span class="text-xs text-[#8e9bb0]">{{ isOpen ? '收起聊天窗口' : '点我随便聊聊' }}</span>
      </span>
      <span class="ml-1 flex h-9 w-9 items-center justify-center rounded-full bg-[#f5f8ff] text-[#6d7fa2]">
        <i class="fa fa-arrows text-sm"></i>
      </span>
    </button>
  </div>
</template>

<style scoped>
.assistant-markdown {
  word-break: break-word;
}

.assistant-markdown :deep(p) {
  margin: 0;
}

.assistant-markdown :deep(p + p),
.assistant-markdown :deep(p + ul),
.assistant-markdown :deep(ul + p),
.assistant-markdown :deep(pre + p),
.assistant-markdown :deep(h1 + p),
.assistant-markdown :deep(h2 + p),
.assistant-markdown :deep(h3 + p),
.assistant-markdown :deep(h4 + p) {
  margin-top: 10px;
}

.assistant-markdown :deep(h1),
.assistant-markdown :deep(h2),
.assistant-markdown :deep(h3),
.assistant-markdown :deep(h4) {
  margin: 0;
  font-weight: 700;
  line-height: 1.5;
}

.assistant-markdown :deep(h1) {
  font-size: 1.15em;
}

.assistant-markdown :deep(h2) {
  font-size: 1.08em;
}

.assistant-markdown :deep(h3),
.assistant-markdown :deep(h4) {
  font-size: 1em;
}

.assistant-markdown :deep(ul) {
  margin: 10px 0 0;
  padding-left: 1.2em;
}

.assistant-markdown :deep(li + li) {
  margin-top: 6px;
}

.assistant-markdown :deep(code) {
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.08);
  padding: 2px 6px;
  font-size: 0.92em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.assistant-markdown :deep(pre) {
  margin: 10px 0 0;
  overflow-x: auto;
  border-radius: 14px;
  background: #0f172a;
  padding: 12px 14px;
}

.assistant-markdown :deep(pre code) {
  background: transparent;
  padding: 0;
  color: #e2e8f0;
  font-size: 0.9em;
  line-height: 1.7;
}

.assistant-markdown :deep(a) {
  color: #2563eb;
  text-decoration: none;
  font-weight: 600;
}

.assistant-markdown :deep(a:hover) {
  text-decoration: underline;
}
</style>
