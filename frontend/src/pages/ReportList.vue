<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const reports = ref([])
const loading = ref(true)
const searchText = ref('')
const filterConclusion = ref('')

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterConclusion.value) params.set('conclusion', filterConclusion.value)
    const qs = params.toString()
    const res = await fetch(`/api/records${qs ? '?' + qs : ''}`)
    if (res.ok) reports.value = await res.json()
  } catch (_) { /* ignore */ }
  loading.value = false
}

onMounted(fetchList)

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
  if (s === null) return 'text-gray-400'
  if (s >= 80) return 'text-[#22c55e]'
  if (s >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

function resetFilters() { searchText.value = ''; filterConclusion.value = ''; fetchList() }
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">面试报告</h2>
          <p class="text-gray-500 text-sm">面试结束后系统自动生成完整评估报告</p>
        </div>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-60 relative">
            <input v-model="searchText" type="text" placeholder="搜索候选人姓名" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="fetchList">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterConclusion" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="fetchList">
            <option value="">全部面试结论</option>
            <option value="建议录用">建议录用</option>
            <option value="待定观察">待定观察</option>
            <option value="不予录用">不予录用</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置筛选</button>
        </div>
      </div>

      <!-- 报告卡片 -->
      <div v-if="loading" class="text-center py-12 text-gray-400"><i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        <div v-for="r in reports" :key="r.session_id" class="bg-white rounded-xl p-5 shadow-sm hover:shadow-md transition">
          <div class="flex justify-between items-start mb-3">
            <div>
              <h3 class="font-bold text-base">{{ r.candidate }}<span class="text-gray-500 font-normal"> - {{ r.position }}</span></h3>
              <p class="text-xs text-gray-400">报告生成：{{ r.created_at?.slice(0, 16) || '-' }}</p>
            </div>
            <span :class="['px-2 py-1 text-xs rounded', conclusionBadge(r.conclusion)]">{{ r.conclusion }}</span>
          </div>

          <!-- 评分进度条 -->
          <div class="mb-3">
            <div class="flex justify-between text-sm mb-1">
              <span class="text-gray-500">综合评分</span>
              <span :class="['font-medium', scoreColor(r.score)]">{{ r.score_display }}</span>
            </div>
            <div class="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div :class="['h-full rounded-full', scoreBar(r.score || 0)]" :style="{ width: (r.score || 0) + '%' }"></div>
            </div>
          </div>

          <p class="text-sm text-gray-500 mb-4 line-clamp-2">
            {{ r.score >= 80 ? '候选人表现出色，各项能力指标达到或超出预期，综合素质优秀。' : r.score >= 60 ? '候选人基本满足要求，部分领域需要提升，可进一步考察。' : '候选人与岗位要求存在差距，建议针对性提升后再试。' }}
          </p>

          <div class="flex gap-2">
            <button class="flex-1 border border-[#1677ff] text-[#1677ff] py-1.5 rounded text-sm hover:bg-blue-50" @click="router.push({ path: '/report', query: { session_id: r.session_id } })">查看完整报告</button>
            <button class="flex-1 bg-gray-100 text-gray-600 py-1.5 rounded text-sm hover:bg-gray-200">
              <i class="fa fa-download mr-1"></i>下载PDF
            </button>
          </div>
        </div>
      </div>

      <div v-if="!loading && !reports.length" class="text-center py-12 text-gray-400">
        <i class="fa fa-bar-chart text-3xl mb-2 block"></i>暂无面试报告，完成面试后自动生成
      </div>

      <div class="flex justify-between items-center mt-6 text-sm text-gray-500"><span>共 {{ reports.length }} 份</span></div>
    </main>
  </div>
</template>
