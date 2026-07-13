<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const report = ref(null)
const loading = ref(true)
const scrollBox = ref(null)

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
    const r = maxR + 28
    return { name, x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) + 5 }
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
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
    <!-- 固定大小的报告卡片 -->
    <div class="w-full max-w-6xl h-[88vh] bg-slate-900/60 backdrop-blur-sm border border-slate-700/50 rounded-2xl shadow-2xl flex flex-col overflow-hidden">

      <!-- Header (固定) -->
      <header class="flex-shrink-0 border-b border-slate-700/50 px-5 py-3 flex items-center gap-3 bg-slate-800/30 rounded-t-2xl">
        <router-link to="/" class="text-slate-400 hover:text-white transition-colors">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
        </router-link>
        <div class="flex-1">
          <h1 class="text-white font-semibold text-sm">{{ report?.report_title || '面试报告' }}</h1>
          <p class="text-slate-500 text-xs">{{ report?.created_at?.slice(0, 10) || '' }}</p>
        </div>
      </header>

      <!-- Content (可滚动) -->
      <div ref="scrollBox" class="flex-1 overflow-y-auto px-5 py-6 space-y-6">

        <!-- Loading -->
        <div v-if="loading" class="text-center py-20">
          <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p class="text-slate-400">正在生成报告...</p>
        </div>

        <!-- Not found -->
        <div v-else-if="!report" class="text-center py-20">
          <p class="text-slate-400 mb-4">报告不可用</p>
          <router-link to="/" class="text-blue-400 hover:text-blue-300">返回首页</router-link>
        </div>

        <template v-else>
          <!-- Basic Info -->
          <div class="grid grid-cols-3 gap-3">
            <div class="bg-slate-800/40 rounded-xl p-3 text-center border border-slate-700/50">
              <p class="text-slate-500 text-xs mb-1">面试时长</p>
              <p class="text-white font-semibold text-sm">{{ report.duration }}</p>
            </div>
            <div class="bg-slate-800/40 rounded-xl p-3 text-center border border-slate-700/50">
              <p class="text-slate-500 text-xs mb-1">问题数</p>
              <p class="text-white font-semibold text-sm">{{ report.total_questions }} 题</p>
            </div>
            <div class="bg-slate-800/40 rounded-xl p-3 text-center border border-slate-700/50">
              <p class="text-slate-500 text-xs mb-1">已回答</p>
              <p class="text-white font-semibold text-sm">{{ report.answered_questions }} 题</p>
            </div>
          </div>

          <!-- Charts Row -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <!-- Donut -->
            <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 p-5 flex flex-col items-center justify-center">
              <p class="text-slate-400 text-xs mb-3">综合评分</p>
              <div class="relative w-36 h-36">
                <svg viewBox="0 0 140 140" class="w-full h-full -rotate-90">
                  <circle cx="70" cy="70" :r="donutR" fill="none" stroke="#334155" stroke-width="12" />
                  <circle
                    cx="70" cy="70" :r="donutR" fill="none"
                    :stroke="scoreColor(report.overall_score).stroke"
                    stroke-width="12" stroke-linecap="round"
                    :stroke-dasharray="donutC"
                    :stroke-dashoffset="donutOffset"
                    class="transition-all duration-1000 ease-out"
                  />
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center">
                  <span :class="['text-4xl font-bold', scoreColor(report.overall_score).text]">{{ report.overall_score }}</span>
                  <span class="text-slate-500 text-[10px]">/ 100</span>
                </div>
              </div>
            </div>

            <!-- Radar -->
            <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 p-3 flex items-center justify-center">
              <svg viewBox="0 0 320 320" class="w-full max-w-[280px]">
                <polygon v-for="g in bgGrids" :key="g.level" :points="g.pts" fill="none" stroke="#334155" stroke-width="1" />
                <text v-for="g in bgGrids" :key="'l'+g.level" :x="cx-5" :y="cy-(g.level/100)*maxR-4" fill="#475569" font-size="9" text-anchor="end">{{ g.level }}</text>
                <line v-for="(a,i) in axes" :key="'a'+i" :x1="cx" :y1="cy" :x2="a.x" :y2="a.y" stroke="#334155" stroke-width="1" />
                <polygon :points="scorePolygon" :fill="scoreColor(report.overall_score).stroke" fill-opacity="0.2" :stroke="scoreColor(report.overall_score).stroke" stroke-width="2" class="transition-all duration-700" />
                <circle v-for="(p,i) in reportDots" :key="'d'+i" :cx="p.x" :cy="p.y" r="4" :fill="scoreColor(report.overall_score).stroke" />
                <text v-for="l in labels" :key="l.name" :x="l.x" :y="l.y" fill="#94a3b8" font-size="11" text-anchor="middle" font-weight="500">{{ l.name }}</text>
              </svg>
            </div>
          </div>

          <!-- Bar Charts -->
          <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 p-5">
            <h3 class="text-white font-semibold text-sm mb-4">各维度评分</h3>
            <div class="space-y-3">
              <div v-for="d in report.dimensions" :key="d.name">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-slate-300 text-sm">{{ d.name }}</span>
                  <span :class="['text-sm font-bold', scoreColor(d.score).text]">{{ d.score }}</span>
                </div>
                <div class="w-full h-2.5 bg-slate-700/50 rounded-full overflow-hidden">
                  <div :class="['h-full rounded-full transition-all duration-1000', scoreColor(d.score).bg]" :style="{ width: d.score + '%' }"></div>
                </div>
                <p class="text-slate-500 text-xs mt-1 leading-relaxed">{{ d.comment }}</p>
              </div>
            </div>
          </div>

          <!-- Interview Record Link -->
          <router-link
            :to="{ path: '/interview-record', query: { session_id: report.session_id } }"
            class="block bg-slate-800/30 rounded-2xl border border-slate-700/50 p-4 hover:border-blue-600/40 transition-colors group"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-blue-600/20 flex items-center justify-center group-hover:bg-blue-600/30 transition-colors">
                  <svg class="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
                  </svg>
                </div>
                <div>
                  <h3 class="text-white font-medium text-sm">面试记录</h3>
                  <p class="text-slate-500 text-xs">{{ report?.report_type === 'interviewer_training' ? '查看本轮训练的完整对练过程' : '查看完整的面试对话过程' }}</p>
                </div>
              </div>
              <svg class="w-4 h-4 text-slate-500 group-hover:text-white group-hover:translate-x-1 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          </router-link>

          <!-- Suggestions -->
          <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 p-5">
            <h2 class="text-white font-semibold text-sm mb-3 flex items-center gap-2">
              <svg class="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
              </svg>
              改进建议
            </h2>
            <ol class="space-y-1.5">
              <li v-for="(s, i) in report.suggestions" :key="i" class="flex gap-2 text-sm">
                <span class="text-yellow-400 font-bold flex-shrink-0">{{ i + 1 }}.</span>
                <span class="text-slate-300">{{ s }}</span>
              </li>
            </ol>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
