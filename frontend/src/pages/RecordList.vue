<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const records = ref([])
const loading = ref(true)
const searchText = ref('')
const filterType = ref('')
const filterConclusion = ref('')
const batchMode = ref(false)
const selectedSessionIds = ref(new Set())
const batchWorking = ref(false)
const page = ref(1)
const pageSize = ref(10)

const totalPages = computed(() => Math.max(1, Math.ceil(records.value.length / pageSize.value)))
const pagedRecords = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return records.value.slice(start, start + pageSize.value)
})
const selectedRecords = computed(() => records.value.filter(r => selectedSessionIds.value.has(r.session_id)))
const allSelected = computed(() => pagedRecords.value.length > 0 && pagedRecords.value.every(r => selectedSessionIds.value.has(r.session_id)))
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
    if (filterType.value) params.set('record_type', filterType.value)
    if (filterConclusion.value) params.set('conclusion', filterConclusion.value)
    const qs = params.toString()
    const res = await fetch(`/api/records${qs ? '?' + qs : ''}`)
    if (res.ok) {
      records.value = await res.json()
      if (page.value > totalPages.value) page.value = totalPages.value
    }
  } catch (_) { /* ignore */ }
  loading.value = false
}

onMounted(fetchList)

function toggleBatchMode() {
  batchMode.value = !batchMode.value
  selectedSessionIds.value = new Set()
}

function setSelectedRecord(sessionId, checked) {
  const next = new Set(selectedSessionIds.value)
  if (checked) next.add(sessionId)
  else next.delete(sessionId)
  selectedSessionIds.value = next
}

function toggleSelectAll() {
  selectedSessionIds.value = allSelected.value ? new Set() : new Set(pagedRecords.value.map(r => r.session_id))
}

function setPage(nextPage) {
  page.value = Math.min(Math.max(1, nextPage), totalPages.value)
}

function changePageSize(size) {
  pageSize.value = Number(size)
  page.value = 1
}

async function removeRecord(sessionId) {
  if (!confirm('确认删除这条面试记录？')) return
  await fetch(`/api/records/${sessionId}`, { method: 'DELETE' })
  await fetchList()
}

async function deleteSelectedRecords() {
  if (!selectedRecords.value.length) return
  if (!confirm(`确认删除选中的 ${selectedRecords.value.length} 条面试记录？`)) return
  batchWorking.value = true
  for (const record of selectedRecords.value) {
    await fetch(`/api/records/${record.session_id}`, { method: 'DELETE' }).catch(() => {})
  }
  selectedSessionIds.value = new Set()
  batchWorking.value = false
  await fetchList()
}

const conclusionBadge = (c) => ({
  '建议录用': 'bg-green-100 text-green-600',
  '待定观察': 'bg-yellow-100 text-yellow-600',
  '不予录用': 'bg-red-100 text-red-600',
  '未知': 'bg-gray-100 text-gray-500',
}[c] || 'bg-gray-100')

const scoreColor = (s) => {
  if (s === null || s === undefined) return 'text-gray-400'
  if (s >= 80) return 'text-green-600'
  if (s >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

function resetFilters() {
  searchText.value = ''
  filterType.value = ''
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
        <h2 class="text-2xl font-bold text-gray-900">面试记录</h2>
        <div class="flex items-center gap-3">
          <button
            :class="['border px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition', batchMode ? 'border-orange-300 bg-orange-50 text-orange-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50']"
            @click="toggleBatchMode"
          >
            <i class="fa fa-check-square-o"></i>{{ batchMode ? '退出批量' : '批量管理' }}
          </button>
          <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 text-sm" @click="router.push('/interviewee')">
            <i class="fa fa-plus"></i> 新建面试
          </button>
        </div>
      </div>

      <div v-if="batchMode" class="bg-white rounded-xl p-4 shadow-sm mb-6 border border-orange-100 flex flex-wrap items-center justify-between gap-3">
        <div class="text-sm text-gray-600">
          已选择 <span class="font-semibold text-orange-600">{{ selectedRecords.length }}</span> 条面试记录
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button class="px-3 py-2 rounded-lg border border-gray-200 text-sm hover:bg-gray-50" @click="toggleSelectAll">{{ allSelected ? '取消全选' : '全选当前页' }}</button>
          <button class="px-3 py-2 rounded-lg border border-red-200 text-red-500 text-sm hover:bg-red-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedRecords.length" @click="deleteSelectedRecords"><i class="fa fa-trash-o mr-1"></i>批量删除</button>
        </div>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-64 relative">
            <input v-model="searchText" type="text" placeholder="搜索候选人姓名" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="page = 1; fetchList()">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterType" class="border rounded-lg px-3 py-2 min-w-[170px]" @change="page = 1; fetchList()">
            <option value="">全部面试类型</option>
            <option value="formal">正式面试（基于面试计划）</option>
            <option value="simulate">求职者模拟面试</option>
          </select>
          <select v-model="filterConclusion" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="page = 1; fetchList()">
            <option value="">全部面试结论</option>
            <option value="建议录用">建议录用</option>
            <option value="待定观察">待定观察</option>
            <option value="不予录用">不予录用</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置筛选</button>
        </div>
      </div>

      <!-- 表格 -->
      <div class="bg-white rounded-xl shadow-sm overflow-hidden">
        <div v-if="loading" class="text-center py-12 text-gray-400"><i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...</div>
        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th v-if="batchMode" class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-10">
                <input type="checkbox" :checked="allSelected" @change="toggleSelectAll">
              </th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm w-8">#</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">候选人</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">应聘岗位</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">面试类型</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">面试时间</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">综合得分</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">面试结论</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-52">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(r, i) in pagedRecords" :key="r.session_id" class="hover:bg-gray-50">
              <td v-if="batchMode" class="px-4 py-3 text-center">
                <input type="checkbox" :checked="selectedSessionIds.has(r.session_id)" @change="setSelectedRecord(r.session_id, $event.target.checked)">
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ (page - 1) * pageSize + i + 1 }}</td>
              <td class="px-4 py-3 font-medium text-sm">{{ r.candidate }}</td>
              <td class="px-4 py-3 text-sm">{{ r.position }}</td>
              <td class="px-4 py-3">
                <span :class="r.type === '正式面试' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'" class="px-2 py-1 text-xs rounded">{{ r.type_label }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ r.created_at?.slice(0, 16) || '-' }}</td>
              <td class="px-4 py-3 font-medium text-sm" :class="scoreColor(r.score)">{{ r.score_display }}</td>
              <td class="px-4 py-3"><span :class="['px-2 py-1 text-xs rounded', conclusionBadge(r.conclusion)]">{{ r.conclusion }}</span></td>
              <td class="px-4 py-3 text-center">
                <button class="text-[#1677ff] hover:underline text-sm" @click="router.push({ path: '/interview-record', query: { session_id: r.session_id } })">对话回放</button>
                <button class="text-[#1677ff] hover:underline text-sm ml-2" @click="router.push({ path: '/report', query: { session_id: r.session_id } })">查看报告</button>
                <button class="text-red-400 hover:underline text-sm ml-2" @click="removeRecord(r.session_id)"><i class="fa fa-trash-o"></i></button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !records.length" class="text-center py-12 text-gray-400">
          <i class="fa fa-inbox text-3xl mb-2 block"></i>暂无面试记录
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 mt-4 text-sm text-gray-500">
        <div class="flex items-center gap-3">
          <span>共 {{ records.length }} 条</span>
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
