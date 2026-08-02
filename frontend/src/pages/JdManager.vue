<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import Sidebar from '../components/Sidebar.vue'
import FixedSelect from '../components/FixedSelect.vue'

const searchText = ref('')
const filterCategory = ref('')
const filterStatus = ref('')
const filterArchive = ref('')
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
const selectedAllResults = ref(false)
const allResultJds = ref([])
const batchWorking = ref(false)
const exportFormat = ref('csv')
const showExportPicker = ref(false)
const viewMode = ref('list')
const showGenerator = ref(false)
const generatingDraft = ref(false)
const optimizingDraft = ref(false)
const savingOptimized = ref(false)
const editingOptimized = ref(false)
const optimizeSource = ref(null)
const optimizedDraft = ref(null)
const versionJd = ref(null)
const versionDetail = ref(null)
const jdVersions = ref([])
const loadingVersions = ref(false)
const restoringVersion = ref(false)
const activeLocationPicker = ref('')
const activeActionMenu = ref(null)
const generatorForm = ref({ name: '', summary: '', category: '', location: '', recruitment_type: '社招' })
const copySource = ref(null)
const copyForm = ref({ name: '', recruitment_type: '社招', experience_required: '不限经验', status: 'draft' })

const jobCategoryOptions = ['技术', '产品', '政企', '销售', '综合']
const recruitmentTypeLocked = computed(() => Boolean(editingJd.value && (Number(editingJd.value.application_count || 0) > 0 || editingJd.value.status !== 'draft')))
const experienceOptions = ['不限经验', '应届生', '1-3年', '3-5年', '5-10年', '10年以上']
const form = ref({ name: '', category: '', location: '', responsibilities: '', requirements: '', status: 'enable', recruitment_type: '社招', experience_required: '不限经验' })
const popularCities = ['深圳', '上海', '北京', '广州', '杭州', '成都', '苏州', '南京', '武汉', '西安']

// 统计数据
const stats = ref({ total: 0, archived: 0, enabled: 0, disabled: 0, categories: 0, interns: 0, campus: 0, social: 0 })

async function fetchStats() {
  try {
    const res = await fetch('/api/jds/stats')
    if (res.ok) stats.value = await res.json()
  } catch (_) {}
}

async function fetchJds() {
  loading.value = true
  selectedAllResults.value = false
  allResultJds.value = []
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterCategory.value) params.set('category', filterCategory.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (filterArchive.value) params.set('archived', filterArchive.value)
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

// 筛选项不能从当前分页数据推导，否则某个类别只出现在其他页时会被漏掉。
// 使用统一类别字典，筛选请求仍由后端对全部 JD 执行。
const categories = computed(() => jobCategoryOptions)
const locations = computed(() => [...new Set(jdList.value.map(j => j.location))].filter(Boolean))
const selectedJds = computed(() => selectedAllResults.value ? allResultJds.value : jdList.value.filter(jd => selectedJdIds.value.has(jd.id)))
const allSelected = computed(() => jdList.value.length > 0 && jdList.value.every(jd => selectedJdIds.value.has(jd.id)))
const statCards = computed(() => [
  {
    label: '全部 JD',
    value: stats.value.total,
    icon: 'fa-briefcase',
    accent: 'from-[#2f7cff] to-[#7aa7ff]',
    soft: 'bg-blue-50 text-[#1f6fff]',
    note: `${stats.value.enabled} 个正在启用`,
  },
  {
    label: '启用中',
    value: stats.value.enabled,
    icon: 'fa-check-circle',
    accent: 'from-[#21c77a] to-[#86e7b6]',
    soft: 'bg-emerald-50 text-[#19a463]',
    note: stats.value.disabled ? `${stats.value.disabled} 个已停用` : '当前无停用 JD',
  },
  {
    label: '岗位类别',
    value: stats.value.categories,
    icon: 'fa-tags',
    accent: 'from-[#8b5cf6] to-[#c4a7ff]',
    soft: 'bg-violet-50 text-[#7c3aed]',
    note: '覆盖不同招聘方向',
  },
  {
    label: '已归档',
    value: stats.value.archived,
    icon: 'fa-archive',
    accent: 'from-[#94a3b8] to-[#cbd5e1]',
    soft: 'bg-slate-100 text-slate-500',
    note: '历史岗位，不计入正常 JD',
  },
])
const compareFields = [
  { key: 'name', label: '岗位名称' },
  { key: 'category', label: '岗位类别' },
  { key: 'location', label: '工作地点' },
  { key: 'recruitment_type', label: '招聘类型' },
  { key: 'experience_required', label: '经验要求' },
  { key: 'responsibilities', label: '岗位职责' },
  { key: 'requirements', label: '任职要求' },
]

function getRecruitmentBadgeClass(type) {
  return {
    实习生: 'bg-green-100 text-green-600',
    校招: 'bg-blue-100 text-blue-600',
    社招: 'bg-purple-100 text-purple-600',
  }[type] || 'bg-blue-100 text-blue-600'
}

function getStatusBadgeClass(status) {
  return ({ draft: 'bg-slate-100 text-slate-600', published: 'bg-green-100 text-green-600', enable: 'bg-green-100 text-green-600', paused: 'bg-amber-100 text-amber-700', disable: 'bg-amber-100 text-amber-700', expired: 'bg-gray-100 text-gray-500', closed: 'bg-red-100 text-red-600' }[status] || 'bg-gray-100 text-gray-500')
}

function statusLabel(status) {
  return ({ draft: '草稿', published: '已发布', enable: '已发布', paused: '已暂停', disable: '已暂停', expired: '已过期', closed: '已关闭' }[status] || status || '草稿')
}

function formatPublishTime(jd) {
  const value = jd?.published_at || jd?.created_at || jd?.updated_at || ''
  return value ? String(value).replace('T', ' ').slice(0, 16) : '-'
}

function getResponsibilityPreview(jd) {
  const source = (jd.responsibilities || jd.requirements || '').trim()
  return source ? source.slice(0, 120) + (source.length > 120 ? '...' : '') : '暂未填写岗位职责与要求'
}

function setFilterLocation(city) {
  filterLocation.value = city
  fetchJds()
}

function setFormLocation(city) {
  form.value.location = city
}

function setGeneratorLocation(city) {
  generatorForm.value.location = city
}

function toggleLocationPicker(name) {
  activeLocationPicker.value = activeLocationPicker.value === name ? '' : name
}

function toggleActionMenu(id) {
  activeActionMenu.value = activeActionMenu.value === id ? null : id
}

function closeActionMenu() {
  activeActionMenu.value = null
}

function handleActionMenuOutside(event) {
  if (!event.target.closest?.('[data-jd-action-menu]')) closeActionMenu()
}

onMounted(() => document.addEventListener('click', handleActionMenuOutside))
onBeforeUnmount(() => document.removeEventListener('click', handleActionMenuOutside))

function pickLocation(target, city) {
  if (target === 'filter') setFilterLocation(city)
  if (target === 'form') setFormLocation(city)
  if (target === 'generator') setGeneratorLocation(city)
  activeLocationPicker.value = ''
}

function locationOptionClass(current, city) {
  return [
    'h-8 whitespace-nowrap rounded-full px-3 text-xs font-medium transition',
    current === city
      ? 'bg-[#1677ff] text-white shadow-sm shadow-blue-100'
      : 'bg-white text-[#536176] ring-1 ring-[#dbe5f2] hover:bg-[#eef5ff] hover:text-[#1677ff] hover:ring-[#bcd5ff]'
  ]
}

function setSelectedJd(jdId, value) {
  selectedAllResults.value = false
  const next = new Set(selectedJdIds.value)
  if (value) next.add(jdId)
  else next.delete(jdId)
  selectedJdIds.value = next
}

function toggleBatchMode() {
  batchMode.value = !batchMode.value
  selectedJdIds.value = new Set()
  selectedAllResults.value = false
  allResultJds.value = []
}

function toggleSelectAll() {
  selectedAllResults.value = false
  selectedJdIds.value = allSelected.value ? new Set() : new Set(jdList.value.map(jd => jd.id))
}

async function selectAllResults() {
  if (selectedAllResults.value) {
    selectedAllResults.value = false; selectedJdIds.value = new Set(); allResultJds.value = []; return
  }
  const params = new URLSearchParams({ page: '1', page_size: '10000' })
  if (searchText.value) params.set('search', searchText.value)
  if (filterCategory.value) params.set('category', filterCategory.value)
  if (filterStatus.value) params.set('status', filterStatus.value)
  if (filterLocation.value) params.set('location', filterLocation.value)
  if (filterRecruitment.value) params.set('recruitment_type', filterRecruitment.value)
  const res = await fetch(`/api/jds?${params.toString()}`)
  if (!res.ok) return
  const data = await res.json()
  allResultJds.value = data.items || []
  selectedJdIds.value = new Set(allResultJds.value.map(jd => jd.id))
  selectedAllResults.value = true
}

function openCreate() {
  editingJd.value = null
  form.value = { name: '', category: '综合', location: '', responsibilities: '', requirements: '', status: 'enable', recruitment_type: '社招', experience_required: '不限经验' }
  showModal.value = true
}

function openGenerator() {
  generatorForm.value = { name: '', summary: '', category: '', location: '', recruitment_type: '社招' }
  showGenerator.value = true
}

function openEdit(jd) {
  editingJd.value = jd
  form.value = { ...jd, category: jobCategoryOptions.includes(jd.category) ? jd.category : '综合', experience_required: experienceOptions.includes(jd.experience_required) ? jd.experience_required : '不限经验' }
  showModal.value = true
}

async function viewJd(jd) {
  viewingJd.value = jd
  try {
    const res = await fetch(`/api/jds/${jd.id}`)
    if (res.ok) viewingJd.value = await res.json()
  } catch (_) {}
}

function closeOptimize(force = false) {
  if (!force && (optimizingDraft.value || savingOptimized.value)) return
  optimizeSource.value = null
  optimizedDraft.value = null
  editingOptimized.value = false
}

async function saveJd() {
  if (!form.value.name.trim()) return
  const payload = { ...form.value }
  try {
    if (payload.status !== 'draft' && (!payload.responsibilities.trim() || !payload.requirements.trim())) {
      alert('发布前请先填写岗位职责和任职要求')
      return
    }
    if (editingJd.value) {
      const res = await fetch(`/api/jds/${editingJd.value.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      if (!res.ok) { const data = await res.json().catch(() => ({})); throw new Error(data.detail || '保存失败') }
    } else {
      const res = await fetch('/api/jds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      if (!res.ok) { const data = await res.json().catch(() => ({})); throw new Error(data.detail || '保存失败') }
    }
    showModal.value = false
    await fetchJds()
  } catch (error) { alert(error?.message || '保存失败') }
}

function openCopy(jd) {
  copySource.value = jd
  copyForm.value = { name: jd?.name || '', recruitment_type: jd?.recruitment_type || '社招', experience_required: jd?.experience_required || '不限经验', status: 'draft' }
}

async function copyJdInfo(jd) {
  if (!jd) return
  const text = [
    `岗位名称：${jd.name || '-'}`,
    `岗位类别：${jd.category || '-'}`,
    `工作地点：${jd.location || '-'}`,
    `招聘类型：${jd.recruitment_type || '-'}`,
    `经验要求：${jd.experience_required || '-'}`,
    '',
    '岗位职责：',
    jd.responsibilities || '暂无',
    '',
    '任职要求：',
    jd.requirements || '暂无',
  ].join('\n')
  try {
    await navigator.clipboard.writeText(text)
    alert('JD 信息已复制')
  } catch (_) {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    textarea.remove()
    alert('JD 信息已复制')
  }
}

async function confirmCopy() {
  if (!copySource.value || !copyForm.value.name.trim()) return
  const source = copySource.value
  try {
    const res = await fetch(`/api/jds/${source.id}/duplicate`, { method: 'POST' })
    const created = await res.json().catch(() => ({}))
    if (!res.ok || !created?.id) throw new Error(created.detail || '复制 JD 失败')
    const updateRes = await fetch(`/api/jds/${created.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: copyForm.value.name.trim(), recruitment_type: copyForm.value.recruitment_type, experience_required: copyForm.value.experience_required, status: copyForm.value.status }) })
    if (!updateRes.ok) throw new Error('复制后的 JD 保存失败')
    copySource.value = null
    await fetchStats(); page.value = 1; await fetchJds()
  } catch (error) {
    alert(error?.message || '复制 JD 失败')
  }
}

async function generateDraft() {
  if (!generatorForm.value.name.trim()) return
  generatingDraft.value = true
  try {
    const res = await fetch('/api/jds/generate-draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(generatorForm.value),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      alert(data.detail || 'JD 生成失败')
      return
    }
    form.value = {
      name: data.name || generatorForm.value.name,
      category: data.category || generatorForm.value.category,
      location: data.location || generatorForm.value.location,
      responsibilities: data.responsibilities || '',
      requirements: data.requirements || '',
      status: data.status || 'enable',
      recruitment_type: data.recruitment_type || generatorForm.value.recruitment_type,
      experience_required: experienceOptions.includes(data.experience_required) ? data.experience_required : '不限经验',
    }
    editingJd.value = null
    showGenerator.value = false
    showModal.value = true
  } catch (e) {
    alert('JD 生成失败: ' + e.message)
  } finally {
    generatingDraft.value = false
  }
}

async function openOptimize(jd) {
  viewingJd.value = null
  showModal.value = false
  optimizeSource.value = jd
  optimizedDraft.value = null
  optimizingDraft.value = true
  try {
    const res = await fetch(`/api/jds/${jd.id}/optimize-draft`, { method: 'POST' })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      alert(data.detail || 'JD 优化失败')
      closeOptimize(true)
      return
    }
    optimizedDraft.value = data
  } catch (e) {
    alert('JD 优化失败: ' + e.message)
    closeOptimize(true)
  } finally {
    optimizingDraft.value = false
  }
}

function toggleOptimizedEdit() {
  if (!optimizedDraft.value) return
  editingOptimized.value = !editingOptimized.value
}

async function acceptOptimizedJd() {
  if (!optimizeSource.value || !optimizedDraft.value) return
  savingOptimized.value = true
  const payload = {
    name: optimizedDraft.value.name || optimizeSource.value.name,
    category: jobCategoryOptions.includes(optimizedDraft.value.category) ? optimizedDraft.value.category : (jobCategoryOptions.includes(optimizeSource.value.category) ? optimizeSource.value.category : '综合'),
    location: optimizedDraft.value.location || '',
    responsibilities: optimizedDraft.value.responsibilities || '',
    requirements: optimizedDraft.value.requirements || '',
    status: optimizedDraft.value.status || optimizeSource.value.status || 'enable',
    recruitment_type: optimizedDraft.value.recruitment_type || '社招',
    experience_required: experienceOptions.includes(optimizedDraft.value.experience_required) ? optimizedDraft.value.experience_required : '不限经验',
  }
  try {
    const res = await fetch(`/api/jds/${optimizeSource.value.id}?source=ai_optimize`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      alert(data.detail || '采纳优化失败')
      return
    }
    closeOptimize(true)
    viewingJd.value = null
    await fetchStats()
    await fetchJds()
    alert('JD 优化内容已保存并写入数据库')
  } catch (e) {
    alert('采纳优化失败: ' + e.message)
  } finally {
    savingOptimized.value = false
  }
}

async function openVersions(jd) {
  viewingJd.value = null
  showModal.value = false
  versionJd.value = jd
  jdVersions.value = []
  loadingVersions.value = true
  try {
    const res = await fetch(`/api/jds/${jd.id}/versions`)
    const data = await res.json().catch(() => [])
    if (!res.ok) {
      alert(data.detail || '获取版本记录失败')
      versionJd.value = null
      return
    }
    jdVersions.value = data
  } finally {
    loadingVersions.value = false
  }
}

async function restoreVersion(version) {
  if (!versionJd.value || !(await window.appConfirm('确认恢复到这个历史版本？当前 JD 会先保存为一条新版本记录。', { title: '恢复历史版本', tone: 'primary', confirmText: '恢复版本' }))) return
  restoringVersion.value = true
  try {
    const res = await fetch(`/api/jds/${versionJd.value.id}/versions/${version.id}/restore`, { method: 'POST' })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      alert(data.detail || '恢复版本失败')
      return
    }
    versionJd.value = null
    jdVersions.value = []
    viewingJd.value = null
    await fetchStats()
    await fetchJds()
  } finally {
    restoringVersion.value = false
  }
}

async function removeJd(jd) {
  const activeCount = Number(jd.active_application_count || 0)
  const message = activeCount > 0
    ? `「${jd.name}」仍有 ${activeCount} 条进行中投递，归档后候选人将无法继续投递，确认继续？`
    : `确认归档「${jd.name}」？`
  if (!(await window.appConfirm(message, { title: activeCount > 0 ? '确认归档并结束岗位' : '确认归档' }))) return
  await fetch(`/api/jds/${jd.id}`, { method: 'DELETE' })
  await fetchJds()
}

async function updateSelectedStatus(status) {
  const targets = selectedJds.value
  if (!targets.length) return
  batchWorking.value = true
  const errors = []
  for (const jd of targets) {
    const res = await fetch(`/api/jds/${jd.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    }).catch(() => null)
    if (!res?.ok) { const data = await res?.json?.().catch(() => ({})); errors.push(`${jd.name}：${data.detail || '操作失败'}`) }
  }
  selectedJdIds.value = new Set()
  batchWorking.value = false
  await fetchStats()
  await fetchJds()
  if (errors.length) alert(errors.join('\n'))
}

async function deleteSelectedJds() {
  const targets = selectedJds.value
  if (!targets.length) return
  if (!(await window.appConfirm(`确认删除选中的 ${targets.length} 个岗位 JD？`))) return
  batchWorking.value = true
  for (const jd of targets) {
    await fetch(`/api/jds/${jd.id}`, { method: 'DELETE' }).catch(() => {})
  }
  selectedJdIds.value = new Set()
  batchWorking.value = false
  await fetchStats()
  await fetchJds()
}

function exportSelectedJds() {
  const targets = selectedJds.value
  if (!targets.length) return
  const records = targets.map(jd => ({
    name: jd.name || '', category: jd.category || '', location: jd.location || '', recruitment_type: jd.recruitment_type || '',
    experience_required: jd.experience_required || '', status: statusLabel(jd.status), responsibilities: jd.responsibilities || '',
    requirements: jd.requirements || '', published_at: jd.published_at || '', updated_at: jd.updated_at || jd.created_at || '',
  }))
  let content; let mime; let extension
  if (exportFormat.value === 'json') {
    content = JSON.stringify(records, null, 2)
    mime = 'application/json;charset=utf-8'; extension = 'json'
  } else {
    const headers = ['岗位名称', '岗位类别', '地点', '招聘类型', '经验要求', '状态', '岗位职责', '任职要求', '发布时间', '更新时间']
    const rows = records.map(item => [item.name, item.category, item.location, item.recruitment_type, item.experience_required, item.status, item.responsibilities, item.requirements, item.published_at, item.updated_at])
    content = '\ufeff' + [headers, ...rows].map(row => row.map(value => `"${String(value ?? '').replaceAll('"', '""')}"`).join(',')).join('\n')
    mime = 'text/csv;charset=utf-8'; extension = 'csv'
  }
  const url = URL.createObjectURL(new Blob([content], { type: mime }))
  const link = document.createElement('a'); link.href = url; link.download = `jd导出-${new Date().toISOString().slice(0,10)}.${extension}`; link.click(); URL.revokeObjectURL(url)
  showExportPicker.value = false
}

function chooseExportFormat(format) {
  exportFormat.value = format
  exportSelectedJds()
}

function resetFilters() {
  searchText.value = ''; filterCategory.value = ''; filterStatus.value = ''; filterArchive.value = ''; filterLocation.value = ''; filterRecruitment.value = ''
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
          <div class="inline-flex rounded-xl border border-gray-200 bg-white p-1 shadow-sm">
            <button
              :class="['h-9 px-4 rounded-lg text-sm font-medium transition flex items-center gap-2', viewMode === 'list' ? 'bg-[#1677ff] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-50']"
              @click="viewMode = 'list'"
            >
              <i class="fa fa-list"></i>
              <span>列表模式</span>
            </button>
            <button
              :class="['h-9 px-4 rounded-lg text-sm font-medium transition flex items-center gap-2', viewMode === 'card' ? 'bg-[#1677ff] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-50']"
              @click="viewMode = 'card'"
            >
              <i class="fa fa-th-large"></i>
              <span>卡片模式</span>
            </button>
          </div>
          <button class="px-4 py-2 rounded-lg flex items-center gap-2 transition text-sm border border-[#7c3aed] text-[#7c3aed] hover:bg-violet-50" @click="openGenerator">
            <i class="fa fa-magic"></i> JD生成助手
          </button>
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

      <div v-if="batchMode" class="mb-6 rounded-2xl border border-orange-100 bg-white p-4 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-50 text-orange-500"><i class="fa fa-check-square-o"></i></div>
            <div><div class="text-sm font-semibold text-gray-800">批量管理岗位</div><div class="text-xs text-gray-500">已选择 <span class="font-semibold text-orange-600">{{ selectedJds.length }}</span> 个 JD{{ selectedAllResults ? '（全部筛选结果）' : '' }}</div></div>
          </div>
          <div class="flex gap-2">
            <button class="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50" @click="toggleSelectAll">{{ allSelected && !selectedAllResults ? '取消本页全选' : '全选当前页' }}</button>
            <button class="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-sm font-medium text-orange-600 hover:bg-orange-100" @click="selectAllResults">{{ selectedAllResults ? '取消全选结果' : `全选全部 ${total} 条` }}</button>
          </div>
        </div>
        <div class="mt-4 grid gap-3 border-t border-gray-100 pt-4 lg:grid-cols-[auto_1fr_auto] lg:items-end">
          <div><div class="mb-1.5 text-xs font-medium text-gray-500">状态操作</div><div class="flex gap-2">
            <button class="rounded-lg border border-green-200 px-3 py-2 text-sm text-green-600 hover:bg-green-50 disabled:opacity-40" :disabled="batchWorking || !selectedJds.length" @click="updateSelectedStatus('enable')"><i class="fa fa-check-circle mr-1"></i>发布</button>
            <button class="rounded-lg border border-orange-200 px-3 py-2 text-sm text-orange-600 hover:bg-orange-50 disabled:opacity-40" :disabled="batchWorking || !selectedJds.length" @click="updateSelectedStatus('disable')"><i class="fa fa-pause-circle mr-1"></i>暂停</button>
          </div></div>
          <div class="hidden text-xs text-gray-400 lg:block">岗位类别和招聘类型保持 JD 固定关联，请在单个 JD 或创建副本时调整。</div>
          <div class="flex gap-2 lg:justify-end">
            <div class="relative">
              <button class="inline-flex items-center gap-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-600 transition hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-40" :disabled="batchWorking || !selectedJds.length" @click="showExportPicker = !showExportPicker">
                <i class="fa fa-download"></i><span>导出</span><i class="fa fa-angle-down text-xs"></i>
              </button>
              <div v-if="showExportPicker" class="absolute bottom-[calc(100%+8px)] right-0 z-30 w-36 rounded-xl border border-slate-100 bg-white p-1.5 text-left shadow-xl">
                <div class="px-2.5 py-1.5 text-[11px] font-semibold text-slate-400">选择导出格式</div>
                <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-slate-700 hover:bg-sky-50 hover:text-sky-600" @click="chooseExportFormat('csv')"><i class="fa fa-file-text-o w-4"></i>CSV 文件</button>
                <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-slate-700 hover:bg-sky-50 hover:text-sky-600" @click="chooseExportFormat('json')"><i class="fa fa-code w-4"></i>JSON 文件</button>
              </div>
            </div>
            <button class="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-40" :disabled="batchWorking || !selectedJds.length" @click="deleteSelectedJds"><i class="fa fa-archive"></i><span>归档</span></button>
          </div>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-1 gap-4 mb-6 sm:grid-cols-2 xl:grid-cols-5">
        <article
          v-for="card in statCards"
          :key="card.label"
          class="relative overflow-hidden rounded-2xl border border-[#e7eef8] bg-white p-5 shadow-sm"
        >
          <div :class="['absolute inset-x-0 top-0 h-1 bg-gradient-to-r', card.accent]"></div>
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-sm font-medium text-[#7b879c]">{{ card.label }}</p>
              <p class="mt-3 text-3xl font-bold tracking-tight text-[#15213f]">{{ card.value }}</p>
            </div>
            <div :class="['flex h-11 w-11 items-center justify-center rounded-xl', card.soft]">
              <i :class="['fa', card.icon]"></i>
            </div>
          </div>
          <div class="mt-4 flex items-center gap-2 text-xs text-[#8a97ad]">
            <span class="h-1.5 w-1.5 rounded-full bg-[#9fb3d1]"></span>
            <span>{{ card.note }}</span>
          </div>
        </article>

        <article class="relative overflow-hidden rounded-2xl border border-[#e7eef8] bg-white p-5 shadow-sm">
          <div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-[#f59e0b] via-[#3b82f6] to-[#8b5cf6]"></div>
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <p class="text-sm font-medium text-[#7b879c]">招聘结构</p>
              <p class="mt-3 text-xs text-[#8a97ad]">按招聘类型分布</p>
            </div>
            <div class="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <i class="fa fa-sitemap"></i>
            </div>
          </div>
          <div class="mt-4 grid grid-cols-3 gap-2">
            <div class="rounded-xl bg-green-50 px-3 py-2 text-center">
              <div class="text-xl font-bold leading-none text-[#16a34a]">{{ stats.interns }}</div>
              <div class="mt-1 text-xs font-medium text-green-700">实习生</div>
            </div>
            <div class="rounded-xl bg-blue-50 px-3 py-2 text-center">
              <div class="text-xl font-bold leading-none text-[#2563eb]">{{ stats.campus }}</div>
              <div class="mt-1 text-xs font-medium text-blue-700">校招</div>
            </div>
            <div class="rounded-xl bg-violet-50 px-3 py-2 text-center">
              <div class="text-xl font-bold leading-none text-[#7c3aed]">{{ stats.social }}</div>
              <div class="mt-1 text-xs font-medium text-violet-700">社招</div>
            </div>
          </div>
        </article>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-60 relative">
            <input v-model="searchText" type="text" placeholder="搜索岗位名称" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="onSearchChange">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <div class="w-[150px]"><FixedSelect v-model="filterCategory" :options="[{ value: '', label: '全部岗位类别' }, ...categories.map(c => ({ value: c, label: c }))]" @change="fetchJds" /></div>
          <div class="w-[140px]"><FixedSelect v-model="filterStatus" :options="[{ value: '', label: '全部状态' }, { value: 'draft', label: '草稿' }, { value: 'enable', label: '已发布' }, { value: 'disable', label: '已暂停' }, { value: 'expired', label: '已过期' }, { value: 'closed', label: '已关闭' }]" @change="fetchJds" /></div>
          <div class="w-[140px]"><FixedSelect v-model="filterArchive" :options="[{ value: '', label: '正常 JD' }, { value: 'archived', label: '已归档' }]" @change="fetchJds" /></div>
          <div class="relative w-64">
            <i class="fa fa-map-marker absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
            <input
              v-model="filterLocation"
              class="h-10 w-full rounded-lg border pl-9 pr-20 text-sm focus:outline-none focus:border-[#1677ff]"
              placeholder="工作地点"
              @change="fetchJds"
            >
            <button
              type="button"
              class="absolute right-1.5 top-1/2 h-7 -translate-y-1/2 rounded-md bg-[#f1f6ff] px-2.5 text-xs font-medium text-[#1677ff] hover:bg-[#e4efff]"
              @click="toggleLocationPicker('filter')"
            >
              城市
            </button>
            <div v-if="activeLocationPicker === 'filter'" class="absolute left-0 top-[44px] z-30 w-[352px] rounded-lg border border-[#dde7f4] bg-[#fbfdff] p-2.5 shadow-lg shadow-slate-200/60">
              <div class="mb-2 flex items-center justify-between px-1">
                <span class="text-xs font-semibold text-[#7a8798]">热门城市</span>
                <button v-if="filterLocation" type="button" class="text-xs text-[#94a3b8] hover:text-[#1677ff]" @click="pickLocation('filter', '')">清空</button>
              </div>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="city in popularCities"
                  :key="city"
                  type="button"
                  :class="locationOptionClass(filterLocation, city)"
                  @click="pickLocation('filter', city)"
                >
                  {{ city }}
                </button>
              </div>
              <p class="mt-2 px-1 text-xs text-[#9aa7b8]">也可以直接输入更细位置</p>
            </div>
          </div>
          <div class="ml-auto flex items-center gap-2">
            <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置</button>
            <div class="inline-flex items-center gap-1 rounded-xl bg-[#eef2f7] p-1">
              <button
                v-for="item in [{ value: '', label: '全部' }, { value: '社招', label: '社招' }, { value: '校招', label: '校招' }, { value: '实习生', label: '实习' }]"
                :key="item.value || 'all'"
                type="button"
                :class="filterRecruitment === item.value ? 'bg-white text-[#4b6cff] shadow-sm' : 'text-[#667085] hover:text-[#344054]'"
                class="rounded-lg px-3 py-2 text-sm font-semibold transition"
                @click="filterRecruitment = item.value; page = 1; fetchJds()"
              >{{ item.label }}</button>
            </div>
          </div>
        </div>
      </div>

      <!-- JD 内容区 -->
      <div v-if="viewMode === 'list'" class="bg-white rounded-xl shadow-sm overflow-hidden">
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
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">JD 发布时间</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">状态</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-56">操作</th>
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
                <span :class="getRecruitmentBadgeClass(jd.recruitment_type)" class="px-2 py-0.5 text-xs rounded font-medium">{{ jd.recruitment_type || '社招' }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ jd.experience_required || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ jd.location }}</td>
              <td class="whitespace-nowrap px-4 py-3 text-sm text-gray-500">{{ formatPublishTime(jd) }}</td>
              <td class="px-4 py-3">
                <span :class="getStatusBadgeClass(jd.status)" class="px-2 py-1 text-xs rounded">{{ statusLabel(jd.status) }}</span>
              </td>
              <td class="px-4 py-3 text-center">
                <div class="relative flex items-center justify-center gap-1" data-jd-action-menu>
                  <button class="w-8 h-8 rounded-lg text-[#1677ff] hover:bg-blue-50 transition flex items-center justify-center" title="查看" @click="viewJd(jd)"><i class="fa fa-eye"></i></button>
                  <button class="w-8 h-8 rounded-lg text-gray-500 hover:bg-gray-100 transition flex items-center justify-center" title="编辑" @click="openEdit(jd)"><i class="fa fa-pencil"></i></button>
                  <button class="h-8 rounded-lg px-2 text-gray-500 hover:bg-gray-100 transition" title="更多操作" @click="toggleActionMenu(jd.id)"><i class="fa fa-ellipsis-h"></i></button>
                  <div v-if="activeActionMenu === jd.id" class="absolute right-0 top-10 z-30 w-32 rounded-xl border border-gray-100 bg-white p-1.5 text-left shadow-xl" @click.stop>
                    <button class="menu-action text-violet-600" @click="closeActionMenu(); openOptimize(jd)"><i class="fa fa-magic"></i>AI 优化</button>
                    <button class="menu-action text-sky-600" @click="closeActionMenu(); openVersions(jd)"><i class="fa fa-history"></i>版本记录</button>
                    <button class="menu-action text-amber-600" @click="closeActionMenu(); openCopy(jd)"><i class="fa fa-clone"></i>创建 JD 副本</button>
                    <button class="menu-action text-red-500" @click="closeActionMenu(); removeJd(jd)"><i class="fa fa-trash-o"></i>归档 JD</button>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !jdList.length" class="text-center py-12 text-gray-400"><i class="fa fa-inbox text-3xl mb-2 block"></i>暂无匹配的岗位 JD</div>
      </div>

      <div v-else>
        <div v-if="loading" class="bg-white rounded-xl shadow-sm text-center py-12 text-gray-400"><i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...</div>
        <div v-else-if="jdList.length" class="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-5">
          <article
            v-for="jd in jdList"
            :key="jd.id"
            class="group rounded-2xl border border-[#e5ecf7] bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(27,76,173,0.10)]"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-start gap-3 min-w-0">
                <label v-if="batchMode" class="pt-1">
                  <input type="checkbox" :checked="selectedJdIds.has(jd.id)" @change="setSelectedJd(jd.id, $event.target.checked)">
                </label>
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <h3 class="text-lg font-semibold text-[#18233e] break-all">{{ jd.name }}</h3>
                    <span :class="getStatusBadgeClass(jd.status)" class="px-2.5 py-1 text-xs rounded-full font-medium">{{ statusLabel(jd.status) }}</span>
                  </div>
                  <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-[#70809c]">
                    <span class="rounded-full border border-[#dce6f7] bg-[#f8fbff] px-2.5 py-1">{{ jd.category || '未分类' }}</span>
                    <span :class="getRecruitmentBadgeClass(jd.recruitment_type)" class="rounded-full px-2.5 py-1 font-medium">{{ jd.recruitment_type || '社招' }}</span>
                    <span class="rounded-full border border-[#dce6f7] bg-white px-2.5 py-1">{{ jd.location || '地点未填' }}</span>
                  </div>
                </div>
              </div>
              <div class="relative flex items-center gap-1 shrink-0" data-jd-action-menu>
                <button class="w-9 h-9 rounded-xl text-[#1677ff] hover:bg-blue-50 transition flex items-center justify-center" title="查看" @click="viewJd(jd)"><i class="fa fa-eye"></i></button>
                <button class="w-9 h-9 rounded-xl text-gray-500 hover:bg-gray-100 transition flex items-center justify-center" title="编辑" @click="openEdit(jd)"><i class="fa fa-pencil"></i></button>
                <button class="h-9 rounded-xl px-2 text-gray-500 hover:bg-gray-100 transition" title="更多操作" @click="toggleActionMenu(jd.id)"><i class="fa fa-ellipsis-h"></i></button>
                <div v-if="activeActionMenu === jd.id" class="absolute right-0 top-11 z-30 w-32 rounded-xl border border-gray-100 bg-white p-1.5 text-left shadow-xl" @click.stop>
                  <button class="menu-action text-violet-600" @click="closeActionMenu(); openOptimize(jd)"><i class="fa fa-magic"></i>AI 优化</button>
                  <button class="menu-action text-sky-600" @click="closeActionMenu(); openVersions(jd)"><i class="fa fa-history"></i>版本记录</button>
                  <button class="menu-action text-amber-600" @click="closeActionMenu(); openCopy(jd)"><i class="fa fa-clone"></i>创建 JD 副本</button>
                  <button class="menu-action text-red-500" @click="closeActionMenu(); removeJd(jd)"><i class="fa fa-trash-o"></i>归档 JD</button>
                </div>
              </div>
            </div>

            <div class="mt-4 grid grid-cols-2 gap-3">
              <div class="rounded-xl border border-[#edf2fb] bg-[#fbfcff] px-3 py-3">
                <div class="text-xs text-[#8a97b0]">经验要求</div>
                <div class="mt-1 text-sm font-medium text-[#22304c]">{{ jd.experience_required || '不限 / 未填写' }}</div>
              </div>
              <div class="rounded-xl border border-[#edf2fb] bg-[#fbfcff] px-3 py-3">
                <div class="text-xs text-[#8a97b0]">岗位编号</div>
                <div class="mt-1 text-sm font-medium text-[#22304c]">JD-{{ jd.id }}</div>
              </div>
            </div>

            <div class="mt-4 rounded-2xl border border-[#edf2fb] bg-[#fcfdff] px-4 py-4">
              <div class="flex items-center justify-between gap-3">
                <div class="text-sm font-semibold text-[#1d2941]">岗位摘要</div>
                <span class="text-xs text-[#95a1b7]">职责 / 要求</span>
              </div>
              <p class="mt-2 text-sm leading-6 text-[#5d6c87]">{{ getResponsibilityPreview(jd) }}</p>
            </div>
          </article>
        </div>
        <div v-else class="bg-white rounded-xl shadow-sm text-center py-12 text-gray-400"><i class="fa fa-inbox text-3xl mb-2 block"></i>暂无匹配的岗位 JD</div>
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
    <div v-if="copySource" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-5" @click.self="copySource = null">
      <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h3 class="text-lg font-bold text-gray-900">创建 JD 副本</h3>
        <p class="mt-1 text-sm text-gray-500">基于“{{ copySource.name }}”创建一条新的 JD 草稿，可调整招聘类型和经验要求。</p>
        <label class="mt-5 block text-sm font-medium text-gray-700">岗位名称<input v-model="copyForm.name" class="mt-1 h-10 w-full rounded-lg border px-3" /></label>
        <label class="mt-4 block text-sm font-medium text-gray-700">招聘类型<FixedSelect v-model="copyForm.recruitment_type" :options="['实习生','校招','社招']" /></label>
        <label class="mt-4 block text-sm font-medium text-gray-700">经验要求<FixedSelect v-model="copyForm.experience_required" :options="experienceOptions" /></label>
        <div class="mt-5 flex justify-end gap-2"><button class="rounded-lg bg-gray-100 px-4 py-2 text-sm" @click="copySource = null">取消</button><button class="rounded-lg bg-[#1677ff] px-4 py-2 text-sm font-semibold text-white" @click="confirmCopy">创建草稿</button></div>
      </div>
    </div>

    <div v-if="showModal" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-5" @click.self="showModal = false">
      <div class="flex max-h-[88vh] w-[960px] max-w-[96vw] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div class="flex shrink-0 items-start justify-between gap-4 border-b px-6 py-5">
          <div>
            <h3 class="text-xl font-bold text-gray-900">{{ editingJd ? '编辑岗位JD' : '新增岗位JD' }}</h3>
            <p class="mt-1 text-sm text-gray-500">维护岗位基础信息、职责与任职要求。</p>
          </div>
          <div v-if="editingJd" class="flex shrink-0 gap-2">
            <button class="rounded-lg border border-amber-200 px-3 py-2 text-sm font-semibold text-amber-600 hover:bg-amber-50" @click="showModal = false; openCopy(editingJd)"><i class="fa fa-clone mr-1"></i>创建 JD 副本</button>
            <button class="rounded-lg border border-violet-200 px-3 py-2 text-sm font-semibold text-violet-600 hover:bg-violet-50" @click="showModal = false; openOptimize(editingJd)"><i class="fa fa-magic mr-1"></i>AI 优化</button>
          </div>
        </div>
        <div class="min-h-0 flex-1 overflow-auto p-6">
          <div class="grid grid-cols-4 gap-4">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">岗位名称 <span class="text-red-500">*</span></label>
              <input v-model="form.name" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：后端开发工程师">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">岗位类别</label>
              <FixedSelect v-model="form.category" :options="jobCategoryOptions" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">工作地点</label>
              <div class="relative">
                <i class="fa fa-map-marker absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                <input v-model="form.location" class="h-10 w-full rounded-lg border pl-9 pr-20 text-sm focus:outline-none focus:border-[#1677ff]" placeholder="如：深圳 / 深圳·南山">
                <button type="button" class="absolute right-1.5 top-1/2 h-7 -translate-y-1/2 rounded-md bg-[#f1f6ff] px-2.5 text-xs font-medium text-[#1677ff] hover:bg-[#e4efff]" @click="toggleLocationPicker('form')">
                  城市
                </button>
                <div v-if="activeLocationPicker === 'form'" class="absolute right-0 top-[44px] z-30 w-[352px] rounded-lg border border-[#dde7f4] bg-[#fbfdff] p-2.5 shadow-lg shadow-slate-200/60">
                  <div class="mb-2 flex items-center justify-between px-1">
                    <span class="text-xs font-semibold text-[#7a8798]">热门城市</span>
                    <button v-if="form.location" type="button" class="text-xs text-[#94a3b8] hover:text-[#1677ff]" @click="pickLocation('form', '')">清空</button>
                  </div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="city in popularCities"
                      :key="'form-' + city"
                      type="button"
                      :class="locationOptionClass(form.location, city)"
                      @click="pickLocation('form', city)"
                    >
                      {{ city }}
                    </button>
                  </div>
                  <p class="mt-2 px-1 text-xs text-[#9aa7b8]">也可以直接输入园区或区县</p>
                </div>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">招聘类型</label>
              <FixedSelect v-model="form.recruitment_type" :options="['实习生', '校招', '社招']" :disabled="recruitmentTypeLocked" />
              <p v-if="recruitmentTypeLocked" class="mt-1 text-xs text-[#98a2b3]">已有投递或已发布，招聘类型不可修改；如需调整请复制 JD。</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">经验要求</label>
              <FixedSelect v-model="form.experience_required" :options="experienceOptions" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
              <FixedSelect v-model="form.status" :options="[{ value: 'draft', label: '草稿' }, { value: 'enable', label: '已发布' }, { value: 'disable', label: '已暂停' }, { value: 'expired', label: '已过期' }, { value: 'closed', label: '已关闭' }]" />
            </div>
          </div>

          <div class="mt-5 grid grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">岗位职责</label>
              <textarea v-model="form.responsibilities" rows="10" class="w-full resize-y rounded-xl border px-3 py-3 leading-6 focus:outline-none focus:border-[#1677ff]" placeholder="描述岗位职责..."></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">任职要求</label>
              <textarea v-model="form.requirements" rows="10" class="w-full resize-y rounded-xl border px-3 py-3 leading-6 focus:outline-none focus:border-[#1677ff]" placeholder="描述任职要求..."></textarea>
            </div>
          </div>
        </div>
        <div class="shrink-0 flex justify-end gap-3 border-t bg-white px-6 py-4">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="showModal = false">取消</button>
          <button class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600 text-sm" @click="saveJd">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showGenerator" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showGenerator = false">
      <div class="bg-white rounded-2xl w-[620px] max-w-[96vw] shadow-xl overflow-hidden">
        <div class="px-6 py-5 border-b">
          <h3 class="text-lg font-bold text-gray-900">JD 生成助手</h3>
          <p class="text-sm text-gray-500 mt-1">输入岗位名称和一句简单描述，系统会按点生成岗位职责、任职要求和经验要求，再带回新增表单。</p>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">岗位名称 <span class="text-red-500">*</span></label>
            <input v-model="generatorForm.name" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：大模型应用开发工程师">
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">岗位类别</label>
              <input v-model="generatorForm.category" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：AI应用 / 技术开发">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">工作地点</label>
              <div class="relative">
                <i class="fa fa-map-marker absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                <input v-model="generatorForm.location" class="h-10 w-full rounded-lg border pl-9 pr-20 text-sm focus:outline-none focus:border-[#1677ff]" placeholder="如：深圳 / 深圳·南山">
                <button type="button" class="absolute right-1.5 top-1/2 h-7 -translate-y-1/2 rounded-md bg-[#f1f6ff] px-2.5 text-xs font-medium text-[#1677ff] hover:bg-[#e4efff]" @click="toggleLocationPicker('generator')">
                  城市
                </button>
                <div v-if="activeLocationPicker === 'generator'" class="absolute right-0 top-[44px] z-30 w-[352px] rounded-lg border border-[#dde7f4] bg-[#fbfdff] p-2.5 shadow-lg shadow-slate-200/60">
                  <div class="mb-2 flex items-center justify-between px-1">
                    <span class="text-xs font-semibold text-[#7a8798]">热门城市</span>
                    <button v-if="generatorForm.location" type="button" class="text-xs text-[#94a3b8] hover:text-[#1677ff]" @click="pickLocation('generator', '')">清空</button>
                  </div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="city in popularCities"
                      :key="'generator-' + city"
                      type="button"
                      :class="locationOptionClass(generatorForm.location, city)"
                      @click="pickLocation('generator', city)"
                    >
                      {{ city }}
                    </button>
                  </div>
                  <p class="mt-2 px-1 text-xs text-[#9aa7b8]">也可以直接输入园区或区县</p>
                </div>
              </div>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">招聘类型</label>
            <select v-model="generatorForm.recruitment_type" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
              <option value="实习生">实习生</option>
              <option value="校招">校招</option>
              <option value="社招">社招</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">简单描述</label>
            <textarea
              v-model="generatorForm.summary"
              rows="5"
              class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]"
              placeholder="例如：负责 RAG 问答系统、Agent 工作流、LLM 应用落地，要求有 Python、LangChain、向量数据库相关经验。生成结果需要按点列出职责和要求。"
            ></textarea>
          </div>
        </div>
        <div class="px-6 py-4 bg-gray-50 border-t flex justify-end gap-3">
          <button class="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-white" :disabled="generatingDraft" @click="showGenerator = false">取消</button>
          <button class="px-4 py-2 rounded-lg bg-[#7c3aed] text-white text-sm hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-violet-300" :disabled="generatingDraft || !generatorForm.name.trim()" @click="generateDraft">
            <i :class="['fa mr-1', generatingDraft ? 'fa-spinner fa-spin' : 'fa-magic']"></i>{{ generatingDraft ? '生成中' : '生成 JD 草稿' }}
          </button>
        </div>
      </div>
    </div>

    <!-- JD 优化对比弹窗 -->
    <div v-if="optimizeSource" class="fixed inset-0 bg-black/45 z-50 flex items-center justify-center p-5" @click.self="closeOptimize()">
      <div class="flex max-h-[88vh] w-[1080px] max-w-[96vw] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div class="shrink-0 flex items-start justify-between gap-5 border-b px-6 py-5">
          <div>
            <div class="inline-flex items-center gap-2 rounded-full bg-violet-50 px-3 py-1 text-xs font-semibold text-[#7c3aed]">
              <i class="fa fa-magic"></i>
              JD 优化助手
            </div>
            <h3 class="mt-3 text-xl font-bold text-gray-900">{{ optimizeSource.name }}</h3>
            <p class="mt-1 text-sm text-gray-500">先查看优化前后差异，确认后再采纳覆盖当前 JD。</p>
          </div>
          <button class="h-9 w-9 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-700" :disabled="optimizingDraft || savingOptimized" @click="closeOptimize()">
            <i class="fa fa-times"></i>
          </button>
        </div>

        <div v-if="optimizingDraft" class="flex min-h-[420px] flex-1 flex-col items-center justify-center text-gray-500">
          <i class="fa fa-spinner fa-spin text-3xl text-[#7c3aed]"></i>
          <p class="mt-4 text-sm">正在分析现有 JD 并生成优化版本...</p>
        </div>

        <div v-else class="min-h-0 flex-1 overflow-auto bg-[#f6f8fc] p-6">
          <div v-if="optimizedDraft?.summary" class="mb-5 rounded-xl border border-violet-100 bg-white px-4 py-3">
            <div class="text-sm font-semibold text-[#2b3350]">优化说明</div>
            <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#64708a]">{{ optimizedDraft.summary }}</p>
          </div>

          <div class="grid gap-5 lg:grid-cols-2">
            <section class="rounded-2xl border border-[#e5ebf5] bg-white">
              <div class="border-b px-4 py-3">
                <div class="text-sm font-semibold text-[#6b7280]">优化前</div>
              </div>
              <div class="divide-y divide-[#eef2f7]">
                <div v-for="field in compareFields" :key="'old-' + field.key" class="px-4 py-3">
                  <div class="text-xs font-semibold text-[#8a96aa]">{{ field.label }}</div>
                  <p class="mt-1 whitespace-pre-wrap text-sm leading-6 text-[#2f3a4f]">{{ optimizeSource[field.key] || '-' }}</p>
                </div>
              </div>
            </section>

            <section class="rounded-2xl border border-[#d8c8ff] bg-white shadow-sm">
              <div class="flex items-center justify-between border-b border-violet-100 px-4 py-3">
                <div class="text-sm font-semibold text-[#7c3aed]">优化后{{ editingOptimized ? '（编辑中）' : '' }}</div>
                <button v-if="!editingOptimized" class="rounded-lg border border-violet-200 px-3 py-1.5 text-xs font-semibold text-violet-600 hover:bg-violet-50" @click="toggleOptimizedEdit"><i class="fa fa-pencil mr-1"></i>编辑优化结果</button>
                <button v-else class="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700" @click="toggleOptimizedEdit"><i class="fa fa-check mr-1"></i>保存修改</button>
              </div>
              <div v-if="editingOptimized" class="space-y-3 p-4">
                <label v-for="field in compareFields" :key="'edit-' + field.key" class="block">
                  <span class="text-xs font-semibold text-[#8a96aa]">{{ field.label }}</span>
                  <textarea
                    v-if="field.key === 'responsibilities' || field.key === 'requirements'"
                    v-model="optimizedDraft[field.key]"
                    rows="8"
                    class="mt-1 w-full resize-y rounded-lg border border-violet-100 px-3 py-2 text-sm leading-6 text-[#202a43] focus:border-violet-400 focus:outline-none"
                  />
                  <input
                    v-else
                    v-model="optimizedDraft[field.key]"
                    class="mt-1 h-10 w-full rounded-lg border border-violet-100 px-3 text-sm text-[#202a43] focus:border-violet-400 focus:outline-none"
                  />
                </label>
              </div>
              <div v-else class="divide-y divide-[#eef2f7]">
                <div v-for="field in compareFields" :key="'new-' + field.key" class="px-4 py-3">
                  <div class="text-xs font-semibold text-[#8a96aa]">{{ field.label }}</div>
                  <p class="mt-1 whitespace-pre-wrap text-sm leading-6 text-[#202a43]">{{ optimizedDraft?.[field.key] || '-' }}</p>
                </div>
              </div>
            </section>
          </div>
        </div>

        <div class="shrink-0 flex flex-wrap items-center justify-between gap-3 border-t bg-white px-6 py-4 shadow-[0_-10px_24px_rgba(15,23,42,0.06)]">
          <div class="text-xs text-gray-500">可先编辑优化结果，确认无误后再采纳。</div>
          <div class="flex items-center gap-3">
            <button class="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50" :disabled="optimizingDraft || savingOptimized" @click="closeOptimize()">暂不采纳</button>
            <button class="px-4 py-2 rounded-lg bg-[#7c3aed] text-white text-sm hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-violet-300" :disabled="optimizingDraft || savingOptimized || !optimizedDraft" @click="acceptOptimizedJd">
              <i :class="['fa mr-1', savingOptimized ? 'fa-spinner fa-spin' : 'fa-check']"></i>{{ savingOptimized ? '保存中' : '采纳优化' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- JD 版本记录弹窗 -->
    <div v-if="versionJd" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-5" @click.self="versionJd = null">
      <div class="flex max-h-[82vh] w-[760px] max-w-[96vw] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div class="shrink-0 flex items-start justify-between gap-4 border-b px-6 py-5">
          <div>
            <div class="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-600">
              <i class="fa fa-history"></i>
              版本记录
            </div>
            <h3 class="mt-3 text-xl font-bold text-gray-900">{{ versionJd.name }}</h3>
            <p class="mt-1 text-sm text-gray-500">编辑、AI 采纳和恢复前都会自动保存历史版本。</p>
          </div>
          <button class="h-9 w-9 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-700" :disabled="restoringVersion" @click="versionJd = null">
            <i class="fa fa-times"></i>
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-auto bg-[#f6f8fc] p-5">
          <div v-if="loadingVersions" class="py-14 text-center text-gray-400">
            <i class="fa fa-spinner fa-spin text-2xl"></i>
            <p class="mt-3 text-sm">正在加载版本记录...</p>
          </div>
          <div v-else-if="!jdVersions.length" class="rounded-2xl border border-dashed border-[#d8e2f1] bg-white py-12 text-center text-gray-400">
            <i class="fa fa-clock-o text-3xl"></i>
            <p class="mt-3 text-sm">暂无历史版本</p>
          </div>
          <div v-else class="space-y-3">
            <article v-for="version in jdVersions" :key="version.id" class="rounded-2xl border border-[#e5ecf7] bg-white p-4">
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <h4 class="font-semibold text-[#1d2941]">{{ version.name }}</h4>
                    <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                      {{ version.source === 'ai_optimize' ? 'AI采纳前' : version.source === 'restore' ? '恢复前' : '编辑前' }}
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-[#8a97ad]">{{ version.created_at }}</p>
                </div>
                <div class="flex shrink-0 items-center gap-2">
                  <button class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50" @click="versionDetail = version">查看详情</button>
                  <button class="rounded-lg border border-sky-200 px-3 py-1.5 text-sm text-sky-600 hover:bg-sky-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="restoringVersion" @click="restoreVersion(version)">
                    恢复此版
                  </button>
                </div>
              </div>
              <div class="mt-3 grid grid-cols-3 gap-2 text-xs text-[#65748d]">
                <span class="rounded-lg bg-[#f8fbff] px-2 py-1">{{ version.category || '未分类' }}</span>
                <span class="rounded-lg bg-[#f8fbff] px-2 py-1">{{ version.location || '地点未填' }}</span>
                <span class="rounded-lg bg-[#f8fbff] px-2 py-1">{{ version.experience_required || '经验未填' }}</span>
              </div>
              <p class="mt-3 line-clamp-2 text-sm leading-6 text-[#52627d]">{{ version.responsibilities || version.requirements || '暂无职责与要求' }}</p>
            </article>
          </div>
        </div>
      </div>
    </div>

    <!-- 版本详情弹窗 -->
    <div v-if="versionDetail" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-5" @click.self="versionDetail = null">
      <div class="flex max-h-[86vh] w-[760px] max-w-[96vw] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div class="flex shrink-0 items-start justify-between gap-4 border-b px-6 py-5">
          <div>
            <h3 class="text-lg font-bold text-gray-900">{{ versionDetail.name }}</h3>
            <p class="mt-1 text-xs text-[#8a97ad]">{{ versionDetail.created_at }} · {{ versionDetail.source === 'ai_optimize' ? 'AI采纳前' : versionDetail.source === 'restore' ? '恢复前' : '编辑前' }}</p>
          </div>
          <button class="h-9 w-9 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-700" @click="versionDetail = null"><i class="fa fa-times"></i></button>
        </div>
        <div class="min-h-0 flex-1 space-y-5 overflow-auto p-6">
          <div class="grid gap-3 rounded-xl border border-[#e6edf7] bg-[#f8fbff] p-3 sm:grid-cols-2">
            <div class="rounded-lg bg-white px-3 py-2"><div class="text-xs text-[#8a97ad]">岗位类别</div><div class="mt-1 text-sm font-medium text-[#25304a]">{{ versionDetail.category || '-' }}</div></div>
            <div class="rounded-lg bg-white px-3 py-2"><div class="text-xs text-[#8a97ad]">工作地点</div><div class="mt-1 text-sm font-medium text-[#25304a]">{{ versionDetail.location || '-' }}</div></div>
            <div class="rounded-lg bg-white px-3 py-2"><div class="text-xs text-[#8a97ad]">招聘类型</div><div class="mt-1 text-sm font-medium text-[#25304a]">{{ versionDetail.recruitment_type || '-' }}</div></div>
            <div class="rounded-lg bg-white px-3 py-2"><div class="text-xs text-[#8a97ad]">经验要求</div><div class="mt-1 text-sm font-medium text-[#25304a]">{{ versionDetail.experience_required || '-' }}</div></div>
          </div>
          <section>
            <h4 class="text-sm font-semibold text-gray-700">岗位职责</h4>
            <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-600">{{ versionDetail.responsibilities || '暂无' }}</p>
          </section>
          <section>
            <h4 class="text-sm font-semibold text-gray-700">任职要求</h4>
            <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-600">{{ versionDetail.requirements || '暂无' }}</p>
          </section>
        </div>
        <div class="flex shrink-0 justify-end gap-3 border-t bg-gray-50 px-6 py-4">
          <button class="rounded-lg bg-gray-100 px-4 py-2 text-sm hover:bg-gray-200" @click="versionDetail = null">关闭</button>
          <button class="rounded-lg bg-[#1677ff] px-4 py-2 text-sm font-semibold text-white hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50" :disabled="restoringVersion" @click="restoreVersion(versionDetail); versionDetail = null">恢复此版本</button>
        </div>
      </div>
    </div>

    <!-- 查看 JD 弹窗 -->
    <div v-if="viewingJd" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="viewingJd = null">
      <div class="bg-white rounded-2xl w-[640px] max-h-[80vh] overflow-auto p-6 shadow-xl">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-lg font-bold">{{ viewingJd.name }}</h3>
          <span :class="getStatusBadgeClass(viewingJd.status)" class="px-2 py-1 text-xs rounded">{{ statusLabel(viewingJd.status) }}</span>
        </div>
        <div class="space-y-4">
          <div class="grid gap-3 rounded-xl border border-[#e6edf7] bg-[#f8fbff] p-3 sm:grid-cols-2">
            <div class="flex min-w-0 items-center gap-2 rounded-lg bg-white px-3 py-2">
              <i class="fa fa-tag shrink-0 text-[#8492aa]"></i>
              <div class="min-w-0">
                <div class="text-xs text-[#8a97ad]">岗位类别</div>
                <div class="truncate text-sm font-medium text-[#25304a]">{{ viewingJd.category || '-' }}</div>
              </div>
            </div>
            <div class="flex min-w-0 items-center gap-2 rounded-lg bg-white px-3 py-2">
              <i class="fa fa-map-marker shrink-0 text-[#8492aa]"></i>
              <div class="min-w-0">
                <div class="text-xs text-[#8a97ad]">工作地点</div>
                <div class="truncate text-sm font-medium text-[#25304a]">{{ viewingJd.location || '-' }}</div>
              </div>
            </div>
            <div class="flex min-w-0 items-center gap-2 rounded-lg bg-white px-3 py-2">
              <i class="fa fa-briefcase shrink-0 text-[#8492aa]"></i>
              <div class="min-w-0">
                <div class="text-xs text-[#8a97ad]">招聘类型</div>
                <span :class="getRecruitmentBadgeClass(viewingJd.recruitment_type)" class="mt-1 inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium">{{ viewingJd.recruitment_type || '社招' }}</span>
              </div>
            </div>
            <div class="flex min-w-0 items-center gap-2 rounded-lg bg-white px-3 py-2">
              <i class="fa fa-clock-o shrink-0 text-[#8492aa]"></i>
              <div class="min-w-0">
                <div class="text-xs text-[#8a97ad]">经验要求</div>
                <div class="line-clamp-2 text-sm font-medium leading-5 text-[#25304a]">{{ viewingJd.experience_required || '-' }}</div>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="rounded-xl bg-[#f8fbff] px-3 py-3"><div class="text-xs text-[#8a97ad]">绑定投递</div><div class="mt-1 text-lg font-bold text-[#25304a]">{{ viewingJd.application_count || 0 }}</div></div>
            <div class="rounded-xl bg-[#f8fbff] px-3 py-3"><div class="text-xs text-[#8a97ad]">进行中</div><div class="mt-1 text-lg font-bold text-[#1677ff]">{{ viewingJd.active_application_count || 0 }}</div></div>
            <div class="rounded-xl bg-[#f8fbff] px-3 py-3"><div class="text-xs text-[#8a97ad]">已结束</div><div class="mt-1 text-lg font-bold text-[#64748b]">{{ viewingJd.completed_application_count || 0 }}</div></div>
            <div class="rounded-xl bg-[#f8fbff] px-3 py-3"><div class="text-xs text-[#8a97ad]">最近更新</div><div class="mt-1 truncate text-sm font-semibold text-[#25304a]">{{ viewingJd.updated_at || viewingJd.created_at || '-' }}</div></div>
          </div>
          <p class="text-xs text-[#8a97ad]">最后修改人：{{ viewingJd.updated_by || viewingJd.created_by || '管理员' }}</p>
          <div>
            <h4 class="text-sm font-semibold text-gray-700 mb-2">岗位职责</h4>
            <p class="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{{ viewingJd.responsibilities || '暂无' }}</p>
          </div>
          <div>
            <h4 class="text-sm font-semibold text-gray-700 mb-2">任职要求</h4>
            <p class="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{{ viewingJd.requirements || '暂无' }}</p>
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button class="px-4 py-2 rounded-lg border border-amber-200 text-amber-600 hover:bg-amber-50 text-sm" @click="copyJdInfo(viewingJd)"><i class="fa fa-clipboard mr-1"></i>复制 JD 文本</button>
          <button class="px-4 py-2 rounded-lg border border-sky-200 text-sky-600 hover:bg-sky-50 text-sm" @click="openVersions(viewingJd)">版本记录</button>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="viewingJd = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.menu-action {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  border-radius: 0.5rem;
  padding: 0.5rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 600;
  transition: background-color .15s ease;
}
.menu-action:hover { background: #f5f7fb; }
select {
  appearance: auto;
  -webkit-appearance: menulist;
  cursor: pointer;
  background-color: #fff;
}
</style>
