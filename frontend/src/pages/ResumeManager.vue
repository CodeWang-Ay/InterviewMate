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
const searchText = ref('')
const filterStatus = ref('')
const filterYears = ref('')
const showJdPicker = ref(false)
const pendingFile = ref(null)
const selectedJdId = ref(0)
const jdOptions = ref([])
const creatingPlanKey = ref('')
const createdPlan = ref(null)
const createdWorkflowPlans = computed(() => (createdPlan.value?.plans || []).filter(Boolean))
const showWorkflowPicker = ref(false)
const workflowResume = ref(null)
const selectedWorkflowIndex = ref(0)
const creatingWorkflow = ref(false)

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

function setParsing(rid, value) {
  const next = new Set(parsingIds.value)
  if (value) next.add(rid)
  else next.delete(rid)
  parsingIds.value = next
}

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
  } catch (_) {}
  loading.value = false
}

onMounted(fetchList)

function onFileChange(e) {
  const file = e.target?.files?.[0]
  if (file) openJdPicker(file)
}

async function openJdPicker(file) {
  pendingFile.value = file
  selectedJdId.value = 0
  try {
    const res = await fetch('/api/jds?page_size=999')
    if (res.ok) {
      const data = await res.json()
      jdOptions.value = data.items.filter(j => j.status === 'enable')
    }
  } catch (_) {}
  showJdPicker.value = true
}

async function confirmUpload() {
  if (!pendingFile.value) return
  uploading.value = true
  showJdPicker.value = false
  try {
    const fd = new FormData()
    fd.append('file', pendingFile.value)
    if (selectedJdId.value > 0) fd.append('jd_id', selectedJdId.value)
    const uploadRes = await fetch('/api/resumes/upload', { method: 'POST', body: fd })
    if (!uploadRes.ok) return
    const resume = await uploadRes.json()
    pendingFile.value = null
    // 上传后自动解析
    await fetch(`/api/resumes/${resume.id}/parse`, { method: 'POST' }).catch(() => {})
    await fetchList()
  } catch (_) {}
  uploading.value = false
}

async function parseResume(rid, refresh = true) {
  setParsing(rid, true)
  try {
    const res = await fetch(`/api/resumes/${rid}/parse`, { method: 'POST' })
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || '解析失败')
      return
    }
    if (refresh) await fetchList()
  } catch (e) {
    alert('解析失败: ' + e.message)
  } finally {
    setParsing(rid, false)
  }
}

async function parsePendingResumes() {
  const targets = parseQueue.value
  if (!targets.length) return
  parsingAll.value = true
  let failed = 0
  for (const item of targets) {
    setParsing(item.id, true)
    try {
      const res = await fetch(`/api/resumes/${item.id}/parse`, { method: 'POST' })
      if (!res.ok) failed += 1
    } catch (_) {
      failed += 1
    } finally {
      setParsing(item.id, false)
    }
  }
  parsingAll.value = false
  await fetchList()
  if (failed) alert(`简历解析完成，${failed} 份解析失败`)
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
  selectedWorkflowIndex.value = 0
  showWorkflowPicker.value = true
}

async function createInterviewWorkflow() {
  const resume = workflowResume.value
  const template = workflowTemplates[selectedWorkflowIndex.value]
  if (!resume || !template) return
  creatingWorkflow.value = true
  try {
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
    createdPlan.value = await res.json()
    showWorkflowPicker.value = false
    workflowResume.value = null
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

function resetFilters() { searchText.value = ''; filterStatus.value = ''; filterYears.value = ''; fetchList() }
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">简历管理</h2>
        <div class="flex items-center gap-3">
          <button
            class="px-5 py-2 rounded-lg flex items-center gap-2 transition text-sm border border-[#1677ff] text-[#1677ff] hover:bg-blue-50 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-400 disabled:hover:bg-transparent"
            :disabled="parsingAll || !parseQueue.length"
            @click="parsePendingResumes"
          >
            <i :class="['fa', parsingAll ? 'fa-spinner fa-spin' : 'fa-magic']"></i>
            {{ parsingAll ? '解析中...' : `简历解析${parseQueue.length ? ` (${parseQueue.length})` : ''}` }}
          </button>
          <label class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 transition cursor-pointer text-sm">
            <i class="fa fa-plus"></i> 上传简历
            <input type="file" accept=".pdf,.docx,.doc,.txt,.md" class="hidden" @change="onFileChange" />
          </label>
        </div>
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

      <!-- 简历表格 -->
      <div class="bg-white rounded-xl shadow-sm overflow-hidden">
        <div v-if="loading" class="text-center py-12 text-gray-400"><i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...</div>
        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
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
            <tr v-for="(r, i) in resumeList" :key="r.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm text-gray-500">{{ i + 1 }}</td>
              <td class="px-4 py-3 font-medium text-sm">{{ r.name || '未命名' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.target_position || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.education || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.experience_years || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.jd_name || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">{{ r.skills || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-400 max-w-[140px] truncate">{{ r.original_name || r.file_path || '-' }}</td>
              <td class="px-4 py-3"><span :class="['px-2 py-1 text-xs rounded', statusBadge(r.parse_status)]">{{ statusLabel(r.parse_status) }}</span></td>
              <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center gap-2">
                  <button class="w-8 h-8 rounded-lg text-[#1677ff] hover:bg-blue-50 transition flex items-center justify-center" title="查看" @click="viewResume(r)"><i class="fa fa-eye"></i></button>
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

      <p class="text-sm text-gray-500 mt-4">共 {{ resumeList.length }} 条</p>
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
            <p class="text-sm text-gray-500 mt-1">{{ workflowResume?.name || '候选人' }} · {{ workflowResume?.jd_name || workflowResume?.target_position || '待定岗位' }}</p>
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
        <h3 class="text-lg font-bold mb-2">选择关联岗位 JD</h3>
        <p class="text-sm text-gray-500 mb-4">文件：{{ pendingFile?.name }}</p>
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
          <label
            :class="['flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition', selectedJdId === 0 ? 'border-gray-400 bg-gray-100' : 'border-gray-200 hover:bg-gray-50']"
          >
            <input v-model="selectedJdId" type="radio" :value="0" class="hidden">
            <div class="flex-1 text-sm text-gray-500">暂不关联（稍后设置）</div>
          </label>
        </div>
        <div class="flex justify-end gap-3 mt-5">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="showJdPicker = false; pendingFile = null">取消</button>
          <button class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600 text-sm" @click="confirmUpload">确认上传</button>
        </div>
      </div>
    </div>
  </div>
</template>
