<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const route = useRoute()
const report = ref(null)
const loading = ref(true)
const scrollBox = ref(null)
const recordBox = ref(null)
const showRecordPanel = ref(false)

// ---- 环形图参数 ----
const donutR = 62
const donutC = 2 * Math.PI * donutR

// ---- 雷达图参数 ----
const cx = 160, cy = 160, maxR = 130
const gridLevels = [20, 40, 60, 80, 100]
const dimNames = computed(() => report.value?.dimensions?.map(d => d.name) || [])
const dimCount = computed(() => Math.max(dimNames.value.length, 1))

function radarPoints(scores) {
  return scores.map((s, i) => {
    const angle = (Math.PI * 2 * i) / dimCount.value - Math.PI / 2
    const r = (s / 100) * maxR
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }
  })
}

const bgGrids = computed(() => {
  if (!report.value) return []
  return gridLevels.map(level => {
    const pts = Array.from({ length: dimCount.value }, (_, i) => {
      const angle = (Math.PI * 2 * i) / dimCount.value - Math.PI / 2
      const r = (level / 100) * maxR
      return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`
    }).join(' ')
    return { level, pts }
  })
})

const axes = computed(() => {
  return dimNames.value.map((_, i) => {
    const angle = (Math.PI * 2 * i) / dimCount.value - Math.PI / 2
    return { x: cx + maxR * Math.cos(angle), y: cy + maxR * Math.sin(angle) }
  })
})

const labels = computed(() => {
  return dimNames.value.map((name, i) => {
    const angle = (Math.PI * 2 * i) / dimCount.value - Math.PI / 2
    const cos = Math.cos(angle)
    const sin = Math.sin(angle)
    const r = maxR + 34
    let anchor = 'middle'
    if (cos > 0.35) anchor = 'start'
    if (cos < -0.35) anchor = 'end'
    return {
      name,
      x: cx + r * cos,
      y: cy + r * sin + 5,
      anchor,
    }
  })
})

const scorePolygon = computed(() => {
  if (!report.value) return ''
  return radarPoints(report.value.dimensions.map(d => d.score)).map(p => `${p.x},${p.y}`).join(' ')
})

const donutOffset = computed(() => {
  if (!report.value) return donutC
  return donutC - (report.value.overall_score / 100) * donutC
})

const scoreColor = (score) => {
  if (score >= 80) return { stroke: '#22c55e', text: 'text-green-400', bg: 'bg-green-600' }
  if (score >= 60) return { stroke: '#eab308', text: 'text-yellow-400', bg: 'bg-yellow-600' }
  return { stroke: '#ef4444', text: 'text-red-400', bg: 'bg-red-600' }
}

const reportDots = computed(() => {
  if (!report.value) return []
  return radarPoints(report.value.dimensions.map(d => d.score))
})

const candidateName = computed(() => report.value?.candidate_name || report.value?.resume_name || report.value?.candidate_username || '未知候选人')
const jobName = computed(() => report.value?.jd_name || report.value?.report_title || '未知岗位')
const scoreTone = computed(() => {
  const score = report.value?.overall_score || 0
  if (score >= 85) return { label: '强烈推荐', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' }
  if (score >= 70) return { label: '推荐进入下一轮', color: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200' }
  if (score >= 60) return { label: '谨慎推进', color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' }
  return { label: '暂不推荐', color: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-200' }
})
const sortedDimensions = computed(() => {
  const items = Array.isArray(report.value?.dimensions) ? [...report.value.dimensions] : []
  return items.sort((a, b) => b.score - a.score)
})
const strengthDimensions = computed(() => sortedDimensions.value.slice(0, 2))
const weakDimensions = computed(() => sortedDimensions.value.slice(-2).reverse())
const overviewText = computed(() => {
  const score = report.value?.overall_score || 0
  const best = strengthDimensions.value[0]?.name || '核心能力'
  const weak = weakDimensions.value[0]?.name || '细节表达'
  if (score >= 85) return `候选人在 ${best} 方面表现突出，整体能力与岗位要求匹配度较高，可优先推进到后续流程。建议在下一轮继续验证 ${weak} 的稳定性。`
  if (score >= 70) return `候选人具备较好的岗位基础，${best} 有一定优势；但 ${weak} 仍需要结合追问继续核验，建议进入下一轮并重点补充验证。`
  if (score >= 60) return `候选人具备部分相关经验，但整体表现仍有波动，尤其需要进一步确认 ${weak} 是否满足岗位要求。建议谨慎推进。`
  return `候选人与当前岗位要求仍存在明显差距，建议暂缓推进，并优先补足 ${weak} 等关键能力。`
})

const recordHistory = computed(() => {
  const items = Array.isArray(report.value?.history) ? report.value.history : []
  return items.map((message) => ({
    ...message,
    timestamp: message.timestamp || message.created_at || '',
  }))
})

function roleLabel(role) {
  if (role === 'candidate') return '候选人'
  if (role === 'trainer') return '训练反馈'
  return report.value?.report_type === 'interviewer_training' ? '候选人模拟' : '面试官'
}

function roleShort(role) {
  if (role === 'candidate') return '候'
  if (role === 'trainer') return '评'
  return '官'
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

async function openRecordPanel() {
  showRecordPanel.value = true
  await nextTick()
  if (recordBox.value) recordBox.value.scrollTop = recordBox.value.scrollHeight
}

onMounted(async () => {
  const sid = route.query.session_id
  if (!sid) { loading.value = false; return }
  try {
    const res = await fetch(`/api/report/${sid}`)
    if (res.ok) report.value = await res.json()
  } catch (_) { /* ignore */ }
  loading.value = false
})
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-[#eef2ff] text-slate-900">
    <Sidebar />

    <main ref="scrollBox" class="flex-1 overflow-y-auto px-6 py-8">
      <div class="mx-auto w-full max-w-[1680px]">
      <div v-if="loading" class="flex min-h-[60vh] items-center justify-center">
        <div class="text-center">
          <div class="mx-auto mb-4 h-9 w-9 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent"></div>
          <p class="text-sm text-slate-500">正在生成报告...</p>
        </div>
      </div>

      <div v-else-if="!report" class="flex min-h-[60vh] items-center justify-center">
        <div class="rounded-2xl bg-white px-10 py-8 text-center shadow-sm">
          <p class="mb-4 text-sm text-slate-500">报告不可用</p>
          <router-link to="/" class="text-sm font-semibold text-indigo-600 hover:text-indigo-700">返回首页</router-link>
        </div>
      </div>

      <template v-else>
        <section class="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)]">
          <div class="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-100">
            <div class="flex items-start gap-5">
              <div class="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                <svg class="h-9 w-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 7.5a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 20.25a7.5 7.5 0 0 1 15 0" />
                </svg>
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div class="min-w-0">
                    <h1 class="truncate text-3xl font-bold tracking-normal text-slate-950">{{ candidateName }}</h1>
                    <p class="mt-1 text-base font-semibold text-slate-500">{{ jobName }}</p>
                  </div>
                  <span :class="['rounded-lg border px-3 py-1 text-sm font-semibold', scoreTone.bg, scoreTone.color, scoreTone.border]">
                    {{ scoreTone.label }}
                  </span>
                </div>
                <div class="mt-4 flex flex-wrap gap-2 text-sm">
                  <span class="rounded-lg bg-indigo-50 px-3 py-1.5 font-semibold text-indigo-600">{{ report.report_type === 'interviewer_training' ? '面试官训练' : '正式面试' }}</span>
                  <span class="rounded-lg bg-slate-100 px-3 py-1.5 text-slate-600">总分 {{ report.overall_score }}</span>
                  <span class="rounded-lg bg-slate-100 px-3 py-1.5 text-slate-600">{{ report.duration || '时长未知' }}</span>
                  <span class="rounded-lg bg-slate-100 px-3 py-1.5 text-slate-600">{{ report.answered_questions }} / {{ report.total_questions }} 题</span>
                </div>
                <button
                  class="mt-5 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-indigo-200 hover:bg-indigo-700"
                  @click="openRecordPanel"
                >
                  <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 12c0 4.142-4.03 7.5-9 7.5a10.5 10.5 0 0 1-3.151-.477L3 21l1.58-4.214A6.9 6.9 0 0 1 3 12c0-4.142 4.03-7.5 9-7.5s9 3.358 9 7.5Z" />
                  </svg>
                  查看完整记录
                </button>
              </div>
            </div>

            <div class="mt-8 border-t border-slate-100 pt-7">
              <p class="text-lg font-bold text-indigo-600">整体评价</p>
              <p class="mt-3 text-[17px] leading-9 text-slate-600">{{ overviewText }}</p>
            </div>
          </div>

          <div class="rounded-2xl bg-white/45 p-6 shadow-sm ring-1 ring-indigo-100/70">
            <div class="mb-2 flex items-center justify-between">
              <div>
                <p class="text-xs font-bold uppercase tracking-[0.18em] text-indigo-400">Score radar</p>
                <h2 class="mt-1 text-lg font-bold text-slate-900">能力雷达</h2>
              </div>
              <span :class="['rounded-full px-3 py-1 text-sm font-bold', scoreTone.bg, scoreTone.color]">{{ report.overall_score }} 分</span>
            </div>
            <div class="relative flex min-h-[310px] items-center justify-center">
              <div class="absolute inset-8 rounded-full bg-white/60 blur-3xl"></div>
              <svg viewBox="-70 -18 460 356" class="relative z-10 h-[330px] w-full max-w-[520px] overflow-visible">
                <polygon v-for="g in bgGrids" :key="g.level" :points="g.pts" fill="#ffffff" fill-opacity="0.36" stroke="#c7d2fe" stroke-width="1" />
                <line v-for="(a,i) in axes" :key="'a'+i" :x1="cx" :y1="cy" :x2="a.x" :y2="a.y" stroke="#c7d2fe" stroke-width="1" />
                <polygon :points="scorePolygon" fill="#6366f1" fill-opacity="0.18" stroke="#6366f1" stroke-width="3" />
                <circle v-for="(p,i) in reportDots" :key="'d'+i" :cx="p.x" :cy="p.y" r="4.5" fill="#6366f1" />
                <text v-for="l in labels" :key="l.name" :x="l.x" :y="l.y" fill="#334155" font-size="12" :text-anchor="l.anchor" font-weight="700">{{ l.name }}</text>
                <text :x="cx" :y="cy + 10" fill="#7c3aed" font-size="34" text-anchor="middle" font-weight="900">{{ report.overall_score }}</text>
              </svg>
            </div>
          </div>
        </section>

        <section class="mt-10 grid grid-cols-1 gap-8 xl:grid-cols-[1fr_240px_1fr]">
          <div class="space-y-8">
            <div class="rounded-2xl bg-white p-7 shadow-sm ring-1 ring-slate-100">
              <h2 class="flex items-center gap-2 text-lg font-bold text-slate-800">
                <span class="h-2 w-2 rounded-full bg-emerald-400"></span>
                核心优势
              </h2>
              <ul class="mt-5 space-y-3 text-sm leading-7 text-slate-600">
                <li v-for="d in strengthDimensions" :key="d.name">· {{ d.name }}：{{ d.comment }}</li>
              </ul>
            </div>
            <div class="rounded-2xl bg-white p-7 shadow-sm ring-1 ring-slate-100">
              <h2 class="flex items-center gap-2 text-lg font-bold text-slate-800">
                <span class="h-2 w-2 rounded-full bg-indigo-400"></span>
                背景匹配
              </h2>
              <ul class="mt-5 space-y-3 text-sm leading-7 text-slate-600">
                <li>· 本轮完成 {{ report.answered_questions }} 个有效回答，覆盖 {{ report.total_questions }} 个计划问题。</li>
                <li>· 与「{{ jobName }}」岗位的匹配判断主要来自综合评分、维度表现和问答稳定性。</li>
              </ul>
            </div>
          </div>

          <div class="flex items-center justify-center">
            <div class="relative h-44 w-44 rounded-full bg-white/45 shadow-inner">
              <div class="absolute inset-4 rounded-full border-[10px] border-indigo-100"></div>
              <div class="absolute left-5 top-5 h-32 w-32 rounded-full border-[10px] border-transparent border-l-emerald-200 border-t-indigo-200 border-r-amber-200"></div>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-xs font-bold uppercase tracking-[0.24em] text-slate-400">Overall</span>
                <span :class="['mt-1 text-2xl font-black', scoreTone.color]">{{ scoreTone.label.replace('进入下一轮', '') }}</span>
              </div>
            </div>
          </div>

          <div class="space-y-8">
            <div class="rounded-2xl bg-white p-7 shadow-sm ring-1 ring-slate-100">
              <h2 class="flex items-center gap-2 text-lg font-bold text-slate-800">
                <span class="h-2 w-2 rounded-full bg-rose-400"></span>
                薄弱环节
              </h2>
              <ul class="mt-5 space-y-3 text-sm leading-7 text-slate-600">
                <li v-for="d in weakDimensions" :key="d.name">· {{ d.name }}：{{ d.comment }}</li>
              </ul>
            </div>
            <div class="rounded-2xl bg-white p-7 shadow-sm ring-1 ring-slate-100">
              <h2 class="flex items-center gap-2 text-lg font-bold text-slate-800">
                <span class="h-2 w-2 rounded-full bg-amber-400"></span>
                推荐理由
              </h2>
              <ul class="mt-5 space-y-3 text-sm leading-7 text-slate-600">
                <li v-for="(s, i) in report.suggestions" :key="i">· {{ s }}</li>
              </ul>
            </div>
          </div>
        </section>

        <section class="mt-10 grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1.35fr)_minmax(380px,0.65fr)]">
          <div>
            <h2 class="mb-5 border-l-4 border-indigo-500 pl-3 text-xl font-bold text-slate-900">基础信息</h2>
            <div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
              <div class="flex items-start gap-5">
                <div class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl bg-indigo-100 text-lg font-black text-indigo-600">Q1</div>
                <div class="min-w-0 flex-1">
                  <div class="flex items-center justify-between gap-4">
                    <h3 class="text-xl font-bold text-slate-900">应聘状态</h3>
                    <div class="rounded-2xl bg-slate-50 px-5 py-3 text-center">
                      <p class="text-2xl font-black text-indigo-600">{{ report.overall_score }}</p>
                      <p class="text-xs font-semibold text-slate-400">AI Score</p>
                    </div>
                  </div>
                  <p class="mt-4 line-clamp-2 text-base leading-8 text-slate-500">
                    {{ recordHistory[0]?.content || '暂无首轮提问内容' }}
                  </p>
                  <button class="mt-5 rounded-xl border border-indigo-200 px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50" @click="openRecordPanel">
                    展开完整问答
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h2 class="mb-5 text-xl font-bold text-slate-900">评估维度</h2>
            <div class="space-y-4">
              <div v-for="d in report.dimensions" :key="d.name" class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
                <div class="flex items-center gap-4">
                  <div class="relative flex h-14 w-14 items-center justify-center rounded-full bg-amber-50">
                    <span class="text-lg font-black text-indigo-600">{{ d.score }}</span>
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center justify-between">
                      <h3 class="font-bold text-slate-900">{{ d.name }}</h3>
                      <span class="text-xs font-semibold text-slate-400">{{ d.score }} score</span>
                    </div>
                    <div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                      <div class="h-full rounded-full bg-indigo-500" :style="{ width: d.score + '%' }"></div>
                    </div>
                    <p class="mt-2 line-clamp-1 text-sm text-slate-500">{{ d.comment }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div
          v-if="report && showRecordPanel"
          class="fixed bottom-0 left-[220px] right-0 top-0 z-40 bg-slate-950/55 backdrop-blur-[3px]"
          @click="showRecordPanel = false"
        ></div>

        <aside
          v-if="report && showRecordPanel"
          class="fixed bottom-4 right-4 top-4 z-50 flex w-[min(900px,calc(100vw-252px))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
        >
          <div class="flex-shrink-0 border-b border-slate-100 px-5 py-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <h2 class="text-base font-semibold text-slate-950">完整记录</h2>
                <p class="mt-1 text-xs text-slate-500">{{ recordHistory.length }} 条消息，可与报告结论对照查看</p>
              </div>
              <button
                class="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition"
                title="关闭记录"
                @click="showRecordPanel = false"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <router-link
              :to="{ path: '/interview-record', query: { session_id: report.session_id } }"
              class="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 transition"
            >
              打开完整记录页
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </router-link>
          </div>

          <div ref="recordBox" class="flex-1 overflow-y-auto bg-white px-6 py-5">
            <div v-if="!recordHistory.length" class="h-full flex items-center justify-center text-sm text-slate-500">
              暂无对话记录
            </div>
            <div v-else class="space-y-5">
              <div
                v-for="(msg, i) in recordHistory"
                :key="i"
                :class="['flex gap-3', msg.role === 'candidate' ? 'flex-row-reverse' : '']"
              >
                <div
                  :class="[
                    'mt-6 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold text-white shadow-sm',
                    msg.role === 'candidate' ? 'bg-orange-500' : msg.role === 'trainer' ? 'bg-amber-500' : 'bg-teal-500'
                  ]"
                >
                  {{ roleShort(msg.role) }}
                </div>
                <div :class="['min-w-0 flex-1', msg.role === 'candidate' ? 'text-right' : '']">
                  <div :class="['mb-1.5 flex items-center gap-2', msg.role === 'candidate' ? 'justify-end' : 'justify-start']">
                    <span class="text-xs font-semibold text-slate-500">{{ roleLabel(msg.role) }}</span>
                    <span v-if="formatMessageTime(msg.timestamp)" class="text-xs font-medium text-slate-400">
                      {{ formatMessageTime(msg.timestamp) }}
                    </span>
                  </div>
                  <div
                    :class="[
                      'inline-block max-w-[82%] rounded-2xl px-4 py-3 text-left text-[15px] leading-relaxed whitespace-pre-wrap shadow-sm',
                      msg.role === 'candidate'
                        ? 'rounded-tr-sm bg-indigo-100 text-slate-900'
                        : msg.role === 'trainer'
                          ? 'rounded-tl-sm bg-amber-50 text-slate-900 border border-amber-100'
                          : 'rounded-tl-sm bg-slate-100 text-slate-900'
                    ]"
                  >
                    {{ msg.content }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </template>
      </div>
    </main>
  </div>
</template>
