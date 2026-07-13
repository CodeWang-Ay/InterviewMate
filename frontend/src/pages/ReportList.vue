<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const reports = ref([])
const loading = ref(true)
const searchText = ref('')
const filterConclusion = ref('')
const page = ref(1)
const pageSize = ref(10)
const activeGroup = ref(null)

function roundKey(report) {
  return `${report.stage_order || 1}::${report.interview_round || '面试'}`
}

function summarizeRoundItems(items) {
  const roundMap = new Map()
  items.forEach((item) => {
    const key = roundKey(item)
    const current = roundMap.get(key)
    if (!current) {
      roundMap.set(key, { ...item, history_count: 1, histories: [item] })
      return
    }

    const histories = [...current.histories, item]
    const nextCount = (current.history_count || 1) + 1
    if (String(item.created_at || '') > String(current.created_at || '')) {
      roundMap.set(key, { ...item, history_count: nextCount, histories })
    } else {
      roundMap.set(key, { ...current, history_count: nextCount, histories })
    }
  })

  return Array.from(roundMap.values()).sort((a, b) =>
    (a.stage_order || 1) - (b.stage_order || 1) ||
    String(b.created_at || '').localeCompare(String(a.created_at || ''))
  )
}

const groupedReports = computed(() => {
  const groups = new Map()
  reports.value.forEach((report) => {
    const key = report.workflow_id || report.candidate_username || `${report.candidate}::${report.position}`
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        candidate: report.candidate || '未知',
        position: report.position || '-',
        workflow_name: report.workflow_name || '单轮面试',
        items: [],
      })
    }
    groups.get(key).items.push(report)
  })

  return Array.from(groups.values()).map((group) => {
    group.items = summarizeRoundItems(group.items)
    group.round_count = group.items.length
    group.session_count = group.items.reduce((sum, item) => sum + (item.history_count || 1), 0)
    group.generated_count = group.items.filter(item => item.score !== null && item.score !== undefined).length
    group.latest_created_at = group.items.reduce((latest, item) => !latest || String(item.created_at || '') > String(latest || '') ? item.created_at : latest, '')
    const scored = group.items.filter(item => item.score !== null && item.score !== undefined)
    group.avg_score = scored.length ? `${Math.round(scored.reduce((sum, item) => sum + Number(item.score || 0), 0) / scored.length)}/100` : '-'
    group.latest_conclusion = scored[0]?.conclusion || '未知'
    return group
  }).sort((a, b) => String(b.latest_created_at || '').localeCompare(String(a.latest_created_at || '')))
})

const totalPages = computed(() => Math.max(1, Math.ceil(groupedReports.value.length / pageSize.value)))
const pagedGroups = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return groupedReports.value.slice(start, start + pageSize.value)
})
const visiblePages = computed(() => {
  const total = totalPages.value
  const start = Math.max(1, Math.min(page.value - 2, Math.max(1, total - 4)))
  const end = Math.min(total, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterConclusion.value) params.set('conclusion', filterConclusion.value)
    const qs = params.toString()
    const res = await fetch(`/api/records${qs ? '?' + qs : ''}`)
    if (res.ok) {
      reports.value = await res.json()
      if (page.value > totalPages.value) page.value = totalPages.value
      syncActiveGroup()
    }
  } catch (_) { /* ignore */ }
  loading.value = false
}

onMounted(fetchList)

function syncActiveGroup() {
  if (!activeGroup.value) return
  activeGroup.value = groupedReports.value.find(group => group.key === activeGroup.value.key) || null
}

const conclusionBadge = (c) => ({
  '建议录用': 'bg-green-100 text-green-600',
  '待定观察': 'bg-yellow-100 text-yellow-600',
  '不予录用': 'bg-red-100 text-red-600',
  '未知': 'bg-gray-100 text-gray-500',
}[c] || 'bg-gray-100')

const scoreBar = (s) => {
  if (s >= 80) return 'bg-[#22c55e]'
  if (s >= 60) return 'bg-yellow-500'
  return 'bg-red-500'
}

const scoreColor = (s) => {
  if (s === null || s === undefined) return 'text-gray-400'
  if (s >= 80) return 'text-[#22c55e]'
  if (s >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

function setPage(nextPage) {
  page.value = Math.min(Math.max(1, nextPage), totalPages.value)
}

function changePageSize(size) {
  pageSize.value = Number(size)
  page.value = 1
}

function openGroup(group) {
  activeGroup.value = group
}

function resetFilters() {
  searchText.value = ''
  filterConclusion.value = ''
  page.value = 1
  fetchList()
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">面试报告</h2>
          <p class="text-gray-500 text-sm">按候选人汇总查看多轮面试报告</p>
        </div>
      </div>

      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-60 relative">
            <input v-model="searchText" type="text" placeholder="搜索候选人姓名" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="page = 1; fetchList()">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterConclusion" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="page = 1; fetchList()">
            <option value="">全部面试结论</option>
            <option value="建议录用">建议录用</option>
            <option value="待定观察">待定观察</option>
            <option value="不予录用">不予录用</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置筛选</button>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm overflow-hidden">
        <div v-if="loading" class="text-center py-12 text-gray-400"><i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...</div>
        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm w-8">#</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">候选人</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">应聘岗位</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">面试流程</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">报告进度</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">平均得分</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">最新结论</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-44">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(group, i) in pagedGroups" :key="group.key" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm text-gray-500">{{ (page - 1) * pageSize + i + 1 }}</td>
              <td class="px-4 py-3">
                <div class="font-medium text-sm text-gray-900">{{ group.candidate }}</div>
                <div class="text-xs text-gray-400">{{ group.round_count }} 个面试环节<span v-if="group.session_count > group.round_count"> · {{ group.session_count }} 次会话</span></div>
              </td>
              <td class="px-4 py-3 text-sm">{{ group.position }}</td>
              <td class="px-4 py-3 text-sm">
                <div class="font-medium text-gray-800">{{ group.workflow_name }}</div>
                <div class="flex flex-wrap gap-1 mt-1">
                  <span v-for="item in group.items" :key="item.session_id" class="px-2 py-0.5 rounded bg-indigo-50 text-indigo-600 text-xs">
                    {{ item.interview_round || '面试' }}<span v-if="item.history_count > 1"> · {{ item.history_count }}次</span>
                  </span>
                </div>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ group.generated_count }}/{{ group.round_count }} 已生成</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <span :class="['font-medium text-sm w-16', scoreColor(group.items[0]?.score)]">{{ group.avg_score }}</span>
                  <div class="w-28 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div :class="['h-full rounded-full', scoreBar(Number.parseInt(group.avg_score) || 0)]" :style="{ width: `${Number.parseInt(group.avg_score) || 0}%` }"></div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3"><span :class="['px-2 py-1 text-xs rounded', conclusionBadge(group.latest_conclusion)]">{{ group.latest_conclusion }}</span></td>
              <td class="px-4 py-3 text-center">
                <button class="text-[#1677ff] hover:underline text-sm" @click="openGroup(group)">查看报告</button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="!loading && !groupedReports.length" class="text-center py-12 text-gray-400">
          <i class="fa fa-bar-chart text-3xl mb-2 block"></i>暂无面试报告，完成面试后自动生成
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 mt-6 text-sm text-gray-500">
        <div class="flex items-center gap-3">
          <span>共 {{ groupedReports.length }} 位候选人 / {{ reports.length }} 份报告</span>
          <select class="border border-gray-200 rounded-lg px-2 py-1 bg-white" :value="pageSize" @change="changePageSize($event.target.value)">
            <option :value="10">10 条/页</option>
            <option :value="20">20 条/页</option>
            <option :value="50">50 条/页</option>
          </select>
        </div>
        <div class="flex items-center gap-1">
          <button class="px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 disabled:text-gray-300 disabled:cursor-not-allowed" :disabled="page <= 1" @click="setPage(page - 1)">上一页</button>
          <button
            v-for="p in visiblePages"
            :key="p"
            :class="['min-w-8 px-3 py-1.5 rounded-lg border text-sm', p === page ? 'border-[#1677ff] bg-blue-50 text-[#1677ff]' : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50']"
            @click="setPage(p)"
          >{{ p }}</button>
          <button class="px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 disabled:text-gray-300 disabled:cursor-not-allowed" :disabled="page >= totalPages" @click="setPage(page + 1)">下一页</button>
        </div>
      </div>
    </main>

    <div v-if="activeGroup" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="activeGroup = null">
      <div class="bg-white rounded-xl w-full max-w-5xl max-h-[88vh] shadow-xl overflow-hidden flex flex-col">
        <div class="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold text-gray-900">{{ activeGroup.candidate }} · {{ activeGroup.workflow_name }}</h3>
            <p class="text-sm text-gray-500 mt-1">{{ activeGroup.position }} · {{ activeGroup.round_count }} 个面试环节<span v-if="activeGroup.session_count > activeGroup.round_count"> · 共 {{ activeGroup.session_count }} 次会话</span></p>
          </div>
          <button class="w-8 h-8 rounded-lg text-gray-400 hover:bg-gray-100" @click="activeGroup = null"><i class="fa fa-times"></i></button>
        </div>

        <div class="overflow-auto p-6 space-y-4">
          <div v-for="item in activeGroup.items" :key="item.session_id" class="border border-gray-200 rounded-xl overflow-hidden">
            <div class="px-4 py-3 bg-gray-50 flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center text-sm font-semibold">{{ item.stage_order || 1 }}</span>
                <div>
                  <div class="font-semibold text-gray-900">{{ item.interview_round || '面试环节' }}</div>
                  <div class="text-xs text-gray-400">会话 ID：{{ item.session_id }} · {{ item.created_at?.slice(0, 16) || '-' }}</div>
                </div>
                <span v-if="item.history_count > 1" class="px-2 py-1 text-xs rounded bg-amber-50 text-amber-600">历史 {{ item.history_count }} 次</span>
                <span :class="['px-2 py-1 text-xs rounded', conclusionBadge(item.conclusion)]">{{ item.conclusion }}</span>
              </div>
              <div class="flex items-center gap-2">
                <button class="px-3 py-1.5 rounded-lg border border-[#1677ff] text-[#1677ff] text-sm hover:bg-blue-50" @click="router.push({ path: '/report', query: { session_id: item.session_id } })">查看报告</button>
                <button class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm hover:bg-white" @click="router.push({ path: '/interview-record', query: { session_id: item.session_id } })">对话回放</button>
              </div>
            </div>
            <div class="px-4 py-3 flex items-center justify-between text-sm">
              <div class="text-gray-600">报告状态：{{ item.score !== null && item.score !== undefined ? '已生成' : '待生成' }}</div>
              <div :class="['font-medium', scoreColor(item.score)]">综合得分：{{ item.score_display }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
