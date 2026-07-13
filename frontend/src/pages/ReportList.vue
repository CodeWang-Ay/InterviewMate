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

const totalPages = computed(() => Math.max(1, Math.ceil(reports.value.length / pageSize.value)))
const pagedReports = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return reports.value.slice(start, start + pageSize.value)
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
    }
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

function setPage(nextPage) {
  page.value = Math.min(Math.max(1, nextPage), totalPages.value)
}

function changePageSize(size) {
  pageSize.value = Number(size)
  page.value = 1
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
          <p class="text-gray-500 text-sm">面试结束后系统自动生成完整评估报告</p>
        </div>
      </div>

      <!-- 搜索筛选 -->
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
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">报告生成时间</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">综合评分</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">面试结论</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-56">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(r, i) in pagedReports" :key="r.session_id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm text-gray-500">{{ (page - 1) * pageSize + i + 1 }}</td>
              <td class="px-4 py-3 font-medium text-sm">{{ r.candidate }}</td>
              <td class="px-4 py-3 text-sm">{{ r.position }}</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ r.created_at?.slice(0, 16) || '-' }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <span :class="['font-medium text-sm w-16', scoreColor(r.score)]">{{ r.score_display }}</span>
                  <div class="w-28 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div :class="['h-full rounded-full', scoreBar(r.score || 0)]" :style="{ width: (r.score || 0) + '%' }"></div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3"><span :class="['px-2 py-1 text-xs rounded', conclusionBadge(r.conclusion)]">{{ r.conclusion }}</span></td>
              <td class="px-4 py-3 text-center">
                <button class="text-[#1677ff] hover:underline text-sm" @click="router.push({ path: '/report', query: { session_id: r.session_id } })">查看完整报告</button>
                <button class="text-gray-500 hover:underline text-sm ml-2">
                  <i class="fa fa-download mr-1"></i>下载PDF
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="!loading && !reports.length" class="text-center py-12 text-gray-400">
          <i class="fa fa-bar-chart text-3xl mb-2 block"></i>暂无面试报告，完成面试后自动生成
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 mt-6 text-sm text-gray-500">
        <div class="flex items-center gap-3">
          <span>共 {{ reports.length }} 份</span>
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
  </div>
</template>
