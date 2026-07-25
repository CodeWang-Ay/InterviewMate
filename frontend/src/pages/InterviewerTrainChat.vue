<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const sessionId = ref('')
const loading = ref(true)
const sending = ref(false)
const finishing = ref(false)
const error = ref('')
const input = ref('')
const state = ref('INTERVIEWING')
const history = ref([])
const candidateName = ref('候选人')
const jdName = ref('目标岗位')
const trainingMode = ref('结构化面试')
const candidateStyle = ref('标准型')
const resumeSummary = ref('')
const chatBox = ref(null)

const quickPrompts = computed(() => {
  const presets = {
    '结构化面试': ['先做个和岗位相关的自我介绍', '挑一个最匹配岗位的项目展开讲讲', '这个项目里你负责最核心的一段是什么'],
    '一面能力摸底': ['你为什么想做这个岗位', '你过去做过最接近的事情是什么', '如果今天就入职，你最快能接住什么工作'],
    '二面项目深挖': ['这个项目里最难的问题是什么', '当时为什么这样设计', '结果怎么证明这套方案有效'],
    'HR综合沟通': ['你换工作的核心动机是什么', '你更适合什么样的团队合作方式', '遇到分歧时你通常怎么处理'],
  }
  return presets[trainingMode.value] || presets['结构化面试']
})

const candidateTags = computed(() =>
  resumeSummary.value
    .split('\n')
    .map(item => item.split('：')[1] || item)
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 5),
)

function formatMessageTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

function roleLabel(role) {
  if (role === 'interviewer') return '我'
  if (role === 'candidate') return candidateName.value
  return '系统'
}

function normalizeHistory(items = []) {
  return items.map(item => ({
    ...item,
    timestamp: item.timestamp || item.created_at || '',
  }))
}

async function scrollDown() {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

async function loadSession() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/interviewer-training/session/${sessionId.value}`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '训练会话加载失败')
    history.value = normalizeHistory(data.history || [])
    state.value = data.state || 'INTERVIEWING'
    candidateName.value = data.candidate_name || '候选人'
    jdName.value = data.jd_name || '目标岗位'
    trainingMode.value = data.training_mode || '结构化面试'
    candidateStyle.value = data.candidate_style || '标准型'
    resumeSummary.value = data.resume_summary || ''
    await scrollDown()
  } catch (err) {
    error.value = err.message || '训练会话加载失败'
  } finally {
    loading.value = false
  }
}

async function sendMessage(messageText = '') {
  const text = (messageText || input.value).trim()
  if (!text || sending.value || finishing.value || state.value === 'COMPLETED') return
  history.value.push({ role: 'interviewer', content: text, timestamp: new Date().toISOString() })
  input.value = ''
  sending.value = true
  await scrollDown()

  try {
    const res = await fetch('/api/interviewer-training/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value, message: text }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '发送失败')
    history.value.push({ role: 'candidate', content: data.message, timestamp: new Date().toISOString() })
    state.value = data.state || state.value
    await scrollDown()
  } catch (err) {
    error.value = err.message || '发送失败'
  } finally {
    sending.value = false
  }
}

async function finishTraining() {
  if (finishing.value || state.value === 'COMPLETED') return
  finishing.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/interviewer-training/finish/${sessionId.value}`, { method: 'POST' })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '生成训练报告失败')
    state.value = 'COMPLETED'
    router.push({ path: '/admin/report', query: { session_id: sessionId.value } })
  } catch (err) {
    error.value = err.message || '生成训练报告失败'
  } finally {
    finishing.value = false
  }
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

onMounted(async () => {
  sessionId.value = String(route.query.session_id || '')
  if (!sessionId.value) {
    router.replace('/admin/interviewer')
    return
  }
  await loadSession()
})
</script>

<template>
  <div class="min-h-screen bg-[#f3f7ff] px-6 py-6">
    <div class="mx-auto grid max-w-[1540px] gap-6 xl:grid-cols-[330px_minmax(0,1fr)]">
      <aside class="rounded-[28px] border border-[#d9e6fb] bg-white p-6 shadow-[0_20px_55px_rgba(70,110,190,0.11)]">
        <router-link to="/admin/interviewer" class="inline-flex items-center gap-2 text-sm font-medium text-[#4f6cae] no-underline hover:text-[#214fc5]">
          <i class="fa fa-angle-left"></i>
          返回训练台
        </router-link>

        <div class="mt-6 rounded-[28px] bg-[linear-gradient(145deg,#17305f_0%,#2f6df6_100%)] p-5 text-white">
          <div class="text-sm uppercase tracking-[0.22em] text-white/70">Training Session</div>
          <h1 class="mt-3 text-[30px] font-bold leading-[1.12]">{{ candidateName }}</h1>
          <p class="mt-3 text-sm leading-7 text-white/82">{{ jdName }}</p>
          <div class="mt-5 flex flex-wrap gap-2">
            <span class="rounded-full bg-white/14 px-3 py-1.5 text-xs font-semibold">{{ trainingMode }}</span>
            <span class="rounded-full bg-white/14 px-3 py-1.5 text-xs font-semibold">{{ candidateStyle }}</span>
          </div>
        </div>

        <div class="mt-6 rounded-3xl bg-[#f7faff] p-5">
          <div class="text-sm font-semibold text-[#1b2742]">候选人速览</div>
          <div class="mt-4 flex flex-wrap gap-2">
            <span v-for="item in candidateTags" :key="item" class="rounded-full border border-[#d7e5ff] bg-white px-3 py-1.5 text-sm text-[#56657f]">
              {{ item }}
            </span>
            <span v-if="!candidateTags.length" class="text-sm text-[#7e8aa3]">暂无候选人画像</span>
          </div>
        </div>

        <div class="mt-6 rounded-3xl border border-[#d9e6fb] bg-white p-5">
          <div class="text-sm font-semibold text-[#1b2742]">建议起手问题</div>
          <div class="mt-4 space-y-3">
            <button
              v-for="prompt in quickPrompts"
              :key="prompt"
              type="button"
              class="w-full rounded-2xl bg-[#f7faff] px-4 py-3 text-left text-sm leading-6 text-[#556580] transition hover:bg-[#eef4ff]"
              @click="sendMessage(prompt)"
            >
              {{ prompt }}
            </button>
          </div>
        </div>

        <button
          :disabled="finishing"
          class="mt-6 flex w-full items-center justify-center gap-3 rounded-2xl bg-[#17305f] px-4 py-4 text-base font-semibold text-white transition hover:bg-[#26447e] disabled:opacity-55"
          @click="finishTraining"
        >
          <i class="fa fa-bar-chart"></i>
          {{ finishing ? '正在生成训练复盘...' : '结束训练并生成复盘' }}
        </button>
      </aside>

      <section class="min-h-[82vh] rounded-[28px] border border-[#d9e6fb] bg-white shadow-[0_20px_55px_rgba(70,110,190,0.11)]">
        <header class="flex flex-wrap items-center justify-between gap-4 border-b border-[#e7eefb] px-7 py-5">
          <div>
            <div class="text-sm font-medium text-[#3970e9]">Live Conversation</div>
            <h2 class="mt-1 text-[28px] font-bold text-[#15213f]">面试官实战对练</h2>
          </div>
          <div class="flex items-center gap-3">
            <span :class="state === 'COMPLETED' ? 'bg-[#ecfdf3] text-[#27734a]' : 'bg-[#eef4ff] text-[#2f6df6]'" class="rounded-full px-4 py-2 text-sm font-semibold">
              {{ state === 'COMPLETED' ? '已结束' : '训练进行中' }}
            </span>
            <button class="rounded-full border border-[#d8e4ff] bg-white px-4 py-2 text-sm font-medium text-[#47556f] transition hover:border-[#97b5ff] hover:text-[#2454d0]" @click="loadSession">
              刷新对话
            </button>
          </div>
        </header>

        <div v-if="error" class="mx-7 mt-5 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-600">
          {{ error }}
        </div>

        <div v-if="loading" class="flex min-h-[60vh] flex-col items-center justify-center text-[#7e8aa3]">
          <div class="h-10 w-10 animate-spin rounded-full border-2 border-[#8fb0ff] border-t-transparent"></div>
          <p class="mt-4 text-sm">正在载入训练会话...</p>
        </div>

        <template v-else>
          <div ref="chatBox" class="h-[calc(82vh-185px)] overflow-y-auto px-7 py-6">
            <div class="mx-auto max-w-4xl space-y-5">
              <div
                v-for="(msg, index) in history"
                :key="`${msg.role}-${index}-${msg.timestamp || index}`"
                :class="['flex', msg.role === 'interviewer' ? 'justify-end' : 'justify-start']"
              >
                <div :class="['max-w-[78%]', msg.role === 'interviewer' ? 'items-end' : 'items-start']" class="flex flex-col">
                  <div class="mb-2 flex items-center gap-3 px-1" :class="msg.role === 'interviewer' ? 'justify-end' : 'justify-start'">
                    <div class="text-[15px] font-semibold text-[#22304b]">{{ roleLabel(msg.role) }}</div>
                    <div class="text-[13px] font-medium text-[#8a96ac]">{{ formatMessageTime(msg.timestamp) }}</div>
                  </div>
                  <div
                    :class="[
                      'rounded-[22px] px-5 py-4 text-[15px] leading-8 shadow-sm',
                      msg.role === 'candidate'
                        ? 'bg-[#f6f8fc] text-[#25314a] rounded-tl-[8px] border border-[#e4ebf8]'
                        : msg.role === 'interviewer'
                          ? 'bg-[linear-gradient(135deg,#17305f_0%,#2f6df6_100%)] text-white rounded-tr-[8px]'
                          : 'bg-[#fff4eb] text-[#8a4b19] border border-[#ffe0c8]'
                    ]"
                  >
                    {{ msg.content }}
                  </div>
                </div>
              </div>

              <div v-if="sending" class="flex justify-start">
                <div class="rounded-[22px] border border-[#e4ebf8] bg-[#f6f8fc] px-5 py-4 text-sm text-[#7f8ca5]">
                  <span class="inline-flex gap-1.5">
                    <span class="h-2 w-2 animate-bounce rounded-full bg-[#95a8cb]" style="animation-delay: 0ms"></span>
                    <span class="h-2 w-2 animate-bounce rounded-full bg-[#95a8cb]" style="animation-delay: 120ms"></span>
                    <span class="h-2 w-2 animate-bounce rounded-full bg-[#95a8cb]" style="animation-delay: 240ms"></span>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <footer class="border-t border-[#e7eefb] px-7 py-5">
            <div class="mx-auto max-w-4xl">
              <div class="rounded-[28px] border border-[#d8e5fb] bg-[#f8fbff] p-3">
                <div class="flex items-end gap-3">
                  <textarea
                    v-model="input"
                    rows="1"
                    :disabled="sending || finishing || state === 'COMPLETED'"
                    placeholder="输入你的面试问题，Enter 发送，Shift + Enter 换行"
                    class="min-h-[62px] flex-1 resize-none bg-transparent px-4 py-3 text-[15px] leading-7 text-[#1e2b45] placeholder:text-[#98a5bb] focus:outline-none disabled:opacity-60"
                    @keydown="onKeydown"
                    @input="event => { event.target.style.height = 'auto'; event.target.style.height = `${Math.min(event.target.scrollHeight, 220)}px` }"
                  ></textarea>
                  <button
                    :disabled="!input.trim() || sending || finishing || state === 'COMPLETED'"
                    class="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#2f6df6] text-white transition hover:bg-[#225ad2] disabled:opacity-45"
                    @click="sendMessage()"
                  >
                    <i class="fa fa-send-o text-lg"></i>
                  </button>
                </div>
              </div>
              <p class="mt-3 text-sm text-[#8a96ac]">
                这轮训练里，AI 会始终按候选人身份回答。你可以重点练岗位贴合、追问深度和案例挖掘。
              </p>
            </div>
          </footer>
        </template>
      </section>
    </div>
  </div>
</template>
