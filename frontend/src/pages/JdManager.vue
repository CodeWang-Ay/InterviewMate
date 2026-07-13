<script setup>
import { ref, computed, onMounted } from 'vue'
import Sidebar from '../components/Sidebar.vue'

const searchText = ref('')
const filterCategory = ref('')
const filterStatus = ref('')
const filterLocation = ref('')
const filterRecruitment = ref('')
const showModal = ref(false)
const editingJd = ref(null)
const jdList = ref([])
const loading = ref(true)
const viewingJd = ref(null)
const page = ref(1)
const total = ref(0)
const pageSize = ref(10)
const batchMode = ref(false)
const selectedJdIds = ref(new Set())
const batchWorking = ref(false)

const form = ref({ name: '', category: '', location: '', responsibilities: '', requirements: '', status: 'enable', recruitment_type: '社招', experience_required: '' })

// 统计数据
const stats = ref({ total: 0, enabled: 0, disabled: 0, categories: 0, interns: 0, campus: 0, social: 0 })

async function fetchStats() {
  try {
    const res = await fetch('/api/jds/stats')
    if (res.ok) stats.value = await res.json()
  } catch (_) {}
}

async function fetchJds() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterCategory.value) params.set('category', filterCategory.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (filterLocation.value) params.set('location', filterLocation.value)
    if (filterRecruitment.value) params.set('recruitment_type', filterRecruitment.value)
    params.set('page', page.value)
    params.set('page_size', pageSize.value)
    const qs = params.toString()
    const res = await fetch(`/api/jds${qs ? '?' + qs : ''}`)
    if (res.ok) {
      const data = await res.json()
      jdList.value = data.items
      total.value = data.total
    }
  } catch (_) {}
  loading.value = false
}

onMounted(() => { fetchStats(); fetchJds() })

let searchTimer = null
function onSearchChange() { clearTimeout(searchTimer); searchTimer = setTimeout(fetchJds, 300) }

const categories = computed(() => [...new Set(jdList.value.map(j => j.category))].filter(Boolean))
const locations = computed(() => [...new Set(jdList.value.map(j => j.location))].filter(Boolean))
const selectedJds = computed(() => jdList.value.filter(jd => selectedJdIds.value.has(jd.id)))
const allSelected = computed(() => jdList.value.length > 0 && jdList.value.every(jd => selectedJdIds.value.has(jd.id)))

function setSelectedJd(jdId, value) {
  const next = new Set(selectedJdIds.value)
  if (value) next.add(jdId)
  else next.delete(jdId)
  selectedJdIds.value = next
}

function toggleBatchMode() {
  batchMode.value = !batchMode.value
  selectedJdIds.value = new Set()
}

function toggleSelectAll() {
  selectedJdIds.value = allSelected.value ? new Set() : new Set(jdList.value.map(jd => jd.id))
}

function openCreate() {
  editingJd.value = null
  form.value = { name: '', category: '', location: '', responsibilities: '', requirements: '', status: 'enable', recruitment_type: '社招', experience_required: '' }
  showModal.value = true
}

function openEdit(jd) {
  editingJd.value = jd
  form.value = { ...jd }
  showModal.value = true
}

function viewJd(jd) { viewingJd.value = jd }

async function saveJd() {
  if (!form.value.name.trim()) return
  const payload = { ...form.value }
  try {
    if (editingJd.value) {
      await fetch(`/api/jds/${editingJd.value.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    } else {
      await fetch('/api/jds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    }
    showModal.value = false
    await fetchJds()
  } catch (_) {}
}

async function removeJd(jd) {
  if (!confirm(`确认删除「${jd.name}」？`)) return
  await fetch(`/api/jds/${jd.id}`, { method: 'DELETE' })
  await fetchJds()
}

async function updateSelectedStatus(status) {
  const targets = selectedJds.value
  if (!targets.length) return
  batchWorking.value = true
  for (const jd of targets) {
    await fetch(`/api/jds/${jd.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    }).catch(() => {})
  }
  selectedJdIds.value = new Set()
  batchWorking.value = false
  await fetchStats()
  await fetchJds()
}

async function deleteSelectedJds() {
  const targets = selectedJds.value
  if (!targets.length) return
  if (!confirm(`确认删除选中的 ${targets.length} 个岗位 JD？`)) return
  batchWorking.value = true
  for (const jd of targets) {
    await fetch(`/api/jds/${jd.id}`, { method: 'DELETE' }).catch(() => {})
  }
  selectedJdIds.value = new Set()
  batchWorking.value = false
  await fetchStats()
  await fetchJds()
}

function resetFilters() {
  searchText.value = ''; filterCategory.value = ''; filterStatus.value = ''; filterLocation.value = ''; filterRecruitment.value = ''
  page.value = 1
  fetchJds()
}

function goPage(p) {
  page.value = p
  fetchJds()
}

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

function changePageSize(size) {
  pageSize.value = size
  page.value = 1
  fetchJds()
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">岗位 JD 管理</h2>
        <div class="flex items-center gap-3">
          <button
            :class="['px-4 py-2 rounded-lg flex items-center gap-2 transition text-sm border', batchMode ? 'border-orange-300 bg-orange-50 text-orange-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50']"
            @click="toggleBatchMode"
          >
            <i class="fa fa-check-square-o"></i>{{ batchMode ? '退出批量' : '批量管理' }}
          </button>
          <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 transition text-sm" @click="openCreate">
            <i class="fa fa-plus"></i> 新增岗位JD
          </button>
        </div>
      </div>

      <div v-if="batchMode" class="bg-white rounded-xl p-4 shadow-sm mb-6 border border-orange-100 flex flex-wrap items-center justify-between gap-3">
        <div class="text-sm text-gray-600">
          已选择 <span class="font-semibold text-orange-600">{{ selectedJds.length }}</span> 个岗位 JD
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button class="px-3 py-2 rounded-lg border border-gray-200 text-sm hover:bg-gray-50" @click="toggleSelectAll">{{ allSelected ? '取消全选' : '全选当前页' }}</button>
          <button class="px-3 py-2 rounded-lg border border-green-200 text-green-600 text-sm hover:bg-green-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedJds.length" @click="updateSelectedStatus('enable')"><i class="fa fa-check-circle mr-1"></i>批量启用</button>
          <button class="px-3 py-2 rounded-lg border border-orange-200 text-orange-600 text-sm hover:bg-orange-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedJds.length" @click="updateSelectedStatus('disable')"><i class="fa fa-pause-circle mr-1"></i>批量停用</button>
          <button class="px-3 py-2 rounded-lg border border-red-200 text-red-500 text-sm hover:bg-red-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedJds.length" @click="deleteSelectedJds"><i class="fa fa-trash-o mr-1"></i>批量删除</button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-xl p-4 shadow-sm text-center">
          <p class="text-2xl font-bold text-[#1677ff]">{{ stats.total }}</p>
          <p class="text-xs text-gray-500 mt-1">全部 JD</p>
        </div>
        <div class="bg-white rounded-xl p-4 shadow-sm text-center">
          <p class="text-2xl font-bold text-[#22c55e]">{{ stats.enabled }}</p>
          <p class="text-xs text-gray-500 mt-1">启用中</p>
        </div>
        <div class="bg-white rounded-xl p-4 shadow-sm text-center">
          <p class="text-2xl font-bold text-purple-500">{{ stats.categories }}</p>
          <p class="text-xs text-gray-500 mt-1">岗位类别</p>
        </div>
        <div class="bg-white rounded-xl p-4 shadow-sm text-center">
          <div class="flex items-center justify-center gap-2">
            <span class="text-lg font-bold text-green-600">{{ stats.interns }}</span>
            <span class="text-lg font-bold text-blue-600">{{ stats.campus }}</span>
            <span class="text-lg font-bold text-purple-600">{{ stats.social }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-1">实习生 / 校招 / 社招</p>
        </div>
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
          <select v-model="filterRecruitment" class="border rounded-lg px-3 py-2 min-w-[120px]" @change="fetchJds">
            <option value="">全部招聘类型</option>
            <option value="实习生">实习生</option>
            <option value="校招">校招</option>
            <option value="社招">社招</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置</button>
        </div>
      </div>

      <!-- JD 表格 -->
      <div class="bg-white rounded-xl shadow-sm overflow-hidden">
        <div v-if="loading" class="text-center py-12 text-gray-400"><i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...</div>
        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th v-if="batchMode" class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-10">
                <input type="checkbox" :checked="allSelected" @change="toggleSelectAll">
              </th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm w-8">#</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">岗位名称</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">岗位类别</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">招聘类型</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">经验要求</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">工作地点</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">状态</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-36">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(jd, i) in jdList" :key="jd.id" class="hover:bg-gray-50">
              <td v-if="batchMode" class="px-4 py-3 text-center">
                <input type="checkbox" :checked="selectedJdIds.has(jd.id)" @change="setSelectedJd(jd.id, $event.target.checked)">
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ i + 1 }}</td>
              <td class="px-4 py-3 font-medium text-sm">{{ jd.name }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ jd.category }}</td>
              <td class="px-4 py-3 text-sm">
                <span :class="{'实习生':'bg-green-100 text-green-600','校招':'bg-blue-100 text-blue-600','社招':'bg-purple-100 text-purple-600'}[jd.recruitment_type] || 'bg-blue-100 text-blue-600'" class="px-2 py-0.5 text-xs rounded font-medium">{{ jd.recruitment_type || '社招' }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ jd.experience_required || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ jd.location }}</td>
              <td class="px-4 py-3">
                <span :class="jd.status === 'enable' ? 'bg-green-100 text-green-600' : 'bg-orange-100 text-orange-600'" class="px-2 py-1 text-xs rounded">{{ jd.status === 'enable' ? '启用' : '停用' }}</span>
              </td>
              <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center gap-1">
                  <button class="w-8 h-8 rounded-lg text-[#1677ff] hover:bg-blue-50 transition flex items-center justify-center" title="查看" @click="viewJd(jd)"><i class="fa fa-eye"></i></button>
                  <button class="w-8 h-8 rounded-lg text-gray-500 hover:bg-gray-100 transition flex items-center justify-center" title="编辑" @click="openEdit(jd)"><i class="fa fa-pencil"></i></button>
                  <button class="w-8 h-8 rounded-lg text-red-400 hover:bg-red-50 transition flex items-center justify-center" title="删除" @click="removeJd(jd)"><i class="fa fa-trash-o"></i></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !jdList.length" class="text-center py-12 text-gray-400"><i class="fa fa-inbox text-3xl mb-2 block"></i>暂无匹配的岗位 JD</div>
      </div>

      <!-- 分页 -->
      <div class="flex justify-between items-center mt-4">
        <div class="flex items-center gap-3">
          <span class="text-sm text-gray-500">共 {{ total }} 条</span>
          <select v-model.number="pageSize" class="border rounded-lg px-2 py-1 text-xs text-gray-500" @change="page = 1; fetchJds()">
            <option :value="10">10条/页</option>
            <option :value="20">20条/页</option>
            <option :value="50">50条/页</option>
          </select>
        </div>
        <div class="flex gap-1">
          <button :disabled="page <= 1" class="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-30 hover:bg-gray-50" @click="goPage(page - 1)">上一页</button>
          <button
            v-for="p in totalPages"
            :key="p"
            :class="['px-3 py-1.5 border rounded-lg text-sm', p === page ? 'bg-[#1677ff] text-white border-[#1677ff]' : 'hover:bg-gray-50']"
            @click="goPage(p)"
          >{{ p }}</button>
          <button :disabled="page >= totalPages" class="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-30 hover:bg-gray-50" @click="goPage(page + 1)">下一页</button>
        </div>
      </div>
    </main>

    <!-- 新增/编辑弹窗 -->
    <div v-if="showModal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showModal = false">
      <div class="bg-white rounded-2xl w-[600px] max-h-[80vh] overflow-auto p-6 shadow-xl">
        <h3 class="text-lg font-bold mb-5">{{ editingJd ? '编辑岗位JD' : '新增岗位JD' }}</h3>
        <div class="space-y-4">
          <div><label class="block text-sm font-medium text-gray-700 mb-1">岗位名称 <span class="text-red-500">*</span></label><input v-model="form.name" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：后端开发工程师"></div>
          <div class="grid grid-cols-2 gap-4">
            <div><label class="block text-sm font-medium text-gray-700 mb-1">岗位类别</label><input v-model="form.category" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：技术开发"></div>
            <div><label class="block text-sm font-medium text-gray-700 mb-1">工作地点</label><input v-model="form.location" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：深圳"></div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">招聘类型</label>
              <select v-model="form.recruitment_type" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
                <option value="实习生">实习生</option>
                <option value="校招">校招</option>
                <option value="社招">社招</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">经验要求</label>
              <input v-model="form.experience_required" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：3-5年">
            </div>
          </div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">岗位职责</label><textarea v-model="form.responsibilities" rows="4" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="描述岗位职责..."></textarea></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">任职要求</label><textarea v-model="form.requirements" rows="4" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="描述任职要求..."></textarea></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">状态</label><select v-model="form.status" class="border rounded-lg px-3 py-2"><option value="enable">启用</option><option value="disable">停用</option></select></div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="showModal = false">取消</button>
          <button class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600 text-sm" @click="saveJd">保存</button>
        </div>
      </div>
    </div>

    <!-- 查看 JD 弹窗 -->
    <div v-if="viewingJd" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="viewingJd = null">
      <div class="bg-white rounded-2xl w-[640px] max-h-[80vh] overflow-auto p-6 shadow-xl">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-lg font-bold">{{ viewingJd.name }}</h3>
          <span :class="viewingJd.status === 'enable' ? 'bg-green-100 text-green-600' : 'bg-orange-100 text-orange-600'" class="px-2 py-1 text-xs rounded">{{ viewingJd.status === 'enable' ? '启用' : '停用' }}</span>
        </div>
        <div class="space-y-4">
          <div class="flex gap-4 text-sm text-gray-500">
            <span><i class="fa fa-tag mr-1"></i>{{ viewingJd.category || '-' }}</span>
            <span><i class="fa fa-map-marker mr-1"></i>{{ viewingJd.location || '-' }}</span>
            <span :class="{'实习生':'bg-green-100 text-green-600','校招':'bg-blue-100 text-blue-600','社招':'bg-purple-100 text-purple-600'}[viewingJd.recruitment_type]" class="px-2 py-0.5 text-xs rounded font-medium">{{ viewingJd.recruitment_type || '社招' }}</span>
            <span class="text-gray-500">{{ viewingJd.experience_required ? viewingJd.experience_required + ' 经验' : '' }}</span>
          </div>
          <div>
            <h4 class="text-sm font-semibold text-gray-700 mb-2">岗位职责</h4>
            <p class="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{{ viewingJd.responsibilities || '暂无' }}</p>
          </div>
          <div>
            <h4 class="text-sm font-semibold text-gray-700 mb-2">任职要求</h4>
            <p class="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{{ viewingJd.requirements || '暂无' }}</p>
          </div>
        </div>
        <div class="flex justify-end mt-6">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="viewingJd = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>
