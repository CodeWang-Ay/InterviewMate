<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const records = ref([])
const loading = ref(true)
const searchText = ref('')
const filterType = ref('')
const filterConclusion = ref('')

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterType.value) params.set('record_type', filterType.value)
    if (filterConclusion.value) params.set('conclusion', filterConclusion.value)
    const qs = params.toString()
    const res = await fetch(`/api/records${qs ? '?' + qs : ''}`)
    if (res.ok) records.value = await res.json()
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

const scoreColor = (s) => {
  if (s === null || s === undefined) return 'text-gray-400'
  if (s >= 80) return 'text-green-600'
  if (s >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

function resetFilters() { searchText.value = ''; filterType.value = ''; filterConclusion.value = ''; fetchList() }
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">面试记录</h2>
        <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 text-sm" @click="router.push('/interviewee')">
          <i class="fa fa-plus"></i> 新建面试
        </button>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-64 relative">
            <input v-model="searchText" type="text" placeholder="搜索候选人姓名" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="fetchList">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterType" class="border rounded-lg px-3 py-2 min-w-[170px]" @change="fetchList">
            <option value="">全部面试类型</option>
            <option value="formal">正式面试（基于面试计划）</option>
            <option value="simulate">求职者模拟面试</option>
          </select>
          <select v-model="filterConclusion" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="fetchList">
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
            <tr v-for="(r, i) in records" :key="r.session_id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm text-gray-500">{{ i + 1 }}</td>
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
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !records.length" class="text-center py-12 text-gray-400">
          <i class="fa fa-inbox text-3xl mb-2 block"></i>暂无面试记录
        </div>
      </div>

      <div class="flex justify-between items-center mt-4 text-sm text-gray-500"><span>共 {{ records.length }} 条</span></div>
    </main>
  </div>
</template>
