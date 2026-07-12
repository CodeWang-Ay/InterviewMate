<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const planList = ref([])
const loading = ref(true)
const searchText = ref('')
const filterStatus = ref('')

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    const qs = params.toString()
    const res = await fetch(`/api/plans${qs ? '?' + qs : ''}`)
    if (res.ok) planList.value = await res.json()
  } catch (_) { /* ignore */ }
  loading.value = false
}

onMounted(fetchList)

async function updateStatus(pid, status) {
  await fetch(`/api/plans/${pid}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) })
  await fetchList()
}

async function removePlan(pid) {
  if (!confirm('确认删除？')) return
  await fetch(`/api/plans/${pid}`, { method: 'DELETE' })
  await fetchList()
}

function createInterview(plan) {
  localStorage.setItem('interviewmate_selected_jd', `岗位：${plan.jd_name}\n候选人：${plan.candidate_name}`)
  router.push('/interviewee')
}

const statusBadge = (s) => ({
  wait: 'bg-blue-50 text-blue-600',
  pending: 'bg-gray-100 text-gray-500',
  running: 'bg-orange-50 text-orange-600',
  finish: 'bg-green-100 text-green-600',
  cancel: 'bg-gray-100 text-gray-500',
}[s] || 'bg-gray-100')

const statusLabel = (s) => ({
  wait: '待发起面试',
  pending: '待前序完成',
  running: '面试中',
  finish: '已完成面试',
  cancel: '已作废',
}[s] || s)

function resetFilters() { searchText.value = ''; filterStatus.value = ''; fetchList() }
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">面试计划管理</h2>
        <div class="flex gap-3">
          <button class="border border-[#1677ff] text-[#1677ff] px-4 py-2 rounded-lg hover:bg-blue-50 text-sm" @click="router.push('/interviewee')">
            <i class="fa fa-file-text-o mr-1"></i>手动新建计划
          </button>
          <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 text-sm" @click="router.push('/interviewee')">
            <i class="fa fa-magic"></i>AI生成面试计划
          </button>
        </div>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-60 relative">
            <input v-model="searchText" type="text" placeholder="候选人姓名 / 岗位名称" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="fetchList">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterStatus" class="border rounded-lg px-3 py-2 min-w-[160px]" @change="fetchList">
            <option value="">全部计划状态</option>
            <option value="wait">待发起面试</option>
            <option value="pending">待前序完成</option>
            <option value="running">面试中</option>
            <option value="finish">已完成面试</option>
            <option value="cancel">已作废</option>
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
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">目标岗位(JD)</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">轮次</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">面试者账号</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">匹配度</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">题目数</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">创建时间</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">状态</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-52">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(p, i) in planList" :key="p.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm text-gray-500">{{ i + 1 }}</td>
              <td class="px-4 py-3 font-medium text-sm">{{ p.candidate_name }}</td>
              <td class="px-4 py-3 text-sm">{{ p.jd_name }}</td>
              <td class="px-4 py-3 text-sm">
                <div class="flex flex-col gap-1">
                  <span class="w-fit px-2 py-1 rounded bg-indigo-50 text-indigo-600 text-xs">{{ p.interview_round || '-' }}</span>
                  <span v-if="p.workflow_name" class="text-xs text-gray-400">{{ p.workflow_name }} · 第 {{ p.stage_order || 1 }}/{{ p.stage_count || 1 }} 环节</span>
                </div>
              </td>
              <td class="px-4 py-3 text-xs text-gray-600">
                <div v-if="p.candidate_username" class="font-mono leading-5">
                  <div>{{ p.candidate_username }}</div>
                  <div class="text-gray-400">{{ p.candidate_password }}</div>
                </div>
                <span v-else>-</span>
              </td>
              <td class="px-4 py-3 font-medium text-sm" :class="p.match_score >= 80 ? 'text-green-600' : p.match_score >= 60 ? 'text-yellow-600' : 'text-red-600'">{{ p.match_score }}%</td>
              <td class="px-4 py-3 text-sm">{{ p.question_count }} 道</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ p.created_at?.slice(0, 16) || '-' }}</td>
              <td class="px-4 py-3"><span :class="['px-2 py-1 text-xs rounded', statusBadge(p.status)]">{{ statusLabel(p.status) }}</span></td>
              <td class="px-4 py-3 text-center">
                <template v-if="p.status === 'wait'">
                  <button class="text-[#1677ff] hover:underline text-sm" @click="router.push({ path: '/report', query: { session_id: p.id } })">预览计划</button>
                  <button class="text-[#1677ff] hover:underline text-sm ml-2">编辑题目</button>
                  <button class="text-[#22c55e] hover:underline text-sm ml-2" @click="createInterview(p)">发起面试</button>
                  <button class="text-red-500 hover:underline text-sm ml-2" @click="updateStatus(p.id, 'cancel')">作废</button>
                </template>
                <template v-else-if="p.status === 'running'">
                  <button class="text-[#1677ff] hover:underline text-sm">预览计划</button>
                  <button class="text-gray-400 text-sm ml-2">编辑题目</button>
                  <button class="text-[#22c55e] hover:underline text-sm ml-2" @click="createInterview(p)">进入面试房间</button>
                  <button class="text-gray-400 text-sm ml-2">作废</button>
                </template>
                <template v-else-if="p.status === 'finish'">
                  <button class="text-[#1677ff] hover:underline text-sm">预览计划</button>
                  <button class="text-gray-400 text-sm ml-2">编辑题目</button>
                  <button class="text-gray-400 text-sm ml-2">发起面试</button>
                  <button class="text-[#1677ff] hover:underline text-sm ml-2" @click="router.push({ path: '/report', query: { session_id: p.id } })">查看面试报告</button>
                </template>
                <template v-else>
                  <button class="text-[#1677ff] hover:underline text-sm">预览计划</button>
                  <button class="text-gray-400 text-sm ml-2">编辑题目</button>
                  <button class="text-[#1677ff] hover:underline text-sm ml-2" @click="updateStatus(p.id, 'wait')">重新发起面试</button>
                </template>
                <button class="text-red-400 hover:underline text-sm ml-2" @click="removePlan(p.id)"><i class="fa fa-trash-o"></i></button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !planList.length" class="text-center py-12 text-gray-400"><i class="fa fa-inbox text-3xl mb-2 block"></i>暂无面试计划</div>
      </div>

      <div class="flex justify-between items-center mt-4 text-sm text-gray-500"><span>共 {{ planList.length }} 条</span></div>
    </main>
  </div>
</template>
