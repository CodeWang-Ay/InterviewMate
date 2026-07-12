<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const report = ref(null)
const loading = ref(true)
const showQA = ref(false)

// ---- 环形图参数 ----
const donutR = 62
const donutC = 2 * Math.PI * donutR  // circumference ≈ 389.6

// ---- 雷达图参数 ----
const cx = 160, cy = 160, maxR = 130
const dimNames = ['沟通表达', '技术匹配', '项目经验', '问题解决', '岗位匹配']
const gridLevels = [20, 40, 60, 80, 100]

// 计算雷达图多边形的坐标点
function radarPoints(scores) {
  return scores.map((s, i) => {
    const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2
    const r = (s / 100) * maxR
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }
  })
}

function gridPoints(level) {
  return gridLevels[0] > 0  // placeholder, actual logic below
}

// 生成 5 层背景网格
const bgGrids = computed(() => {
  if (!report.value) return []
  return gridLevels.map(level => {
    const pts = Array.from({ length: 5 }, (_, i) => {
      const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2
      const r = (level / 100) * maxR
      return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`
    }).join(' ')
    return { level, pts }
  })
})

// 5 条轴线的端点
const axes = computed(() => {
  return dimNames.map((_, i) => {
    const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2
    return {
      x: cx + maxR * Math.cos(angle),
      y: cy + maxR * Math.sin(angle),
    }
  })
})

// 标签位置（稍微外移）
const labels = computed(() => {
  return dimNames.map((name, i) => {
    const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2
    const r = maxR + 28
    return {
      name,
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle) + 5,
    }
  })
})

// 分数多边形
const scorePolygon = computed(() => {
  if (!report.value) return ''
  const scores = report.value.dimensions.map(d => d.score)
  return radarPoints(scores).map(p => `${p.x},${p.y}`).join(' ')
})

// 环形图进度
const donutOffset = computed(() => {
  if (!report.value) return donutC
  return donutC - (report.value.overall_score / 100) * donutC
})

const scoreColor = (score) => {
  if (score >= 80) return { stroke: '#22c55e', text: 'text-green-400', bg: 'bg-green-600' }
  if (score >= 60) return { stroke: '#eab308', text: 'text-yellow-400', bg: 'bg-yellow-600' }
  return { stroke: '#ef4444', text: 'text-red-400', bg: 'bg-red-600' }
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
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
    <div class="max-w-4xl mx-auto px-4 py-8">

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

      <!-- Report -->
      <template v-else>
        <!-- Header -->
        <div class="flex items-center justify-between mb-8">
          <router-link to="/" class="text-slate-400 hover:text-white transition-colors flex items-center gap-1">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            返回
          </router-link>
          <h1 class="text-2xl font-bold text-white">面试报告</h1>
          <span class="text-slate-500 text-sm">{{ report.created_at?.slice(0, 10) || '' }}</span>
        </div>

        <!-- Basic Info -->
        <div class="grid grid-cols-3 gap-3 mb-8">
          <div class="bg-slate-800/40 rounded-xl p-4 text-center border border-slate-700/50">
            <p class="text-slate-500 text-xs mb-1">面试时长</p>
            <p class="text-white font-semibold">{{ report.duration }}</p>
          </div>
          <div class="bg-slate-800/40 rounded-xl p-4 text-center border border-slate-700/50">
            <p class="text-slate-500 text-xs mb-1">问题数</p>
            <p class="text-white font-semibold">{{ report.total_questions }} 题</p>
          </div>
          <div class="bg-slate-800/40 rounded-xl p-4 text-center border border-slate-700/50">
            <p class="text-slate-500 text-xs mb-1">已回答</p>
            <p class="text-white font-semibold">{{ report.answered_questions }} 题</p>
          </div>
        </div>

        <!-- Charts Row: Donut + Radar -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <!-- Donut: Overall Score -->
          <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 p-6 flex flex-col items-center justify-center">
            <p class="text-slate-400 text-sm mb-4">综合评分</p>
            <div class="relative w-44 h-44">
              <svg viewBox="0 0 140 140" class="w-full h-full -rotate-90">
                <!-- Background circle -->
                <circle cx="70" cy="70" :r="donutR" fill="none" stroke="#334155" stroke-width="12" />
                <!-- Progress circle -->
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
                <span :class="['text-5xl font-bold', scoreColor(report.overall_score).text]">
                  {{ report.overall_score }}
                </span>
                <span class="text-slate-500 text-xs mt-1">/ 100</span>
              </div>
            </div>
          </div>

          <!-- Radar Chart -->
          <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 p-4 flex items-center justify-center">
            <svg viewBox="0 0 320 320" class="w-full max-w-[320px]">
              <!-- Grid polygons -->
              <polygon
                v-for="g in bgGrids"
                :key="g.level"
                :points="g.pts"
                fill="none"
                stroke="#334155"
                stroke-width="1"
              />
              <!-- Grid labels -->
              <text
                v-for="g in bgGrids"
                :key="'l' + g.level"
                :x="cx - 5"
                :y="cy - (g.level / 100) * maxR - 4"
                fill="#475569"
                font-size="9"
                text-anchor="end"
              >{{ g.level }}</text>

              <!-- Axes -->
              <line
                v-for="(a, i) in axes"
                :key="'a' + i"
                :x1="cx" :y1="cy" :x2="a.x" :y2="a.y"
                stroke="#334155" stroke-width="1"
              />

              <!-- Score polygon -->
              <polygon
                :points="scorePolygon"
                :fill="scoreColor(report.overall_score).stroke"
                fill-opacity="0.2"
                :stroke="scoreColor(report.overall_score).stroke"
                stroke-width="2"
                class="transition-all duration-700"
              />

              <!-- Score dots -->
              <circle
                v-for="(p, i) in radarPoints(report.dimensions.map(d => d.score))"
                :key="'d' + i"
                :cx="p.x" :cy="p.y" r="4"
                :fill="scoreColor(report.overall_score).stroke"
              />

              <!-- Labels -->
              <text
                v-for="l in labels"
                :key="l.name"
                :x="l.x" :y="l.y"
                fill="#94a3b8"
                font-size="11"
                text-anchor="middle"
                font-weight="500"
              >{{ l.name }}</text>
            </svg>
          </div>
        </div>

        <!-- Bar Charts -->
        <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 p-6 mb-8">
          <h3 class="text-white font-semibold mb-5">各维度评分</h3>
          <div class="space-y-4">
            <div v-for="d in report.dimensions" :key="d.name">
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-slate-300 text-sm">{{ d.name }}</span>
                <span :class="['text-sm font-bold', scoreColor(d.score).text]">{{ d.score }}</span>
              </div>
              <div class="w-full h-3 bg-slate-700/50 rounded-full overflow-hidden">
                <div
                  :class="['h-full rounded-full transition-all duration-1000 ease-out', scoreColor(d.score).bg]"
                  :style="{ width: d.score + '%' }"
                ></div>
              </div>
              <p class="text-slate-500 text-xs mt-1.5 leading-relaxed">{{ d.comment }}</p>
            </div>
          </div>
        </div>

        <!-- Q&A Details -->
        <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 overflow-hidden mb-8">
          <button
            class="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-700/20 transition-colors"
            @click="showQA = !showQA"
          >
            <span class="text-white font-medium">问答详情</span>
            <svg
              :class="['w-5 h-5 text-slate-400 transition-transform', showQA ? 'rotate-180' : '']"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          <div v-if="showQA" class="border-t border-slate-700/50 divide-y divide-slate-700/30">
            <div v-for="(qa, i) in report.qa_pairs" :key="i" class="px-6 py-4">
              <p class="text-blue-400 text-sm font-medium mb-2">Q{{ i + 1 }}: {{ qa.question }}</p>
              <p class="text-slate-300 text-sm bg-slate-900/40 rounded-lg p-3 whitespace-pre-wrap">{{ qa.answer || '(未回答)' }}</p>
            </div>
          </div>
        </div>

        <!-- Suggestions -->
        <div class="bg-slate-800/30 rounded-2xl border border-slate-700/50 p-6 mb-8">
          <h2 class="text-white font-semibold mb-4 flex items-center gap-2">
            <svg class="w-5 h-5 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
            </svg>
            改进建议
          </h2>
          <ol class="space-y-2">
            <li v-for="(s, i) in report.suggestions" :key="i" class="flex gap-3 text-sm">
              <span class="text-yellow-400 font-bold flex-shrink-0">{{ i + 1 }}.</span>
              <span class="text-slate-300">{{ s }}</span>
            </li>
          </ol>
        </div>

        <div class="text-center pb-8">
          <router-link to="/" class="text-slate-500 hover:text-slate-300 text-sm transition-colors">
            ← 返回首页
          </router-link>
        </div>
      </template>
    </div>
  </div>
</template>
