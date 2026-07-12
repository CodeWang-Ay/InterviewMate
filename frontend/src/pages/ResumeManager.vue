<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const resumeList = ref([])
const loading = ref(true)
const uploading = ref(false)
const searchText = ref('')
const filterStatus = ref('')
const filterYears = ref('')

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterStatus.value) params.set('parse_status', filterStatus.value)
    if (filterYears.value) params.set('experience_years', filterYears.value)
    const qs = params.toString()
    const res = await fetch(`/api/resumes${qs ? '?' + qs : ''}`)
    if (res.ok) resumeList.value = await res.json()
  } catch (_) { /* ignore */ }
  loading.value = false
}

onMounted(fetchList)

function onDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

function onFileChange(e) {
  const file = e.target?.files?.[0]
  if (file) uploadFile(file)
}

async function uploadFile(file) {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await fetch('/api/resumes/upload', { method: 'POST', body: fd })
    await fetchList()
  } catch (_) { /* ignore */ }
  uploading.value = false
}

async function parseResume(rid) {
  try {
    await fetch(`/api/resumes/${rid}/parse`, { method: 'POST' })
    await fetchList()
  } catch (_) { /* ignore */ }
}

async function removeResume(rid, name) {
  if (!confirm(`确认删除「${name}」？`)) return
  await fetch(`/api/resumes/${rid}`, { method: 'DELETE' })
  await fetchList()
}

function createInterview(resume) {
  localStorage.setItem('interviewmate_selected_resume', resume.file_path || '')
  router.push('/interviewee')
}

const statusBadge = (status) => ({
  success: 'bg-green-100 text-green-600',
  wait: 'bg-orange-100 text-orange-600',
  fail: 'bg-red-100 text-red-600',
}[status] || 'bg-gray-100 text-gray-500')

const statusLabel = (status) => ({
  success: '解析成功',
  wait: '待解析',
  fail: '解析失败',
}[status] || status)

function resetFilters() {
  searchText.value = ''
  filterStatus.value = ''
  filterYears.value = ''
  fetchList()
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">简历管理</h2>
        <label class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 transition cursor-pointer">
          <i class="fa fa-plus"></i> 上传简历
          <input type="file" accept=".pdf,.docx,.doc,.txt,.md" class="hidden" @change="onFileChange" />
        </label>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-64 relative">
            <input v-model="searchText" type="text" placeholder="搜索候选人姓名、技能、期望岗位" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="fetchList">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterStatus" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="fetchList">
            <option value="">全部解析状态</option>
            <option value="wait">待解析</option>
            <option value="success">解析成功</option>
            <option value="fail">解析失败</option>
          </select>
          <select v-model="filterYears" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="fetchList">
            <option value="">全部工作年限</option>
            <option value="应届生">应届生</option>
            <option value="1-3年">1-3年</option>
            <option value="3-5年">3-5年</option>
            <option value="5年以上">5年以上</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置筛选</button>
        </div>
      </div>

      <!-- 拖拽上传 -->
      <div
        class="border-2 border-dashed border-blue-300 rounded-xl p-8 mb-6 text-center bg-white shadow-sm transition hover:border-[#1677ff] hover:bg-blue-50/30"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <i v-if="uploading" class="fa fa-spinner fa-spin text-4xl text-[#1677ff] mb-3"></i>
        <i v-else class="fa fa-cloud-upload text-4xl text-[#1677ff] mb-3"></i>
        <p class="text-gray-700 text-lg">{{ uploading ? '正在上传...' : '拖拽简历文件到此处快速上传' }}</p>
        <p class="text-gray-400 text-sm mt-1">支持 PDF / DOC / DOCX / TXT，上传后自动启动 AI 简历解析</p>
      </div>

      <!-- 简历卡片列表 -->
      <div v-if="loading" class="text-center py-12 text-gray-400">
        <i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        <div v-for="r in resumeList" :key="r.id" class="bg-white rounded-xl p-5 shadow-sm">
          <div class="flex justify-between items-start mb-3">
            <div>
              <h3 class="font-bold text-lg">{{ r.name || '未命名' }}</h3>
              <span class="text-gray-500 text-sm">{{ r.target_position || '未设定岗位' }}</span>
            </div>
            <span :class="['px-2 py-1 text-xs rounded', statusBadge(r.parse_status)]">{{ statusLabel(r.parse_status) }}</span>
          </div>
          <div class="text-sm text-gray-500 space-y-1 mb-4">
            <p v-if="r.education"><i class="fa fa-graduation-cap mr-1"></i>{{ r.education }}</p>
            <p v-if="r.experience_years"><i class="fa fa-briefcase mr-1"></i>{{ r.experience_years }} 经验</p>
            <p v-if="r.skills" class="line-clamp-2"><i class="fa fa-tags mr-1"></i>{{ r.skills }}</p>
            <p v-if="r.file_path" class="text-gray-400 text-xs"><i class="fa fa-file-text-o mr-1"></i>{{ r.file_path }}</p>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-if="r.parse_status === 'success'"
              class="border border-[#1677ff] text-[#1677ff] py-1.5 rounded text-sm hover:bg-blue-50"
              @click="router.push({ path: '/interview-record', query: { session_id: r.file_path } })"
            >查看详情</button>
            <button
              v-else
              :class="r.parse_status === 'fail' ? 'border border-[#1677ff] text-[#1677ff] py-1.5 rounded text-sm hover:bg-blue-50' : 'border border-orange-400 text-orange-400 py-1.5 rounded text-sm hover:bg-orange-50'"
              @click="parseResume(r.id)"
            >{{ r.parse_status === 'fail' ? '重新解析' : '手动解析' }}</button>
            <button
              v-if="r.parse_status === 'success'"
              class="border border-[#22c55e] text-[#22c55e] py-1.5 rounded text-sm hover:bg-green-50"
              @click="createInterview(r)"
            >匹配岗位JD</button>
            <button
              v-else
              class="border border-gray-300 text-gray-400 py-1.5 rounded text-sm cursor-not-allowed"
              disabled
            >匹配岗位JD</button>
            <button
              v-if="r.parse_status === 'success'"
              class="col-span-2 bg-[#1677ff] text-white py-1.5 rounded text-sm hover:bg-blue-600"
              @click="createInterview(r)"
            >创建面试任务</button>
            <button
              v-else
              class="col-span-2 bg-gray-300 text-gray-500 py-1.5 rounded text-sm cursor-not-allowed"
              disabled
            >创建面试任务</button>
          </div>
          <button class="mt-2 w-full text-red-400 text-xs hover:text-red-500" @click="removeResume(r.id, r.name)">
            <i class="fa fa-trash-o mr-1"></i>删除
          </button>
        </div>
      </div>
      <div v-if="!loading && !resumeList.length" class="text-center py-12 text-gray-400">
        <i class="fa fa-inbox text-3xl mb-2 block"></i>暂无简历，请上传
      </div>

      <div class="flex justify-between items-center mt-6 text-sm text-gray-500">
        <span>共 {{ resumeList.length }} 份简历</span>
      </div>
    </main>
  </div>
</template>
