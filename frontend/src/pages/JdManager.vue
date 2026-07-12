<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const searchText = ref('')
const filterCategory = ref('')
const filterStatus = ref('')
const filterLocation = ref('')
const showModal = ref(false)
const editingJd = ref(null)
const jdList = ref([])
const loading = ref(true)

const form = ref({ name: '', category: '', location: '', responsibilities: '', requirements: '', status: 'enable' })

async function fetchJds() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterCategory.value) params.set('category', filterCategory.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (filterLocation.value) params.set('location', filterLocation.value)
    const qs = params.toString()
    const res = await fetch(`/api/jds${qs ? '?' + qs : ''}`)
    if (res.ok) jdList.value = await res.json()
  } catch (_) { /* ignore */ }
  loading.value = false
}

onMounted(fetchJds)

// 搜索去抖
let searchTimer = null
function onSearchChange() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchJds, 300)
}

const categories = computed(() => [...new Set(jdList.value.map(j => j.category))].filter(Boolean))
const locations = computed(() => [...new Set(jdList.value.map(j => j.location))].filter(Boolean))

function openCreate() {
  editingJd.value = null
  form.value = { name: '', category: '', location: '', responsibilities: '', requirements: '', status: 'enable' }
  showModal.value = true
}

function openEdit(jd) {
  editingJd.value = jd
  form.value = { ...jd }
  showModal.value = true
}

async function saveJd() {
  if (!form.value.name.trim()) return
  const payload = { ...form.value }
  try {
    if (editingJd.value) {
      await fetch(`/api/jds/${editingJd.value.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } else {
      await fetch('/api/jds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    }
    showModal.value = false
    await fetchJds()
  } catch (_) { /* ignore */ }
}

async function removeJd(jd) {
  if (!confirm(`确认删除「${jd.name}」？`)) return
  try {
    await fetch(`/api/jds/${jd.id}`, { method: 'DELETE' })
    await fetchJds()
  } catch (_) { /* ignore */ }
}

function createInterview(jd) {
  const jdText = `岗位名称：${jd.name}\n岗位类别：${jd.category}\n工作地点：${jd.location}\n\n岗位职责：\n${jd.responsibilities}\n\n任职要求：\n${jd.requirements}`
  localStorage.setItem('interviewmate_selected_jd', jdText)
  router.push('/interviewee')
}

function resetFilters() {
  searchText.value = ''
  filterCategory.value = ''
  filterStatus.value = ''
  filterLocation.value = ''
  fetchJds()
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">岗位 JD 管理</h2>
        <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 transition" @click="openCreate">
          <i class="fa fa-plus"></i> 新增岗位JD
        </button>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-60 relative">
            <input v-model="searchText" type="text" placeholder="搜索岗位名称" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="onSearchChange">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterCategory" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="fetchJds">
            <option value="">全部岗位类别</option>
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
          <select v-model="filterStatus" class="border rounded-lg px-3 py-2 min-w-[140px]" @change="fetchJds">
            <option value="">全部状态</option>
            <option value="enable">启用</option>
            <option value="disable">停用</option>
          </select>
          <select v-model="filterLocation" class="border rounded-lg px-3 py-2 min-w-[140px]" @change="fetchJds">
            <option value="">全部工作地点</option>
            <option v-for="l in locations" :key="l" :value="l">{{ l }}</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置</button>
        </div>
      </div>

      <!-- JD 表格 -->
      <div class="bg-white rounded-xl shadow-sm overflow-hidden">
        <div v-if="loading" class="text-center py-12 text-gray-400">
          <i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...
        </div>
        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm w-12">#</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">岗位名称</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">岗位类别</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">工作地点</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">岗位职责</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">状态</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-44">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(jd, i) in jdList" :key="jd.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm text-gray-500">{{ i + 1 }}</td>
              <td class="px-4 py-3 font-medium text-sm">{{ jd.name }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ jd.category }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ jd.location }}</td>
              <td class="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">{{ jd.responsibilities?.slice(0, 50) }}...</td>
              <td class="px-4 py-3">
                <span :class="jd.status === 'enable' ? 'bg-green-100 text-green-600' : 'bg-orange-100 text-orange-600'" class="px-2 py-1 text-xs rounded">
                  {{ jd.status === 'enable' ? '启用' : '停用' }}
                </span>
              </td>
              <td class="px-4 py-3 text-center">
                <button class="text-[#1677ff] hover:underline text-sm" @click="openEdit(jd)">编辑</button>
                <button class="text-red-500 hover:underline text-sm ml-2" @click="removeJd(jd)">删除</button>
                <button v-if="jd.status === 'enable'" class="text-[#22c55e] hover:underline text-sm ml-2" @click="createInterview(jd)">创建面试</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !jdList.length" class="text-center py-12 text-gray-400">
          <i class="fa fa-inbox text-3xl mb-2 block"></i>暂无匹配的岗位 JD
        </div>
      </div>

      <div class="flex justify-between items-center mt-4 text-sm text-gray-500">
        <span>共 {{ jdList.length }} 条</span>
      </div>
    </main>

    <!-- 新增/编辑弹窗 -->
    <div v-if="showModal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showModal = false">
      <div class="bg-white rounded-2xl w-[600px] max-h-[80vh] overflow-auto p-6 shadow-xl">
        <h3 class="text-lg font-bold mb-5">{{ editingJd ? '编辑岗位JD' : '新增岗位JD' }}</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">岗位名称 <span class="text-red-500">*</span></label>
            <input v-model="form.name" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：后端开发工程师">
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">岗位类别</label>
              <input v-model="form.category" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：技术开发">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">工作地点</label>
              <input v-model="form.location" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：深圳">
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">岗位职责</label>
            <textarea v-model="form.responsibilities" rows="4" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="描述岗位职责..."></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">任职要求</label>
            <textarea v-model="form.requirements" rows="4" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="描述任职要求..."></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
            <select v-model="form.status" class="border rounded-lg px-3 py-2">
              <option value="enable">启用</option>
              <option value="disable">停用</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200" @click="showModal = false">取消</button>
          <button class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600" @click="saveJd">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
