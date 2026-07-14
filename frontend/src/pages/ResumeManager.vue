<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const resumeList = ref([])
const loading = ref(true)
const uploading = ref(false)
const parsingAll = ref(false)
const parsingIds = ref(new Set())
const parseProgressMap = ref({})
const batchParseProgress = ref({ current: 0, total: 0, percent: 0, active: false })
const searchText = ref('')
const filterStatus = ref('')
const filterYears = ref('')
const showJdPicker = ref(false)
const pendingFile = ref(null)
const selectedJdId = ref(0)
const jdOptions = ref([])
const uploadInput = ref(null)
const showBindJdPicker = ref(false)
const bindingResume = ref(null)
const bindingJdId = ref(0)
const bindingJdSaving = ref(false)
const creatingPlanKey = ref('')
const createdPlan = ref(null)
const createdWorkflowPlans = computed(() => (createdPlan.value?.plans || []).filter(Boolean))
const showWorkflowPicker = ref(false)
const workflowResume = ref(null)
const workflowBatchMode = ref(false)
const selectedWorkflowIndex = ref(0)
const creatingWorkflow = ref(false)
const batchMode = ref(false)
const selectedResumeIds = ref(new Set())
const batchWorking = ref(false)
const page = ref(1)
const pageSize = ref(10)
const viewMode = ref('list')

const workflowTemplates = [
  {
    name: '标准技术岗流程',
    desc: '技术一面、技术二面、HR 面，适合研发/算法/测试岗位',
    stages: [
      { name: '技术一面', question_count: 10 },
      { name: '技术二面', question_count: 8 },
      { name: 'HR 面', question_count: 6 },
    ],
  },
  {
    name: '快速招聘流程',
    desc: '综合面试、HR 面，适合应届生和批量初筛',
    stages: [
      { name: '综合面试', question_count: 10 },
      { name: 'HR 面', question_count: 6 },
    ],
  },
  {
    name: '高级岗位流程',
    desc: '技术一面、技术二面、交叉面、终面，适合专家/管理岗位',
    stages: [
      { name: '技术一面', question_count: 10 },
      { name: '技术二面', question_count: 10 },
      { name: '交叉面', question_count: 8 },
      { name: '终面', question_count: 6 },
    ],
  },
]

const parseQueue = computed(() => resumeList.value.filter(r => r.file_path && r.parse_status !== 'success'))
const totalPages = computed(() => Math.max(1, Math.ceil(resumeList.value.length / pageSize.value)))
const pagedResumeList = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return resumeList.value.slice(start, start + pageSize.value)
})
const selectedResumes = computed(() => resumeList.value.filter(r => selectedResumeIds.value.has(r.id)))
const selectableResumes = computed(() => pagedResumeList.value)
const allSelected = computed(() => selectableResumes.value.length > 0 && selectableResumes.value.every(r => selectedResumeIds.value.has(r.id)))
const visiblePages = computed(() => {
  const total = totalPages.value
  const start = Math.max(1, page.value - 2)
  const end = Math.min(total, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

function getParseProgress(rid) {
  return parseProgressMap.value[rid] || null
}

function setParseProgress(rid, patch) {
  parseProgressMap.value = {
    ...parseProgressMap.value,
    [rid]: {
      percent: 0,
      phase: '准备解析',
      timer: null,
      status: 'running',
      ...(parseProgressMap.value[rid] || {}),
      ...patch,
    },
  }
}

function clearParseProgress(rid, delay = 1200) {
  const item = parseProgressMap.value[rid]
  if (item?.timer) clearInterval(item.timer)
  window.setTimeout(() => {
    const next = { ...parseProgressMap.value }
    delete next[rid]
    parseProgressMap.value = next
  }, delay)
}

function startFakeParseProgress(rid) {
  const phases = [
    { limit: 18, label: '读取简历文件' },
    { limit: 44, label: '提取文本内容' },
    { limit: 73, label: '识别候选人信息' },
    { limit: 92, label: '整理结构化结果' },
  ]
  const timer = window.setInterval(() => {
    const current = parseProgressMap.value[rid]
    if (!current || current.status !== 'running') return
    const nextPercent = Math.min(current.percent + Math.max(2, Math.round((100 - current.percent) / 10)), 92)
    const phase = phases.find(item => nextPercent <= item.limit)?.label || phases[phases.length - 1].label
    setParseProgress(rid, { percent: nextPercent, phase, timer })
    if (nextPercent >= 92 && timer) clearInterval(timer)
  }, 280)
  setParseProgress(rid, { percent: 8, phase: '开始解析', timer, status: 'running' })
}

function finishParseProgress(rid, ok = true) {
  const item = parseProgressMap.value[rid]
  if (!item) return
  if (item.timer) clearInterval(item.timer)
  setParseProgress(rid, {
    percent: ok ? 100 : item.percent || 100,
    phase: ok ? '解析完成' : '解析失败',
    status: ok ? 'success' : 'fail',
    timer: null,
  })
  clearParseProgress(rid, ok ? 900 : 2200)
}

function setParsing(rid, value) {
  const next = new Set(parsingIds.value)
  if (value) next.add(rid)
  else next.delete(rid)
  parsingIds.value = next
}

function setSelectedResume(rid, value) {
  const next = new Set(selectedResumeIds.value)
  if (value) next.add(rid)
  else next.delete(rid)
  selectedResumeIds.value = next
}

function toggleBatchMode() {
  batchMode.value = !batchMode.value
  selectedResumeIds.value = new Set()
}

function toggleSelectAll() {
  selectedResumeIds.value = allSelected.value ? new Set() : new Set(selectableResumes.value.map(r => r.id))
}

function setPage(nextPage) {
  page.value = Math.min(Math.max(1, nextPage), totalPages.value)
}

function changePageSize(size) {
  pageSize.value = Number(size)
  page.value = 1
}

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterStatus.value) params.set('parse_status', filterStatus.value)
    if (filterYears.value) params.set('experience_years', filterYears.value)
    params.set('_t', String(Date.now()))
    const qs = params.toString()
    const res = await fetch(`/api/resumes${qs ? '?' + qs : ''}`, { cache: 'no-store' })
    if (res.ok) {
      resumeList.value = await res.json()
      if (page.value > totalPages.value) page.value = totalPages.value
    }
  } catch (_) {}
  loading.value = false
}

onMounted(fetchList)

function resetUploadInput() {
  if (uploadInput.value) uploadInput.value.value = ''
}

function onFileChange(e) {
  const file = e.target?.files?.[0]
  if (file) {
    pendingFile.value = file
    confirmUpload()
  }
}

async function openJdPicker() {
  selectedJdId.value = 0
  pendingFile.value = null
  await loadJdOptions()
  showJdPicker.value = true
}

async function loadJdOptions() {
  try {
    const res = await fetch('/api/jds?page_size=999')
    if (res.ok) {
      const data = await res.json()
      jdOptions.value = data.items.filter(j => j.status === 'enable')
    }
  } catch (_) {}
}

async function confirmUpload() {
  if (!pendingFile.value) return
  if (!(selectedJdId.value > 0)) {
    alert('请先选择一个关联岗位 JD')
    return
  }
  uploading.value = true
  showJdPicker.value = false
  try {
    const fd = new FormData()
    fd.append('file', pendingFile.value)
    fd.append('jd_id', selectedJdId.value)
    const uploadRes = await fetch('/api/resumes/upload', { method: 'POST', body: fd })
    if (!uploadRes.ok) return
    const resume = await uploadRes.json()
    pendingFile.value = null
    resetUploadInput()
    page.value = 1
    await fetchList()
    // 上传后自动解析
    startFakeParseProgress(resume.id)
    const parseRes = await fetch(`/api/resumes/${resume.id}/parse`, { method: 'POST' }).catch(() => null)
    finishParseProgress(resume.id, Boolean(parseRes?.ok))
    await fetchList()
  } catch (_) {}
  uploading.value = false
}

function confirmJdAndChooseFile() {
  if (!(selectedJdId.value > 0)) return
  resetUploadInput()
  uploadInput.value?.click()
  showJdPicker.value = false
}

async function openBindJdPicker(resume) {
  bindingResume.value = resume
  bindingJdId.value = Number(resume?.jd_id || 0)
  await loadJdOptions()
  showBindJdPicker.value = true
}

async function confirmBindJd() {
  if (!bindingResume.value) return
  bindingJdSaving.value = true
  try {
    const jd = jdOptions.value.find(item => Number(item.id) === Number(bindingJdId.value))
    const res = await fetch(`/api/resumes/${bindingResume.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jd_id: bindingJdId.value > 0 ? Number(bindingJdId.value) : null,
        jd_name: bindingJdId.value > 0 ? (jd?.name || '') : '',
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      alert(err.detail || '关联 JD 失败')
      return
    }
    showBindJdPicker.value = false
    bindingResume.value = null
    await fetchList()
    if (viewingResume.value?.id) {
      const current = await fetch(`/api/resumes/${viewingResume.value.id}`)
      if (current.ok) viewingResume.value = await current.json()
    }
  } catch (e) {
    alert('关联 JD 失败: ' + e.message)
  } finally {
    bindingJdSaving.value = false
  }
}

async function parseResume(rid, refresh = true) {
  setParsing(rid, true)
  startFakeParseProgress(rid)
  try {
    const res = await fetch(`/api/resumes/${rid}/parse`, { method: 'POST' })
    if (!res.ok) {
      const err = await res.json()
      finishParseProgress(rid, false)
      alert(err.detail || '解析失败')
      return
    }
    finishParseProgress(rid, true)
    if (refresh) await fetchList()
  } catch (e) {
    finishParseProgress(rid, false)
    alert('解析失败: ' + e.message)
  } finally {
    setParsing(rid, false)
  }
}

async function parsePendingResumes() {
  const targets = parseQueue.value
  if (!targets.length) return
  parsingAll.value = true
  batchParseProgress.value = { current: 0, total: targets.length, percent: 0, active: true }
  let failed = 0
  for (const item of targets) {
    setParsing(item.id, true)
    startFakeParseProgress(item.id)
    try {
      const res = await fetch(`/api/resumes/${item.id}/parse`, { method: 'POST' })
      if (!res.ok) {
        failed += 1
        finishParseProgress(item.id, false)
      } else {
        finishParseProgress(item.id, true)
      }
    } catch (_) {
      failed += 1
      finishParseProgress(item.id, false)
    } finally {
      setParsing(item.id, false)
      batchParseProgress.value = {
        current: batchParseProgress.value.current + 1,
        total: targets.length,
        percent: Math.round(((batchParseProgress.value.current + 1) / targets.length) * 100),
        active: true,
      }
    }
  }
  parsingAll.value = false
  await fetchList()
  window.setTimeout(() => {
    batchParseProgress.value = { current: 0, total: 0, percent: 0, active: false }
  }, 1200)
  if (failed) alert(`简历解析完成，${failed} 份解析失败`)
}

async function parseSelectedResumes() {
  const targets = selectedResumes.value.filter(r => r.file_path && r.parse_status !== 'success')
  if (!targets.length) return
  batchWorking.value = true
  for (const item of targets) {
    await parseResume(item.id, false)
  }
  batchWorking.value = false
  await fetchList()
}

async function deleteSelectedResumes() {
  const targets = selectedResumes.value
  if (!targets.length) return
  if (!confirm(`确认删除选中的 ${targets.length} 份简历？`)) return
  batchWorking.value = true
  for (const item of targets) {
    await fetch(`/api/resumes/${item.id}`, { method: 'DELETE' }).catch(() => {})
  }
  selectedResumeIds.value = new Set()
  batchWorking.value = false
  await fetchList()
}

async function removeResume(rid, name) {
  if (!confirm(`确认删除「${name}」？`)) return
  await fetch(`/api/resumes/${rid}`, { method: 'DELETE' })
  await fetchList()
}

const viewingResume = ref(null)
const editingResume = ref(false)
const savingResume = ref(false)
const editResumeData = ref({})
const parsedResumeData = computed(() => {
  if (!viewingResume.value?.structured_data) return {}
  try {
    return JSON.parse(viewingResume.value.structured_data || '{}')
  } catch (_) {
    return {}
  }
})
const activeResumeData = computed(() => editingResume.value ? editResumeData.value : parsedResumeData.value)
const basicInfo = computed(() => activeResumeData.value?.基础信息 || {})
const selfEvaluation = computed(() => activeResumeData.value?.自我评价 || '')
const educationList = computed(() => asList(activeResumeData.value?.教育经历))
const workList = computed(() => asList(activeResumeData.value?.工作经历))
const projectList = computed(() => asList(activeResumeData.value?.项目经历))
const educationRows = computed(() => buildEducationRows(activeResumeData.value?.教育经历))
const workRows = computed(() => buildExperienceRows(activeResumeData.value?.工作经历, 'work'))
const projectRows = computed(() => buildExperienceRows(activeResumeData.value?.项目经历, 'project'))

async function viewResume(r) {
  viewingResume.value = null
  editingResume.value = false
  editResumeData.value = {}
  try {
    const res = await fetch(`/api/resumes/${r.id}`)
    if (res.ok) viewingResume.value = await res.json()
  } catch (_) {}
}

async function createInterviewPlan(resume, round) {
  const roundLabel = round === 'second' ? '二面' : '一面'
  creatingPlanKey.value = `${resume.id}-${round}`
  try {
    const res = await fetch('/api/plans', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_name: resume.name || '未命名候选人',
        jd_name: resume.jd_name || resume.target_position || '待定岗位',
        interview_round: roundLabel,
        match_score: 0,
        question_count: round === 'second' ? 8 : 10,
        status: 'wait',
        resume_filename: resume.file_path || '',
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      alert(err.detail || '创建面试计划失败')
      return
    }
    createdPlan.value = await res.json()
  } catch (e) {
    alert('创建面试计划失败: ' + e.message)
  } finally {
    creatingPlanKey.value = ''
  }
}

function openWorkflowPicker(resume) {
  workflowResume.value = resume
  workflowBatchMode.value = false
  selectedWorkflowIndex.value = 0
  showWorkflowPicker.value = true
}

function openBatchWorkflowPicker() {
  if (!selectedResumes.value.length) return
  workflowResume.value = null
  workflowBatchMode.value = true
  selectedWorkflowIndex.value = 0
  showWorkflowPicker.value = true
}

async function createInterviewWorkflow() {
  const template = workflowTemplates[selectedWorkflowIndex.value]
  const targets = workflowBatchMode.value ? selectedResumes.value.filter(r => r.parse_status === 'success') : [workflowResume.value].filter(Boolean)
  if (!targets.length || !template) return
  creatingWorkflow.value = true
  try {
    const results = []
    for (const resume of targets) {
      const res = await fetch('/api/plans/workflow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_name: resume.name || '未命名候选人',
          jd_name: resume.jd_name || resume.target_position || '待定岗位',
          workflow_name: template.name,
          resume_filename: resume.file_path || '',
          stages: template.stages,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        alert(err.detail || '创建面试流程失败')
        return
      }
      results.push(await res.json())
    }
    createdPlan.value = results.length === 1 ? results[0] : { workflow_name: template.name, candidate_name: `已为 ${results.length} 位候选人创建流程`, candidate_username: '-', candidate_password: '-', plans: results.flatMap(item => item.plans || []) }
    showWorkflowPicker.value = false
    workflowResume.value = null
    workflowBatchMode.value = false
    selectedResumeIds.value = new Set()
  } catch (e) {
    alert('创建面试流程失败: ' + e.message)
  } finally {
    creatingWorkflow.value = false
  }
}

function fieldValue(obj, keys, fallback = '-') {
  for (const key of keys) {
    const value = obj?.[key]
    if (value !== undefined && value !== null && String(value).trim()) return value
  }
  return fallback
}

function asList(section) {
  return Array.isArray(section) ? section.filter(Boolean) : []
}

function cloneData(data) {
  return JSON.parse(JSON.stringify(data || {}))
}

function normalizeResumeData(data) {
  const next = cloneData(data)
  next.基础信息 = next.基础信息 || {}
  next.教育经历 = asList(next.教育经历).length ? asList(next.教育经历) : [{}]
  next.工作经历 = asList(next.工作经历).length ? asList(next.工作经历) : [{}]
  next.项目经历 = asList(next.项目经历).length ? asList(next.项目经历) : [{}]
  if (next.自我评价 === undefined || next.自我评价 === null) next.自我评价 = ''
  return next
}

function startEditResume() {
  editResumeData.value = normalizeResumeData(parsedResumeData.value)
  editingResume.value = true
}

function cancelEditResume() {
  editingResume.value = false
  editResumeData.value = {}
}

function formatEducationSummary(eduList) {
  const first = asList(eduList)[0]
  if (!first) return ''
  return [first.学位 || first.学历, first.学校].filter(Boolean).join(' | ')
}

function getSkillTags(skills) {
  return String(skills || '')
    .split(/[、,，/|]/)
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 4)
}

function getResumeHeadline(resume) {
  return resume.target_position || resume.jd_name || '待定岗位'
}

function getResumeSummary(resume) {
  const parts = [
    resume.education,
    resume.experience_years,
    resume.jd_name,
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : '等待补充简历概览信息'
}

async function saveResumeEdit() {
  if (!viewingResume.value) return
  savingResume.value = true
  try {
    const data = cloneData(editResumeData.value)
    const base = data.基础信息 || {}
    const res = await fetch(`/api/resumes/${viewingResume.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: base.姓名 || viewingResume.value.name || '',
        target_position: base.意向岗位 || base.岗位名称 || viewingResume.value.target_position || '',
        education: formatEducationSummary(data.教育经历),
        skills: viewingResume.value.skills || '',
        parse_status: 'success',
        structured_data: JSON.stringify(data),
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      alert(err.detail || '保存失败')
      return
    }
    viewingResume.value = await res.json()
    editingResume.value = false
    editResumeData.value = {}
    await fetchList()
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    savingResume.value = false
  }
}

function buildEducationRows(section) {
  const rows = []
  asList(section).forEach(item => {
    rows.push(['学位', fieldValue(item, ['学位']), '学历', fieldValue(item, ['学历', '学位'])])
    rows.push(['学校', fieldValue(item, ['学校']), '专业', fieldValue(item, ['专业'])])
    rows.push(['开始时间', fieldValue(item, ['开始时间']), '结束时间', fieldValue(item, ['结束时间'])])
  })
  return rows
}

function buildExperienceRows(section, type) {
  const rows = []
  asList(section).forEach(item => {
    if (type === 'project') {
      rows.push(['项目名称', fieldValue(item, ['项目名称', '名称']), '角色', fieldValue(item, ['角色'])])
    } else {
      rows.push(['公司', fieldValue(item, ['公司名称', '公司']), '职位', fieldValue(item, ['职位'])])
    }
    rows.push(['开始时间', fieldValue(item, ['开始时间']), '结束时间', fieldValue(item, ['结束时间'])])
    rows.push(['描述', fieldValue(item, ['项目描述', '工作描述', '描述']), '', ''])
  })
  return rows
}

function downloadResume(resume) {
  if (!resume?.file_path) return
  window.open(`/uploads/resume/${resume.file_path}`, '_blank')
}

const statusBadge = (s) => ({ success: 'bg-green-100 text-green-600', wait: 'bg-orange-100 text-orange-600', fail: 'bg-red-100 text-red-600' }[s] || 'bg-gray-100 text-gray-500')
const statusLabel = (s) => ({ success: '解析成功', wait: '待解析', fail: '解析失败' }[s] || s)

function resetFilters() { searchText.value = ''; filterStatus.value = ''; filterYears.value = ''; page.value = 1; fetchList() }
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">简历管理</h2>
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
              <i class="fa fa-id-card-o"></i>
              <span>卡片模式</span>
            </button>
          </div>
          <button
            :class="['px-4 py-2 rounded-lg flex items-center gap-2 transition text-sm border', batchMode ? 'border-orange-300 bg-orange-50 text-orange-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50']"
            @click="toggleBatchMode"
          >
            <i class="fa fa-check-square-o"></i>{{ batchMode ? '退出批量' : '批量管理' }}
          </button>
          <button
            class="px-5 py-2 rounded-lg flex items-center gap-2 transition text-sm border border-[#1677ff] text-[#1677ff] hover:bg-blue-50 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-400 disabled:hover:bg-transparent"
            :disabled="parsingAll || !parseQueue.length"
            @click="parsePendingResumes"
          >
            <i :class="['fa', parsingAll ? 'fa-spinner fa-spin' : 'fa-magic']"></i>
            {{ parsingAll ? '解析中...' : `简历解析${parseQueue.length ? ` (${parseQueue.length})` : ''}` }}
          </button>
          <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 transition text-sm" @click="openJdPicker">
            <i class="fa fa-plus"></i> 上传简历
          </button>
          <input ref="uploadInput" type="file" accept=".pdf,.docx,.doc,.txt,.md" class="hidden" @change="onFileChange" />
        </div>
      </div>

      <div v-if="batchMode" class="bg-white rounded-xl p-4 shadow-sm mb-6 border border-orange-100 flex flex-wrap items-center justify-between gap-3">
        <div class="text-sm text-gray-600">
          已选择 <span class="font-semibold text-orange-600">{{ selectedResumes.length }}</span> 份简历
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button class="px-3 py-2 rounded-lg border border-gray-200 text-sm hover:bg-gray-50" @click="toggleSelectAll">{{ allSelected ? '取消全选' : '全选当前页' }}</button>
          <button class="px-3 py-2 rounded-lg border border-purple-200 text-purple-600 text-sm hover:bg-purple-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedResumes.length" @click="parseSelectedResumes"><i class="fa fa-magic mr-1"></i>批量解析</button>
          <button class="px-3 py-2 rounded-lg border border-green-200 text-green-600 text-sm hover:bg-green-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedResumes.some(r => r.parse_status === 'success')" @click="openBatchWorkflowPicker"><i class="fa fa-sitemap mr-1"></i>批量创建流程</button>
          <button class="px-3 py-2 rounded-lg border border-red-200 text-red-500 text-sm hover:bg-red-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedResumes.length" @click="deleteSelectedResumes"><i class="fa fa-trash-o mr-1"></i>批量删除</button>
        </div>
      </div>

      <div v-if="batchParseProgress.active" class="mb-6 rounded-2xl border border-[#dbe6ff] bg-white p-4 shadow-sm">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-sm font-semibold text-[#1d2941]">简历解析进行中</div>
            <div class="mt-1 text-xs text-[#7c89a2]">已完成 {{ batchParseProgress.current }}/{{ batchParseProgress.total }} 份，系统正在逐份提取结构化信息。</div>
          </div>
          <div class="text-sm font-semibold text-[#2f6df6]">{{ batchParseProgress.percent }}%</div>
        </div>
        <div class="mt-3 h-2 overflow-hidden rounded-full bg-[#edf3ff]">
          <div class="h-full rounded-full bg-[linear-gradient(90deg,#2f6df6_0%,#66a3ff_100%)] transition-all duration-300" :style="{ width: `${batchParseProgress.percent}%` }"></div>
        </div>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-64 relative">
            <input v-model="searchText" type="text" placeholder="搜索候选人姓名、技能、期望岗位" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="page = 1; fetchList()">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterStatus" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="page = 1; fetchList()">
            <option value="">全部解析状态</option>
            <option value="wait">待解析</option>
            <option value="success">解析成功</option>
            <option value="fail">解析失败</option>
          </select>
          <select v-model="filterYears" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="page = 1; fetchList()">
            <option value="">全部工作年限</option>
            <option value="应届生">应届生</option>
            <option value="1-3年">1-3年</option>
            <option value="3-5年">3-5年</option>
            <option value="5年以上">5年以上</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置筛选</button>
        </div>
      </div>

      <!-- 简历内容区 -->
      <div v-if="viewMode === 'list'" class="bg-white rounded-xl shadow-sm overflow-hidden">
        <div v-if="loading" class="text-center py-12 text-gray-400"><i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...</div>
        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th v-if="batchMode" class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-10">
                <input type="checkbox" :checked="allSelected" @change="toggleSelectAll">
              </th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm w-8">#</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">候选人</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">期望岗位</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">学历</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">经验</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">关联 JD</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">技能</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">文件</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">解析状态</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-64">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(r, i) in pagedResumeList" :key="r.id" class="hover:bg-gray-50">
              <td v-if="batchMode" class="px-4 py-3 text-center">
                <input type="checkbox" :checked="selectedResumeIds.has(r.id)" @change="setSelectedResume(r.id, $event.target.checked)">
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ (page - 1) * pageSize + i + 1 }}</td>
              <td class="px-4 py-3 font-medium text-sm">{{ r.name || '未命名' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.target_position || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.education || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.experience_years || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.jd_name || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">{{ r.skills || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-400 max-w-[140px] truncate">{{ r.original_name || r.file_path || '-' }}</td>
              <td class="px-4 py-3">
                <div class="min-w-[180px]">
                  <span :class="['px-2 py-1 text-xs rounded', statusBadge(r.parse_status)]">{{ statusLabel(r.parse_status) }}</span>
                  <div v-if="getParseProgress(r.id)" class="mt-2">
                    <div class="flex items-center justify-between text-[11px] text-[#7b89a4]">
                      <span>{{ getParseProgress(r.id).phase }}</span>
                      <span>{{ getParseProgress(r.id).percent }}%</span>
                    </div>
                    <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-[#edf3ff]">
                      <div
                        class="h-full rounded-full transition-all duration-300"
                        :class="getParseProgress(r.id).status === 'fail' ? 'bg-red-400' : 'bg-[linear-gradient(90deg,#8b5cf6_0%,#2f6df6_100%)]'"
                        :style="{ width: `${getParseProgress(r.id).percent}%` }"
                      ></div>
                    </div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center gap-2">
                  <button class="w-8 h-8 rounded-lg text-[#1677ff] hover:bg-blue-50 transition flex items-center justify-center" title="查看" @click="viewResume(r)"><i class="fa fa-eye"></i></button>
                  <button class="w-8 h-8 rounded-lg text-amber-500 hover:bg-amber-50 transition flex items-center justify-center" title="关联 JD" @click="openBindJdPicker(r)"><i class="fa fa-link"></i></button>
                  <button
                    class="w-8 h-8 rounded-lg text-purple-600 bg-purple-50 hover:bg-purple-100 transition flex items-center justify-center disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-300"
                    :disabled="!r.file_path || parsingAll || parsingIds.has(r.id)"
                    :title="r.parse_status === 'success' ? '重新解析简历' : '解析简历'"
                    @click="parseResume(r.id)"
                  >
                    <i :class="['fa', parsingIds.has(r.id) ? 'fa-spinner fa-spin' : 'fa-magic']"></i>
                  </button>
                  <span class="h-5 w-px bg-gray-200"></span>
                  <div v-if="r.parse_status === 'success'" class="flex items-center rounded-lg border border-green-100 bg-green-50 p-0.5">
                    <button
                      class="h-7 px-3 rounded-md text-xs font-medium text-green-700 hover:bg-white transition disabled:cursor-not-allowed disabled:text-gray-300"
                      :disabled="creatingWorkflow"
                      title="创建面试流程"
                      @click="openWorkflowPicker(r)"
                    >
                      <i class="fa fa-sitemap mr-1"></i>流程
                    </button>
                  </div>
                  <button class="w-8 h-8 rounded-lg text-red-400 hover:bg-red-50 transition flex items-center justify-center" title="删除" @click="removeResume(r.id, r.name)"><i class="fa fa-trash-o"></i></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !resumeList.length" class="text-center py-12 text-gray-400">
          <i class="fa fa-inbox text-3xl mb-2 block"></i>暂无简历，请上传
        </div>
      </div>

      <div v-else>
        <div v-if="loading" class="bg-white rounded-xl shadow-sm text-center py-12 text-gray-400">
          <i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...
        </div>
        <div v-else-if="pagedResumeList.length" class="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-5">
          <article
            v-for="r in pagedResumeList"
            :key="r.id"
            class="group rounded-2xl border border-[#e6edf9] bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(27,76,173,0.10)]"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-start gap-3 min-w-0">
                <label v-if="batchMode" class="pt-1">
                  <input type="checkbox" :checked="selectedResumeIds.has(r.id)" @change="setSelectedResume(r.id, $event.target.checked)">
                </label>
                <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,#eaf2ff_0%,#f5f8ff_100%)] text-[#2f6df6]">
                  <i class="fa fa-user-o text-lg"></i>
                </div>
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <h3 class="text-lg font-semibold text-[#18233e] break-all">{{ r.name || '未命名候选人' }}</h3>
                    <span :class="['px-2.5 py-1 text-xs rounded-full font-medium', statusBadge(r.parse_status)]">{{ statusLabel(r.parse_status) }}</span>
                  </div>
                  <div class="mt-1 text-sm font-medium text-[#4f6488]">{{ getResumeHeadline(r) }}</div>
                  <div class="mt-2 text-xs text-[#7c89a2]">{{ getResumeSummary(r) }}</div>
                </div>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <button class="w-9 h-9 rounded-xl text-[#1677ff] hover:bg-blue-50 transition flex items-center justify-center" title="查看" @click="viewResume(r)"><i class="fa fa-eye"></i></button>
                <button class="w-9 h-9 rounded-xl text-amber-500 hover:bg-amber-50 transition flex items-center justify-center" title="关联 JD" @click="openBindJdPicker(r)"><i class="fa fa-link"></i></button>
                <button
                  class="w-9 h-9 rounded-xl text-purple-600 bg-purple-50 hover:bg-purple-100 transition flex items-center justify-center disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-300"
                  :disabled="!r.file_path || parsingAll || parsingIds.has(r.id)"
                  :title="r.parse_status === 'success' ? '重新解析简历' : '解析简历'"
                  @click="parseResume(r.id)"
                >
                  <i :class="['fa', parsingIds.has(r.id) ? 'fa-spinner fa-spin' : 'fa-magic']"></i>
                </button>
                <button class="w-9 h-9 rounded-xl text-red-400 hover:bg-red-50 transition flex items-center justify-center" title="删除" @click="removeResume(r.id, r.name)"><i class="fa fa-trash-o"></i></button>
              </div>
            </div>

            <div class="mt-4 grid grid-cols-2 gap-3">
              <div class="rounded-xl border border-[#edf2fb] bg-[#fbfcff] px-3 py-3">
                <div class="text-xs text-[#8a97b0]">学历背景</div>
                <div class="mt-1 text-sm font-medium text-[#22304c]">{{ r.education || '待补充' }}</div>
              </div>
              <div class="rounded-xl border border-[#edf2fb] bg-[#fbfcff] px-3 py-3">
                <div class="text-xs text-[#8a97b0]">工作年限</div>
                <div class="mt-1 text-sm font-medium text-[#22304c]">{{ r.experience_years || '待识别' }}</div>
              </div>
            </div>

            <div class="mt-4 flex flex-wrap gap-2">
              <span class="rounded-full border border-[#dce6f7] bg-[#f8fbff] px-2.5 py-1 text-xs text-[#5f708f]">{{ r.jd_name || '未关联 JD' }}</span>
              <span class="rounded-full border border-[#dce6f7] bg-white px-2.5 py-1 text-xs text-[#5f708f]">{{ r.original_name || r.file_path || '无文件名' }}</span>
            </div>

            <div v-if="getParseProgress(r.id)" class="mt-4 rounded-2xl border border-[#e7edfb] bg-[#f9fbff] px-4 py-3">
              <div class="flex items-center justify-between text-xs text-[#70809c]">
                <span>{{ getParseProgress(r.id).phase }}</span>
                <span class="font-medium">{{ getParseProgress(r.id).percent }}%</span>
              </div>
              <div class="mt-2 h-2 overflow-hidden rounded-full bg-[#e8efff]">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  :class="getParseProgress(r.id).status === 'fail' ? 'bg-red-400' : 'bg-[linear-gradient(90deg,#8b5cf6_0%,#2f6df6_100%)]'"
                  :style="{ width: `${getParseProgress(r.id).percent}%` }"
                ></div>
              </div>
            </div>

            <div class="mt-4 rounded-2xl border border-[#edf2fb] bg-[#fcfdff] px-4 py-4">
              <div class="flex items-center justify-between gap-3">
                <div class="text-sm font-semibold text-[#1d2941]">技能概览</div>
                <span class="text-xs text-[#95a1b7]">{{ getSkillTags(r.skills).length ? `${getSkillTags(r.skills).length} 个标签` : '待解析' }}</span>
              </div>
              <div v-if="getSkillTags(r.skills).length" class="mt-3 flex flex-wrap gap-2">
                <span
                  v-for="tag in getSkillTags(r.skills)"
                  :key="tag"
                  class="rounded-full bg-white px-2.5 py-1 text-xs text-[#5f708f] border border-[#dce6f7]"
                >
                  {{ tag }}
                </span>
              </div>
              <p v-else class="mt-2 text-sm leading-6 text-[#7f8ca4]">这份简历还没有提取出稳定的技能标签，解析成功后会在这里展示候选人的能力关键词。</p>
            </div>

            <div class="mt-4 flex items-center justify-between gap-3">
              <div class="text-xs text-[#8b98af]">简历 ID：{{ r.id }}</div>
              <button
                v-if="r.parse_status === 'success'"
                class="inline-flex items-center gap-2 rounded-xl border border-green-100 bg-green-50 px-3 py-2 text-xs font-medium text-green-700 transition hover:bg-green-100 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="creatingWorkflow"
                @click="openWorkflowPicker(r)"
              >
                <i class="fa fa-sitemap"></i>
                <span>创建流程</span>
              </button>
              <span v-else class="text-xs text-[#9aa6bc]">解析完成后可创建流程</span>
            </div>
          </article>
        </div>
        <div v-else class="bg-white rounded-xl shadow-sm text-center py-12 text-gray-400">
          <i class="fa fa-inbox text-3xl mb-2 block"></i>暂无简历，请上传
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 mt-4 text-sm text-gray-500">
        <div class="flex items-center gap-3">
          <span>共 {{ resumeList.length }} 条</span>
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

    <!-- 查看简历弹窗 - 左右分栏 -->
    <div v-if="viewingResume" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-2" @click.self="viewingResume = null">
      <div class="bg-white rounded-lg w-[calc(100vw-24px)] max-w-[1800px] h-[92vh] flex flex-col shadow-xl overflow-hidden">
        <!-- Header -->
        <div class="flex-shrink-0 h-[52px] px-6 border-b flex items-center justify-between">
          <button class="text-[#1677ff] text-sm font-medium hover:text-blue-600" @click="viewingResume = null">编辑候选人</button>
          <div class="flex items-center gap-2">
          <button
            class="h-8 px-3 border border-gray-200 rounded text-xs text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-300"
            :disabled="!viewingResume.file_path"
            @click="downloadResume(viewingResume)"
          >
            <i class="fa fa-download mr-1"></i>下载简历
          </button>
            <button
              class="h-8 px-3 border border-amber-200 bg-amber-50 text-amber-700 rounded text-xs hover:bg-amber-100"
              @click="openBindJdPicker(viewingResume)"
            >
              <i class="fa fa-link mr-1"></i>{{ viewingResume.jd_name ? '修改关联 JD' : '关联 JD' }}
            </button>
            <button
              v-if="!editingResume"
              class="h-8 px-3 bg-[#1677ff] text-white rounded text-xs hover:bg-blue-600"
              @click="startEditResume"
            >
              <i class="fa fa-pencil-square-o mr-1"></i>编辑
            </button>
            <template v-else>
              <button
                class="h-8 px-3 border border-gray-200 rounded text-xs text-gray-600 hover:bg-gray-50"
                :disabled="savingResume"
                @click="cancelEditResume"
              >取消</button>
              <button
                class="h-8 px-3 bg-[#1677ff] text-white rounded text-xs hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-blue-300"
                :disabled="savingResume"
                @click="saveResumeEdit"
              >
                <i :class="['fa mr-1', savingResume ? 'fa-spinner fa-spin' : 'fa-save']"></i>{{ savingResume ? '保存中' : '保存' }}
              </button>
            </template>
            <button class="ml-2 text-gray-300 hover:text-gray-500" @click="viewingResume = null"><i class="fa fa-times text-lg"></i></button>
          </div>
        </div>

        <!-- Body - 左右分栏 -->
        <div class="flex-1 flex overflow-hidden bg-white">
          <!-- 左侧：PDF 原文 -->
          <div class="w-1/2 border-r border-gray-200 overflow-hidden bg-white flex flex-col">
            <h4 class="flex-shrink-0 text-center text-xs font-semibold text-gray-400 px-4 py-3 bg-white border-b truncate">{{ viewingResume.original_name || viewingResume.file_path || '简历原文' }}</h4>
            <div class="flex-1">
              <embed
                v-if="viewingResume.file_path"
                :src="'/uploads/resume/' + viewingResume.file_path"
                type="application/pdf"
                class="w-full h-full"
              />
              <div v-else class="flex items-center justify-center h-full text-gray-400">
                <p class="text-sm">无文件</p>
              </div>
            </div>
          </div>

          <!-- 右侧：解析数据 -->
          <div class="w-1/2 overflow-auto bg-white p-4">
            <div v-if="viewingResume.parse_status === 'success' && viewingResume.structured_data">
              <table class="w-full table-fixed border-collapse text-[12px] leading-5 text-gray-700">
                <tbody>
                  <tr>
                    <th class="w-[76px] bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">姓名</th>
                    <td colspan="2" class="border border-gray-200 px-3 py-2">
                      <input v-if="editingResume" v-model="editResumeData.基础信息.姓名" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]">
                      <span v-else>{{ fieldValue(basicInfo, ['姓名'], viewingResume.name || '-') }}</span>
                    </td>
                    <th class="w-[76px] bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">性别</th>
                    <td class="border border-gray-200 px-3 py-2">
                      <input v-if="editingResume" v-model="editResumeData.基础信息.性别" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]">
                      <span v-else>{{ fieldValue(basicInfo, ['性别']) }}</span>
                    </td>
                  </tr>
                  <tr>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">岗位名称</th>
                    <td colspan="2" class="border border-gray-200 px-3 py-2">
                      <input v-if="editingResume" v-model="editResumeData.基础信息.意向岗位" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]">
                      <span v-else>{{ fieldValue(basicInfo, ['意向岗位', '岗位名称'], viewingResume.target_position || '-') }}</span>
                    </td>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">邮箱</th>
                    <td class="border border-gray-200 px-3 py-2">
                      <input v-if="editingResume" v-model="editResumeData.基础信息.邮箱" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]">
                      <span v-else>{{ fieldValue(basicInfo, ['邮箱', '电子邮箱']) }}</span>
                    </td>
                  </tr>
                  <tr>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">电话</th>
                    <td colspan="2" class="border border-gray-200 px-3 py-2">
                      <input v-if="editingResume" v-model="editResumeData.基础信息.电话" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]">
                      <span v-else>{{ fieldValue(basicInfo, ['电话', '手机', '手机号']) }}</span>
                    </td>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">年龄</th>
                    <td class="border border-gray-200 px-3 py-2">
                      <input v-if="editingResume" v-model="editResumeData.基础信息.年龄" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]">
                      <span v-else>{{ fieldValue(basicInfo, ['年龄']) }}</span>
                    </td>
                  </tr>
                  <tr>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">籍贯</th>
                    <td colspan="2" class="border border-gray-200 px-3 py-2">
                      <input v-if="editingResume" v-model="editResumeData.基础信息.籍贯" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]">
                      <span v-else>{{ fieldValue(basicInfo, ['籍贯']) }}</span>
                    </td>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">地址</th>
                    <td class="border border-gray-200 px-3 py-2">
                      <input v-if="editingResume" v-model="editResumeData.基础信息.地址" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]">
                      <span v-else>{{ fieldValue(basicInfo, ['地址', '现居地']) }}</span>
                    </td>
                  </tr>
                  <tr>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">自我评价</th>
                    <td colspan="4" class="border border-gray-200 px-3 py-2">
                      <textarea v-if="editingResume" v-model="editResumeData.自我评价" rows="3" class="w-full resize-y bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></textarea>
                      <span v-else>{{ selfEvaluation || '-' }}</span>
                    </td>
                  </tr>

                  <template v-if="editingResume">
                    <template v-for="(edu, i) in educationList" :key="'edit-edu-' + i">
                      <tr>
                        <th v-if="i === 0" :rowspan="educationList.length * 3" class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">教育经历</th>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">学位</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="edu.学位" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">学历</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="edu.学历" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                      </tr>
                      <tr>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">学校</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="edu.学校" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">专业</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="edu.专业" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                      </tr>
                      <tr>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">开始时间</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="edu.开始时间" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">结束时间</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="edu.结束时间" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                      </tr>
                    </template>
                  </template>
                  <tr v-else v-for="(row, i) in educationRows" :key="'edu-' + i">
                    <th v-if="i === 0" :rowspan="educationRows.length" class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">教育经历</th>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">{{ row[0] }}</th>
                    <td class="border border-gray-200 px-3 py-2">{{ row[1] }}</td>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">{{ row[2] }}</th>
                    <td class="border border-gray-200 px-3 py-2">{{ row[3] }}</td>
                  </tr>

                  <template v-if="editingResume">
                    <template v-for="(job, i) in workList" :key="'edit-work-' + i">
                      <tr>
                        <th v-if="i === 0" :rowspan="workList.length * 3" class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">工作经历</th>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">公司</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="job.公司名称" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">职位</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="job.职位" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                      </tr>
                      <tr>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">开始时间</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="job.开始时间" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">结束时间</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="job.结束时间" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                      </tr>
                      <tr>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">描述</th>
                        <td colspan="3" class="border border-gray-200 px-3 py-2"><textarea v-model="job.工作描述" rows="4" class="w-full resize-y bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></textarea></td>
                      </tr>
                    </template>
                  </template>
                  <tr v-else v-for="(row, i) in workRows" :key="'work-' + i">
                    <th v-if="i === 0" :rowspan="workRows.length" class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">工作经历</th>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">{{ row[0] }}</th>
                    <td :colspan="row[2] ? 1 : 3" class="border border-gray-200 px-3 py-2 whitespace-pre-line">{{ row[1] }}</td>
                    <th v-if="row[2]" class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">{{ row[2] }}</th>
                    <td v-if="row[2]" class="border border-gray-200 px-3 py-2">{{ row[3] }}</td>
                  </tr>

                  <template v-if="editingResume">
                    <template v-for="(project, i) in projectList" :key="'edit-project-' + i">
                      <tr>
                        <th v-if="i === 0" :rowspan="projectList.length * 3" class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">项目经历</th>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">项目名称</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="project.项目名称" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">角色</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="project.角色" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                      </tr>
                      <tr>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">开始时间</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="project.开始时间" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">结束时间</th>
                        <td class="border border-gray-200 px-3 py-2"><input v-model="project.结束时间" class="w-full bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></td>
                      </tr>
                      <tr>
                        <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">描述</th>
                        <td colspan="3" class="border border-gray-200 px-3 py-2"><textarea v-model="project.项目描述" rows="4" class="w-full resize-y bg-blue-50/60 border border-blue-200 rounded px-2 py-1 outline-none focus:border-[#1677ff]"></textarea></td>
                      </tr>
                    </template>
                  </template>
                  <tr v-else v-for="(row, i) in projectRows" :key="'project-' + i">
                    <th v-if="i === 0" :rowspan="projectRows.length" class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">项目经历</th>
                    <th class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">{{ row[0] }}</th>
                    <td :colspan="row[2] ? 1 : 3" class="border border-gray-200 px-3 py-2 whitespace-pre-line">{{ row[1] }}</td>
                    <th v-if="row[2]" class="bg-gray-50 border border-gray-200 px-3 py-2 text-center font-semibold text-gray-600">{{ row[2] }}</th>
                    <td v-if="row[2]" class="border border-gray-200 px-3 py-2">{{ row[3] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="text-center py-12 text-gray-400">
              <i class="fa fa-file-text-o text-3xl mb-2 block"></i>
              <p class="text-sm">尚未解析，请先上传文件并点击解析按钮</p>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- 面试流程模板弹窗 -->
    <div v-if="showWorkflowPicker" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="showWorkflowPicker = false">
      <div class="bg-white rounded-2xl w-[760px] max-w-[96vw] shadow-xl overflow-hidden">
        <div class="px-6 py-5 border-b flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold text-gray-900">选择面试流程</h3>
            <p class="text-sm text-gray-500 mt-1">
              <template v-if="workflowBatchMode">已选择 {{ selectedResumes.length }} 份简历，将为解析成功的简历创建流程</template>
              <template v-else>{{ workflowResume?.name || '候选人' }} · {{ workflowResume?.jd_name || workflowResume?.target_position || '待定岗位' }}</template>
            </p>
          </div>
          <button class="text-gray-300 hover:text-gray-500" @click="showWorkflowPicker = false"><i class="fa fa-times text-lg"></i></button>
        </div>
        <div class="p-6 grid grid-cols-1 gap-4">
          <label
            v-for="(template, index) in workflowTemplates"
            :key="template.name"
            :class="['block rounded-xl border p-4 cursor-pointer transition', selectedWorkflowIndex === index ? 'border-[#1677ff] bg-blue-50' : 'border-gray-200 hover:bg-gray-50']"
          >
            <input v-model="selectedWorkflowIndex" type="radio" :value="index" class="hidden">
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="font-semibold text-gray-900">{{ template.name }}</div>
                <div class="text-xs text-gray-500 mt-1">{{ template.desc }}</div>
              </div>
              <span class="px-2 py-1 rounded bg-white text-xs text-[#1677ff] border border-blue-100">{{ template.stages.length }} 个面试计划</span>
            </div>
            <div class="mt-4 flex items-center gap-2 overflow-x-auto pb-1">
              <template v-for="(stage, stageIndex) in template.stages" :key="stage.name">
                <div class="flex-shrink-0 rounded-lg border border-gray-200 bg-white px-3 py-2 min-w-[110px]">
                  <div class="text-xs text-gray-400">第 {{ stageIndex + 1 }} 环节</div>
                  <div class="text-sm font-medium text-gray-800 mt-1">{{ stage.name }}</div>
                  <div class="text-xs text-gray-400 mt-1">{{ stage.question_count }} 道题</div>
                </div>
                <i v-if="stageIndex < template.stages.length - 1" class="fa fa-long-arrow-right text-gray-300"></i>
              </template>
            </div>
          </label>
        </div>
        <div class="px-6 py-4 bg-gray-50 border-t flex justify-end gap-3">
          <button class="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-white" :disabled="creatingWorkflow" @click="showWorkflowPicker = false">取消</button>
          <button class="px-4 py-2 rounded-lg bg-[#1677ff] text-white text-sm hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-blue-300" :disabled="creatingWorkflow" @click="createInterviewWorkflow">
            <i :class="['fa mr-1', creatingWorkflow ? 'fa-spinner fa-spin' : 'fa-sitemap']"></i>{{ creatingWorkflow ? '生成中' : '生成面试流程' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 面试计划账号弹窗 -->
    <div v-if="createdPlan" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="createdPlan = null">
      <div class="bg-white rounded-2xl w-[520px] max-w-[95vw] shadow-xl overflow-hidden">
        <div class="px-6 py-5 border-b flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold text-gray-900">{{ createdPlan.plans ? '面试流程已创建' : '面试计划已创建' }}</h3>
            <p class="text-sm text-gray-500 mt-1">
              <template v-if="createdPlan.plans">{{ createdPlan.workflow_name }} · {{ createdPlan.candidate_name }} · 已生成 {{ createdWorkflowPlans.length }} 个面试计划</template>
              <template v-else>{{ createdPlan.interview_round || '面试' }} · {{ createdPlan.candidate_name }} · {{ createdPlan.jd_name }}</template>
            </p>
          </div>
          <button class="text-gray-300 hover:text-gray-500" @click="createdPlan = null"><i class="fa fa-times text-lg"></i></button>
        </div>
        <div class="p-6 space-y-4">
          <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
            <div class="text-sm font-semibold text-blue-700 mb-3">面试者登录账号</div>
            <div class="grid grid-cols-[80px_1fr] gap-y-3 text-sm">
              <div class="text-gray-500">用户名</div>
              <div class="font-mono font-semibold text-gray-900 select-all">{{ createdPlan.candidate_username }}</div>
              <div class="text-gray-500">密码</div>
              <div class="font-mono font-semibold text-gray-900 select-all">{{ createdPlan.candidate_password }}</div>
            </div>
          </div>
          <div v-if="createdPlan.plans" class="rounded-xl border border-gray-200 overflow-hidden">
            <div class="px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-500">已生成计划</div>
            <div class="divide-y divide-gray-100">
              <div v-for="plan in createdWorkflowPlans" :key="plan.id" class="px-4 py-3 flex items-center justify-between text-sm">
                <div>
                  <span class="font-medium text-gray-800">{{ plan.interview_round }}</span>
                  <span class="text-gray-400 ml-2">第 {{ plan.stage_order }}/{{ plan.stage_count }} 环节</span>
                </div>
                <span class="text-xs text-gray-400">{{ plan.question_count }} 道题</span>
              </div>
            </div>
          </div>
          <p class="text-xs text-gray-500 leading-relaxed">把这组账号密码发给面试者，面试者可用于登录系统进入对应面试流程。</p>
        </div>
        <div class="px-6 py-4 bg-gray-50 border-t flex justify-end gap-3">
          <button class="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-white" @click="createdPlan = null">关闭</button>
          <button class="px-4 py-2 rounded-lg bg-[#1677ff] text-white text-sm hover:bg-blue-600" @click="router.push('/plan-manager')">查看面试计划</button>
        </div>
      </div>
    </div>

    <!-- JD 选择弹窗 -->
    <div v-if="showJdPicker" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showJdPicker = false">
      <div class="bg-white rounded-2xl w-[480px] p-6 shadow-xl">
        <h3 class="text-lg font-bold mb-2">先选择岗位 JD</h3>
        <p class="text-sm text-gray-500 mb-4">请先选择一个岗位，确认后再进入简历文件选择。这样后续解析、打分和面试流程都会自动关联。</p>
        <div class="space-y-2 max-h-64 overflow-auto">
          <label
            v-for="jd in jdOptions"
            :key="jd.id"
            :class="['flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition', selectedJdId === jd.id ? 'border-[#1677ff] bg-blue-50' : 'border-gray-200 hover:bg-gray-50']"
          >
            <input v-model="selectedJdId" type="radio" :value="jd.id" class="hidden">
            <div class="flex-1">
              <div class="font-medium text-sm">{{ jd.name }}</div>
              <div class="text-xs text-gray-500">{{ jd.category }} · {{ jd.location }} · {{ jd.recruitment_type }}</div>
            </div>
          </label>
        </div>
        <div class="flex justify-end gap-3 mt-5">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="showJdPicker = false; pendingFile = null">取消</button>
          <button
            class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600 text-sm disabled:cursor-not-allowed disabled:bg-blue-300"
            :disabled="!(selectedJdId > 0)"
            @click="confirmJdAndChooseFile"
          >
            下一步：选择简历
          </button>
        </div>
      </div>
    </div>

    <div v-if="showBindJdPicker" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showBindJdPicker = false">
      <div class="bg-white rounded-2xl w-[480px] p-6 shadow-xl">
        <h3 class="text-lg font-bold mb-2">设置关联岗位 JD</h3>
        <p class="text-sm text-gray-500 mb-4">
          {{ bindingResume?.name || '未命名候选人' }} · {{ bindingResume?.original_name || bindingResume?.file_path || '无文件名' }}
        </p>
        <div class="space-y-2 max-h-64 overflow-auto">
          <label
            v-for="jd in jdOptions"
            :key="'bind-' + jd.id"
            :class="['flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition', Number(bindingJdId) === Number(jd.id) ? 'border-[#1677ff] bg-blue-50' : 'border-gray-200 hover:bg-gray-50']"
          >
            <input v-model="bindingJdId" type="radio" :value="jd.id" class="hidden">
            <div class="flex-1">
              <div class="font-medium text-sm">{{ jd.name }}</div>
              <div class="text-xs text-gray-500">{{ jd.category }} · {{ jd.location }} · {{ jd.recruitment_type }}</div>
            </div>
          </label>
          <label
            :class="['flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition', Number(bindingJdId) === 0 ? 'border-gray-400 bg-gray-100' : 'border-gray-200 hover:bg-gray-50']"
          >
            <input v-model="bindingJdId" type="radio" :value="0" class="hidden">
            <div class="flex-1 text-sm text-gray-500">清空关联</div>
          </label>
        </div>
        <div class="flex justify-end gap-3 mt-5">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" :disabled="bindingJdSaving" @click="showBindJdPicker = false; bindingResume = null">取消</button>
          <button class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600 text-sm disabled:cursor-not-allowed disabled:bg-blue-300" :disabled="bindingJdSaving" @click="confirmBindJd">
            <i :class="['fa mr-1', bindingJdSaving ? 'fa-spinner fa-spin' : 'fa-save']"></i>{{ bindingJdSaving ? '保存中' : '保存关联' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
