<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const route = useRoute()
const report = ref(null)
const history = ref([])
const loading = ref(true)
const chatBox = ref(null)

const candidateName = computed(() => report.value?.candidate_name || report.value?.resume_name || report.value?.candidate_username || '未知候选人')
const jobName = computed(() => report.value?.jd_name || report.value?.report_title || '未知岗位')
const interviewerName = computed(() => report.value?.interviewer || '未指定')
const roundName = computed(() => report.value?.interview_round || (report.value?.stage_order ? `第 ${report.value.stage_order} 面` : '未设置'))
const roundSummary = computed(() => {
  const current = Number(report.value?.stage_order || 0)
  const total = Number(report.value?.stage_count || 0)
  if (current && total) return `${roundName.value} · ${current}/${total}`
  return roundName.value
})
const interviewerCount = computed(() => history.value.filter(item => item.role !== 'candidate').length)
const candidateCount = computed(() => history.value.filter(item => item.role === 'candidate').length)

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
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mi = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}:${ss}`
}

function roleLabel(role) {
  if (role === 'candidate') return '候选人'
  if (role === 'trainer') return '训练反馈'
  return report.value?.report_type === 'interviewer_training' ? '候选人模拟' : '面试官'
}

function roleShort(role) {
  if (role === 'candidate') return '我'
  if (role === 'trainer') return '评'
  return '官'
}

onMounted(async () => {
  const sid = route.query.session_id
  if (!sid) { loading.value = false; return }
  try {
    const res = await fetch(`/api/report/${sid}`)
    if (res.ok) {
      const data = await res.json()
      report.value = data
      history.value = Array.isArray(data.history) ? data.history.map(withTimestamp) : []
    }
  } catch (_) { /* ignore */ }
  loading.value = false
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
})
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-[#eef2ff] text-slate-900">
    <Sidebar />

    <main class="flex-1 overflow-y-auto px-6 py-8">
        <div class="mx-auto grid h-full max-w-[1620px] grid-cols-1 gap-6 xl:grid-cols-[400px_minmax(0,1fr)]">
        <aside class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-indigo-100/80">
          <router-link to="/admin/interview-archive" class="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-indigo-600 no-underline">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            返回档案
          </router-link>

          <div class="mt-8">
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
              <svg class="h-9 w-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm3.75 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm3.75 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 12c0 4.142-4.03 7.5-9 7.5a10.5 10.5 0 0 1-3.151-.477L3 21l1.58-4.214A6.9 6.9 0 0 1 3 12c0-4.142 4.03-7.5 9-7.5s9 3.358 9 7.5Z" />
              </svg>
            </div>
            <p class="mt-5 text-xs font-bold uppercase tracking-[0.2em] text-indigo-400">Interview record</p>
            <h1 class="mt-2 text-2xl font-bold text-slate-950">面试记录</h1>
            <p class="mt-2 text-sm leading-6 text-slate-500">完整对话回顾，按时间线保留每一次提问与回答。</p>
          </div>

          <div class="mt-8 space-y-3">
            <div class="rounded-2xl bg-slate-50 p-4">
              <p class="text-xs font-semibold text-slate-400">候选人</p>
              <p class="mt-1 truncate text-base font-bold text-slate-900">{{ candidateName }}</p>
            </div>
            <div class="rounded-2xl bg-slate-50 p-4">
              <p class="text-xs font-semibold text-slate-400">岗位</p>
              <p class="mt-1 line-clamp-2 text-base font-bold text-slate-900">{{ jobName }}</p>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="rounded-2xl bg-indigo-50 p-4">
                <p class="text-xs font-semibold text-indigo-400">面试官</p>
                  <p class="mt-1 text-base font-bold leading-6 text-indigo-700">{{ interviewerName }}</p>
              </div>
              <div class="rounded-2xl bg-violet-50 p-4">
                <p class="text-xs font-semibold text-violet-400">面试轮次</p>
                  <p class="mt-1 text-base font-bold leading-6 text-violet-700">{{ roundSummary }}</p>
              </div>
            </div>
          </div>

          <div class="mt-6 grid grid-cols-3 gap-3">
            <div class="rounded-2xl bg-indigo-50 p-3 text-center">
              <p class="text-lg font-black text-indigo-600">{{ history.length }}</p>
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

          <router-link
            :to="{ path: '/admin/report', query: { session_id: route.query.session_id } }"
            class="mt-8 flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm shadow-indigo-200 hover:bg-indigo-700 no-underline"
          >
            查看面试报告
          </router-link>
        </aside>

        <section class="flex min-h-0 flex-col overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-indigo-100/80">
          <header class="flex flex-shrink-0 items-center justify-between border-b border-slate-100 px-6 py-5">
            <div>
              <h2 class="text-xl font-bold text-slate-950">对话时间线</h2>
              <p class="mt-1 text-sm text-slate-500">{{ interviewerName }} · {{ roundSummary }} · 每条消息都保留发送时间。</p>
            </div>
            <span class="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-500">{{ history.length }} 条消息</span>
          </header>

          <div ref="chatBox" class="min-h-0 flex-1 overflow-y-auto bg-[linear-gradient(180deg,#f8fbff_0%,#eef2ff_100%)] px-6 py-6">
            <div v-if="loading" class="flex h-full items-center justify-center">
              <div class="h-9 w-9 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent"></div>
            </div>
            <div v-else-if="!history.length" class="flex h-full items-center justify-center">
              <div class="rounded-2xl bg-white px-8 py-6 text-center text-sm text-slate-500 shadow-sm">暂无面试记录</div>
            </div>
            <div v-else class="space-y-6">
              <div
                v-for="(msg, i) in history"
                :key="i"
                :class="['flex gap-3', msg.role === 'candidate' ? 'justify-end' : 'justify-start']"
              >
                <div v-if="msg.role !== 'candidate'" class="mt-7 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-sm font-bold text-white shadow-sm">
                  {{ roleShort(msg.role) }}
                </div>
                <div :class="['max-w-[78%]', msg.role === 'candidate' ? 'text-right' : 'text-left']">
                  <div :class="['mb-2 flex items-center gap-2', msg.role === 'candidate' ? 'justify-end' : 'justify-start']">
                    <span class="text-sm font-bold text-slate-700">{{ roleLabel(msg.role) }}</span>
                    <span v-if="formatMessageTime(msg.timestamp)" class="text-sm font-semibold text-slate-400">{{ formatMessageTime(msg.timestamp) }}</span>
                  </div>
                  <div
                    :class="[
                      'inline-block rounded-3xl px-5 py-4 text-left text-[15px] leading-7 whitespace-pre-wrap shadow-sm',
                      msg.role === 'candidate'
                        ? 'rounded-tr-md bg-emerald-500 text-white shadow-emerald-100'
                        : 'rounded-tl-md bg-white text-slate-700 ring-1 ring-slate-100'
                    ]"
                  >
                    {{ msg.content }}
                  </div>
                </div>
                <div v-if="msg.role === 'candidate'" class="mt-7 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-emerald-500 text-sm font-bold text-white shadow-sm">
                  {{ roleShort(msg.role) }}
                </div>
              </div>
            </div>
          </div>

          <footer class="flex flex-shrink-0 items-center justify-center gap-3 border-t border-slate-100 bg-white px-5 py-4">
            <router-link
              :to="{ path: '/admin/report', query: { session_id: route.query.session_id } }"
              class="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 no-underline"
            >
              查看面试报告
            </router-link>
            <router-link to="/admin/interview-archive" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-500 hover:bg-slate-50 no-underline">
              返回档案
            </router-link>
          </footer>
        </section>
      </div>
    </main>
  </div>
</template>
