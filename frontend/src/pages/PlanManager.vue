<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const route = useRoute()
const planList = ref([])
const loading = ref(true)
const searchText = ref(String(route.query.candidate || route.query.search || ''))
const filterStatus = ref('')
const batchMode = ref(false)
const selectedPlanIds = ref(new Set())
const batchWorking = ref(false)
const page = ref(1)
const pageSize = ref(10)
const workflowGroup = ref(null)
const editingPlanId = ref(null)
const editForm = ref({})
const savingPlan = ref(false)
const launchPlan = ref(null)
const copiedCredentialKey = ref('')
const previewPlan = ref(null)

const allPlanGroups = computed(() => {
  const map = new Map()
  planList.value.forEach((plan) => {
    const key = groupKey(plan)
    if (!map.has(key)) {
      map.set(key, {
        key,
        candidate_name: plan.candidate_name || '未命名候选人',
        jd_name: plan.jd_name || '-',
        workflow_name: plan.workflow_name || '面试流程',
        candidate_username: plan.candidate_username || '',
        candidate_password: plan.candidate_password || '',
        created_at: plan.created_at || '',
        plans: [],
      })
    }
    const group = map.get(key)
    group.plans.push(plan)
    if (!group.candidate_username && plan.candidate_username) group.candidate_username = plan.candidate_username
    if (!group.candidate_password && plan.candidate_password) group.candidate_password = plan.candidate_password
    if (plan.created_at && (!group.created_at || plan.created_at < group.created_at)) group.created_at = plan.created_at
  })

  return Array.from(map.values()).map((group) => {
    group.plans.sort((a, b) => (a.stage_order || 1) - (b.stage_order || 1) || a.id - b.id)
    group.stage_count = Math.max(...group.plans.map(p => p.stage_count || group.plans.length), group.plans.length)
    group.finished_count = group.plans.filter(p => p.status === 'finish').length
    group.status = groupStatus(group.plans)
    group.current_plan = group.plans.find(p => ['running', 'wait'].includes(p.status)) || group.plans[0]
    group.match_score = Math.round(group.plans.reduce((sum, p) => sum + Number(p.match_score || 0), 0) / group.plans.length)
    group.question_count = group.plans.reduce((sum, p) => sum + Number(p.question_count || 0), 0)
    return group
  }).sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
})

const groupedPlanList = computed(() => {
  if (!filterStatus.value) return allPlanGroups.value
  return allPlanGroups.value.filter(group => group.status === filterStatus.value)
})

const selectedPlans = computed(() => planList.value.filter(p => selectedPlanIds.value.has(p.id)))
const totalPages = computed(() => Math.max(1, Math.ceil(groupedPlanList.value.length / pageSize.value)))
const pagedPlanGroups = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return groupedPlanList.value.slice(start, start + pageSize.value)
})
const pagedPlanIds = computed(() => pagedPlanGroups.value.flatMap(group => group.plans.map(plan => plan.id)))
const allSelected = computed(() => pagedPlanIds.value.length > 0 && pagedPlanIds.value.every(id => selectedPlanIds.value.has(id)))
const visiblePages = computed(() => {
  const total = totalPages.value
  const start = Math.max(1, Math.min(page.value - 2, Math.max(1, total - 4)))
  const end = Math.min(total, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

const planStats = computed(() => {
  const groups = allPlanGroups.value
  const count = (status) => groups.filter(group => group.status === status).length
  const finishedStages = planList.value.filter(plan => plan.status === 'finish').length
  const totalStages = planList.value.length
  return {
    candidates: groups.length,
    stages: totalStages,
    waiting: count('wait'),
    running: count('running'),
    pending: count('pending'),
    finished: count('finish'),
    partial: count('partial'),
    completionRate: totalStages ? Math.round(finishedStages / totalStages * 100) : 0,
  }
})

const statusQuickFilters = [
  { label: '全部', value: '', icon: 'fa-list-ul' },
  { label: '待发起', value: 'wait', icon: 'fa-play-circle-o' },
  { label: '面试中', value: 'running', icon: 'fa-comments-o' },
  { label: '待前序', value: 'pending', icon: 'fa-hourglass-half' },
  { label: '已完成', value: 'finish', icon: 'fa-check-circle-o' },
]

function groupKey(plan) {
  if (plan.workflow_id) return `wf:${plan.workflow_id}`
  if (plan.candidate_username) return `user:${plan.candidate_username}`
  return `candidate:${plan.candidate_name || ''}:${plan.jd_name || ''}`
}

function groupStatus(plans) {
  if (plans.length && plans.every(p => p.status === 'finish')) return 'finish'
  if (plans.length && plans.every(p => p.status === 'cancel')) return 'cancel'
  if (plans.some(p => p.status === 'running')) return 'running'
  if (plans.some(p => p.status === 'wait')) return 'wait'
  if (plans.some(p => p.status === 'finish')) return 'partial'
  if (plans.some(p => p.status === 'pending')) return 'pending'
  return plans[0]?.status || 'pending'
}

function progressPercent(group) {
  if (!group?.stage_count) return 0
  return Math.min(100, Math.round(group.finished_count / group.stage_count * 100))
}

function currentStageLabel(group) {
  const plan = group?.current_plan
  if (!plan) return '暂无环节'
  if (group.status === 'finish') return '全部完成'
  return `${plan.stage_order || 1}/${group.stage_count || group.plans.length} ${plan.interview_round || '面试'}`
}

function nextActionText(group) {
  const plan = group?.current_plan
  if (!plan) return '暂无动作'
  if (plan.status === 'wait') return '可发起'
  if (plan.status === 'running') return '已发起，等待面试'
  if (group.status === 'finish') return '流程已完成'
  if (group.status === 'pending') return '等待上一轮完成'
  if (group.status === 'partial') return '继续推进下一轮'
  if (group.status === 'cancel') return '流程已作废'
  return statusLabel(group.status)
}

function formatSchedule(value) {
  if (!value) return '未预约'
  return String(value).replace('T', ' ').slice(0, 16)
}

function toDatetimeLocal(value) {
  if (!value) return ''
  return String(value).replace(' ', 'T').slice(0, 16)
}

function currentPlanMeta(group) {
  const plan = group?.current_plan
  if (!plan) return '未分配面试官'
  const interviewer = plan.interviewer || '未分配面试官'
  return `${formatSchedule(plan.scheduled_at)} · ${interviewer}`
}

function resultLabel(plan) {
  if (!plan?.interview_result) return '未录入'
  return {
    pass: '通过',
    reject: '不通过',
    pending: '待定',
  }[plan.interview_result] || plan.interview_result
}

function resultBadgeClass(result) {
  return {
    pass: 'bg-green-50 text-green-700 border-green-100',
    reject: 'bg-red-50 text-red-600 border-red-100',
    pending: 'bg-amber-50 text-amber-700 border-amber-100',
  }[result] || 'bg-gray-50 text-gray-500 border-gray-100'
}

function stagePillClass(status) {
  return {
    wait: 'bg-blue-50 text-blue-700 border-blue-100',
    pending: 'bg-gray-50 text-gray-500 border-gray-100',
    running: 'bg-orange-50 text-orange-700 border-orange-100',
    finish: 'bg-green-50 text-green-700 border-green-100',
    cancel: 'bg-gray-100 text-gray-400 border-gray-200',
  }[status] || 'bg-indigo-50 text-indigo-600 border-indigo-100'
}

function setSelectedGroup(group, value) {
  const next = new Set(selectedPlanIds.value)
  group.plans.forEach((plan) => {
    if (value) next.add(plan.id)
    else next.delete(plan.id)
  })
  selectedPlanIds.value = next
}

function isGroupSelected(group) {
  return group.plans.length > 0 && group.plans.every(plan => selectedPlanIds.value.has(plan.id))
}

function toggleBatchMode() {
  batchMode.value = !batchMode.value
  selectedPlanIds.value = new Set()
}

function toggleSelectAll() {
  const next = new Set(selectedPlanIds.value)
  if (allSelected.value) pagedPlanIds.value.forEach(id => next.delete(id))
  else pagedPlanIds.value.forEach(id => next.add(id))
  selectedPlanIds.value = next
}

function setPage(nextPage) {
  page.value = Math.min(Math.max(1, nextPage), totalPages.value)
}

function changePageSize(size) {
  pageSize.value = Number(size)
  page.value = 1
}

function setStatusFilter(status) {
  filterStatus.value = status
  page.value = 1
  fetchList()
}

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    const qs = params.toString()
    const res = await fetch(`/api/plans${qs ? '?' + qs : ''}`)
    if (res.ok) {
      planList.value = await res.json()
      if (page.value > totalPages.value) page.value = totalPages.value
      syncWorkflowGroup()
    }
  } catch (_) { /* ignore */ }
  loading.value = false
}

onMounted(() => {
  if (searchText.value) page.value = 1
  fetchList()
})

function syncWorkflowGroup() {
  if (!workflowGroup.value) return
  workflowGroup.value = groupedPlanList.value.find(group => group.key === workflowGroup.value.key) || null
}

async function updateStatus(pid, status) {
  const action = {
    running: 'start',
    finish: 'finish',
    cancel: 'cancel',
    wait: 'reopen',
    pending: 'reset',
  }[status] || 'reopen'
  await fetch(`/api/plans/${pid}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  }).catch(() => {})
  await fetchList()
}

async function removePlan(pid) {
  if (!confirm('确认删除这个面试环节？')) return
  await fetch(`/api/plans/${pid}`, { method: 'DELETE' })
  await fetchList()
}

async function removeGroup(group) {
  if (!confirm(`确认删除「${group.candidate_name}」的 ${group.plans.length} 个面试环节？`)) return
  batchWorking.value = true
  for (const plan of group.plans) {
    await fetch(`/api/plans/${plan.id}`, { method: 'DELETE' }).catch(() => {})
  }
  selectedPlanIds.value = new Set()
  workflowGroup.value = null
  batchWorking.value = false
  await fetchList()
}

async function updateSelectedStatus(status) {
  const targets = status === 'running'
    ? selectedPlans.value.filter(plan => plan.status === 'wait')
    : selectedPlans.value
  if (!targets.length) return
  batchWorking.value = true
  for (const plan of targets) {
    await fetch(`/api/plans/${plan.id}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: status === 'running' ? 'start' : status === 'finish' ? 'finish' : status === 'cancel' ? 'cancel' : 'reopen' }),
    }).catch(() => {})
  }
  selectedPlanIds.value = new Set()
  batchWorking.value = false
  await fetchList()
}

async function deleteSelectedPlans() {
  const targets = selectedPlans.value
  if (!targets.length) return
  if (!confirm(`确认删除选中的 ${targets.length} 个面试环节？`)) return
  batchWorking.value = true
  for (const plan of targets) {
    await fetch(`/api/plans/${plan.id}`, { method: 'DELETE' }).catch(() => {})
  }
  selectedPlanIds.value = new Set()
  workflowGroup.value = null
  batchWorking.value = false
  await fetchList()
}

async function createInterview(plan) {
  if (!['wait', 'running'].includes(plan.status)) {
    alert('当前环节还不能发起，请先确认前序面试是否完成。')
    return
  }
  if (plan.status === 'running') {
    launchPlan.value = plan
    return
  }
  try {
    const res = await fetch(`/api/plans/${plan.id}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'start' }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      alert(err.detail || '发起面试失败')
      return
    }
    const updated = await res.json()
    launchPlan.value = updated
    await fetchList()
  } catch (e) {
    alert('发起面试失败: ' + e.message)
  }
}

function openWorkflowGroup(group) {
  workflowGroup.value = group
  editingPlanId.value = null
  editForm.value = {}
}

async function refreshWorkflowGroup() {
  await fetchList()
}

function openPlanPreview(plan) {
  previewPlan.value = plan
}

function archiveQuery(plan, tab = 'records') {
  return {
    candidate: plan.candidate_name || '',
    round: plan.interview_round || '',
    tab,
  }
}

function goPlanArchive(plan, tab = 'records') {
  router.push({ path: '/interview-archive', query: archiveQuery(plan, tab) })
}

function startEditPlan(plan) {
  editingPlanId.value = plan.id
  editForm.value = {
    candidate_name: plan.candidate_name || '',
    jd_name: plan.jd_name || '',
    workflow_name: plan.workflow_name || '',
    interview_round: plan.interview_round || '',
    question_count: plan.question_count || 10,
    match_score: plan.match_score || 0,
    status: plan.status || 'wait',
    candidate_username: plan.candidate_username || '',
    candidate_password: plan.candidate_password || '',
    questions: plan.questions || '',
    scheduled_at: toDatetimeLocal(plan.scheduled_at),
    interviewer: plan.interviewer || '',
    meeting_url: plan.meeting_url || '',
    interview_result: plan.interview_result || '',
    result_score: plan.result_score || 0,
    result_note: plan.result_note || '',
  }
}

function cancelEditPlan() {
  editingPlanId.value = null
  editForm.value = {}
}

async function savePlanEdit(plan) {
  savingPlan.value = true
  try {
    const payload = {
      candidate_name: editForm.value.candidate_name,
      jd_name: editForm.value.jd_name,
      workflow_name: editForm.value.workflow_name,
      interview_round: editForm.value.interview_round,
      question_count: Number(editForm.value.question_count || 0),
      match_score: Number(editForm.value.match_score || 0),
      status: editForm.value.status,
      candidate_username: editForm.value.candidate_username,
      candidate_password: editForm.value.candidate_password,
      questions: editForm.value.questions,
      scheduled_at: editForm.value.scheduled_at,
      interviewer: editForm.value.interviewer,
      meeting_url: editForm.value.meeting_url,
      interview_result: editForm.value.interview_result,
      result_score: Number(editForm.value.result_score || 0),
      result_note: editForm.value.result_note,
    }
    const res = await fetch(`/api/plans/${plan.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      alert(err.detail || '保存失败')
      return
    }
    const updated = await res.json()
    if (payload.status === 'finish') {
      await fetch(`/api/plans/${plan.id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'finish',
          interview_result: payload.interview_result,
          result_score: payload.result_score,
          result_note: payload.result_note,
        }),
      }).catch(() => {})
    }
    cancelEditPlan()
    await fetchList()
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    savingPlan.value = false
  }
}

const statusBadge = (s) => ({
  wait: 'bg-blue-50 text-blue-600',
  pending: 'bg-gray-100 text-gray-500',
  running: 'bg-orange-50 text-orange-600',
  finish: 'bg-green-100 text-green-600',
  cancel: 'bg-gray-100 text-gray-500',
  partial: 'bg-emerald-50 text-emerald-600',
}[s] || 'bg-gray-100')

const statusLabel = (s) => ({
  wait: '待发起面试',
  pending: '待前序完成',
  running: '已发起/面试中',
  finish: '已完成面试',
  cancel: '已作废',
  partial: '部分完成',
}[s] || s)

function resetFilters() {
  searchText.value = ''
  filterStatus.value = ''
  page.value = 1
  fetchList()
}

function credentialText(data) {
  return `用户名：${data?.candidate_username || '-'}\n密码：${data?.candidate_password || '-'}`
}

async function copyCredential(data, key) {
  if (!data?.candidate_username) return
  try {
    await navigator.clipboard.writeText(credentialText(data))
    copiedCredentialKey.value = key
    window.setTimeout(() => {
      if (copiedCredentialKey.value === key) copiedCredentialKey.value = ''
    }, 1500)
  } catch (_) {
    alert(credentialText(data))
  }
}

function launchLoginUrl(plan) {
  const origin = window.location.origin
  const query = new URLSearchParams({
    redirect: '/user',
    username: plan.candidate_username || '',
    password: plan.candidate_password || '',
  }).toString()
  return `${origin}/user/login?${query}`
}

async function copyLaunchText(plan) {
  const text = [
    `候选人：${plan.candidate_name || '-'}`,
    `岗位：${plan.jd_name || '-'}`,
    `环节：${plan.interview_round || '面试'}`,
    `登录地址：${launchLoginUrl(plan)}`,
    `用户名：${plan.candidate_username || '-'}`,
    `密码：${plan.candidate_password || '-'}`,
  ].join('\n')
  try {
    await navigator.clipboard.writeText(text)
    alert('候选人登录信息已复制')
  } catch (_) {
    alert(text)
  }
}

function openCandidateLogin(plan) {
  window.open(launchLoginUrl(plan), '_blank')
}

const previewQuestions = computed(() => {
  if (!previewPlan.value?.questions) return []
  try {
    const parsed = JSON.parse(previewPlan.value.questions)
    if (!Array.isArray(parsed)) return []
    return parsed
      .map(item => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') return item.question || item.title || item.content || ''
        return ''
      })
      .filter(Boolean)
  } catch (_) {
    return []
  }
})
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-start mb-6 gap-4">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">面试计划管理</h2>
          <p class="mt-1 text-sm text-gray-500">按候选人聚合查看一面、二面、HR 面等流程进度，快速发起和推进下一轮。</p>
        </div>
        <div class="flex gap-3">
          <button
            :class="['border px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition', batchMode ? 'border-orange-300 bg-orange-50 text-orange-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50']"
            @click="toggleBatchMode"
          >
            <i class="fa fa-check-square-o"></i>{{ batchMode ? '退出批量' : '批量管理' }}
          </button>
          <button class="border border-[#1677ff] text-[#1677ff] px-4 py-2 rounded-lg hover:bg-blue-50 text-sm" @click="router.push('/interviewee')">
            <i class="fa fa-file-text-o mr-1"></i>手动新建计划
          </button>
          <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 text-sm" @click="router.push('/interviewee')">
            <i class="fa fa-magic"></i>AI生成面试计划
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <button class="rounded-2xl border border-blue-100 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md" @click="setStatusFilter('')">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-500">候选流程</span>
            <span class="h-9 w-9 rounded-xl bg-blue-50 text-[#1677ff] flex items-center justify-center"><i class="fa fa-sitemap"></i></span>
          </div>
          <div class="mt-3 text-3xl font-bold text-gray-900">{{ planStats.candidates }}</div>
          <div class="mt-1 text-xs text-gray-400">{{ planStats.stages }} 个面试环节</div>
        </button>
        <button class="rounded-2xl border border-orange-100 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md" @click="setStatusFilter('running')">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-500">面试中</span>
            <span class="h-9 w-9 rounded-xl bg-orange-50 text-orange-500 flex items-center justify-center"><i class="fa fa-comments-o"></i></span>
          </div>
          <div class="mt-3 text-3xl font-bold text-gray-900">{{ planStats.running }}</div>
          <div class="mt-1 text-xs text-gray-400">{{ planStats.waiting }} 个流程待发起</div>
        </button>
        <button class="rounded-2xl border border-amber-100 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md" @click="setStatusFilter('pending')">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-500">待前序完成</span>
            <span class="h-9 w-9 rounded-xl bg-amber-50 text-amber-500 flex items-center justify-center"><i class="fa fa-hourglass-half"></i></span>
          </div>
          <div class="mt-3 text-3xl font-bold text-gray-900">{{ planStats.pending }}</div>
          <div class="mt-1 text-xs text-gray-400">{{ planStats.partial }} 个流程部分完成</div>
        </button>
        <button class="rounded-2xl border border-green-100 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md" @click="setStatusFilter('finish')">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-500">完成率</span>
            <span class="h-9 w-9 rounded-xl bg-green-50 text-green-500 flex items-center justify-center"><i class="fa fa-check-circle-o"></i></span>
          </div>
          <div class="mt-3 text-3xl font-bold text-gray-900">{{ planStats.completionRate }}%</div>
          <div class="mt-1 text-xs text-gray-400">{{ planStats.finished }} 位候选人流程完成</div>
        </button>
      </div>

      <div v-if="batchMode" class="bg-white rounded-xl p-4 shadow-sm mb-6 border border-orange-100 flex flex-wrap items-center justify-between gap-3">
        <div class="text-sm text-gray-600">
          已选择 <span class="font-semibold text-orange-600">{{ selectedPlans.length }}</span> 个面试环节
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button class="px-3 py-2 rounded-lg border border-gray-200 text-sm hover:bg-gray-50" @click="toggleSelectAll">{{ allSelected ? '取消全选' : '全选当前页' }}</button>
          <button class="px-3 py-2 rounded-lg border border-blue-200 text-blue-600 text-sm hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedPlans.length" @click="updateSelectedStatus('running')"><i class="fa fa-play-circle mr-1"></i>批量标记已发起</button>
          <button class="px-3 py-2 rounded-lg border border-green-200 text-green-600 text-sm hover:bg-green-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedPlans.length" @click="updateSelectedStatus('finish')"><i class="fa fa-check-circle mr-1"></i>批量完成</button>
          <button class="px-3 py-2 rounded-lg border border-gray-200 text-gray-600 text-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-300" :disabled="batchWorking || !selectedPlans.length" @click="updateSelectedStatus('cancel')"><i class="fa fa-ban mr-1"></i>批量作废</button>
          <button class="px-3 py-2 rounded-lg border border-red-200 text-red-500 text-sm hover:bg-red-50 disabled:cursor-not-allowed disabled:text-gray-300 disabled:border-gray-200" :disabled="batchWorking || !selectedPlans.length" @click="deleteSelectedPlans"><i class="fa fa-trash-o mr-1"></i>批量删除</button>
        </div>
      </div>

      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center justify-between">
          <div class="flex flex-wrap gap-4 items-center">
          <div class="w-60 relative">
            <input v-model="searchText" type="text" placeholder="候选人姓名 / 岗位名称" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="page = 1; fetchList()">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterStatus" class="border rounded-lg px-3 py-2 min-w-[160px]" @change="page = 1; fetchList()">
            <option value="">全部流程状态</option>
            <option value="wait">待发起面试</option>
            <option value="pending">待前序完成</option>
            <option value="running">已发起/面试中</option>
            <option value="finish">已完成面试</option>
            <option value="cancel">已作废</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置筛选</button>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <button
              v-for="item in statusQuickFilters"
              :key="item.value || 'all'"
              :class="['px-3 py-2 rounded-lg border text-sm transition', filterStatus === item.value ? 'border-[#1677ff] bg-blue-50 text-[#1677ff]' : 'border-gray-200 text-gray-600 hover:bg-gray-50']"
              @click="setStatusFilter(item.value)"
            >
              <i :class="['fa mr-1', item.icon]"></i>{{ item.label }}
            </button>
          </div>
        </div>
      </div>

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
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">目标岗位(JD)</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">面试流程</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">面试者账号</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">进度</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">安排</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">题目数</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">创建时间</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">状态</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-56">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(group, i) in pagedPlanGroups" :key="group.key" class="hover:bg-gray-50">
              <td v-if="batchMode" class="px-4 py-3 text-center">
                <input type="checkbox" :checked="isGroupSelected(group)" @change="setSelectedGroup(group, $event.target.checked)">
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ (page - 1) * pageSize + i + 1 }}</td>
              <td class="px-4 py-3">
                <div class="font-medium text-sm text-gray-900">{{ group.candidate_name }}</div>
                <div class="text-xs text-gray-400">{{ group.plans.length }} 个面试环节</div>
              </td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ group.jd_name }}</td>
              <td class="px-4 py-3 text-sm">
                <div class="font-medium text-gray-800">{{ group.workflow_name }}</div>
                <div class="flex flex-wrap gap-1 mt-1">
                  <span
                    v-for="plan in group.plans"
                    :key="plan.id"
                    :class="['px-2 py-0.5 rounded border text-xs', stagePillClass(plan.status)]"
                  >{{ plan.interview_round || '面试' }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-xs text-gray-600">
                <button
                  v-if="group.candidate_username"
                  class="font-mono leading-5 text-left rounded-lg px-2 py-1 -mx-2 hover:bg-blue-50 transition"
                  title="点击复制账号和密码"
                  @click="copyCredential(group, `group:${group.key}`)"
                >
                  <div class="text-gray-800">{{ group.candidate_username }}</div>
                  <div class="text-gray-400">{{ group.candidate_password }}</div>
                  <div class="text-[11px] text-[#1677ff] mt-1">
                    {{ copiedCredentialKey === `group:${group.key}` ? '已复制' : '点击复制账号密码' }}
                  </div>
                </button>
                <span v-else>-</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-700">
                <div class="font-medium text-gray-900">{{ currentStageLabel(group) }}</div>
                <div class="mt-0.5 text-xs text-gray-400">{{ nextActionText(group) }}</div>
                <div class="w-28 h-1.5 rounded-full bg-gray-100 mt-2 overflow-hidden">
                  <div class="h-full bg-[#1677ff]" :style="{ width: `${progressPercent(group)}%` }"></div>
                </div>
                <div class="mt-1 text-xs text-gray-400">{{ group.finished_count }}/{{ group.stage_count }} 已完成</div>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                <div>{{ currentPlanMeta(group) }}</div>
                <a
                  v-if="group.current_plan?.meeting_url"
                  :href="group.current_plan.meeting_url"
                  target="_blank"
                  class="mt-1 inline-flex text-xs text-[#1677ff] hover:underline"
                >会议链接</a>
              </td>
              <td class="px-4 py-3 text-sm">{{ group.question_count }} 道</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ group.created_at?.slice(0, 16) || '-' }}</td>
              <td class="px-4 py-3"><span :class="['px-2 py-1 text-xs rounded', statusBadge(group.status)]">{{ statusLabel(group.status) }}</span></td>
              <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center gap-2">
                  <button class="h-8 px-3 rounded-lg border border-blue-100 text-[#1677ff] text-sm hover:bg-blue-50" @click="openWorkflowGroup(group)">查看</button>
                  <button v-if="group.current_plan && group.current_plan.status === 'wait'" class="h-8 px-3 rounded-lg border border-green-100 bg-green-50 text-green-700 text-sm hover:bg-green-100" @click="createInterview(group.current_plan)">发起</button>
                  <button v-else-if="group.current_plan && group.current_plan.status === 'running'" class="h-8 px-3 rounded-lg border border-blue-100 bg-blue-50 text-blue-700 text-sm hover:bg-blue-100" @click="createInterview(group.current_plan)">入口</button>
                  <button class="h-8 w-8 rounded-lg text-red-400 hover:bg-red-50" title="删除流程" @click="removeGroup(group)"><i class="fa fa-trash-o"></i></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !groupedPlanList.length" class="text-center py-14 text-gray-400">
          <div class="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-[#1677ff]">
            <i class="fa fa-calendar-check-o text-2xl"></i>
          </div>
          <div class="text-sm font-medium text-gray-700">暂无匹配的面试计划</div>
          <div class="mt-1 text-xs text-gray-400">可以从简历管理中为候选人创建流程，或调整当前筛选条件。</div>
          <button class="mt-4 rounded-lg bg-[#1677ff] px-4 py-2 text-sm text-white hover:bg-blue-600" @click="router.push('/resume-manager')">去简历管理</button>
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 mt-4 text-sm text-gray-500">
        <div class="flex items-center gap-3">
          <span>共 {{ groupedPlanList.length }} 位候选人 / {{ planList.length }} 个环节</span>
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

    <div v-if="workflowGroup" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="workflowGroup = null">
      <div class="bg-white rounded-xl w-full max-w-6xl max-h-[90vh] shadow-xl overflow-hidden flex flex-col">
        <div class="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold text-gray-900">{{ workflowGroup.candidate_name }} · {{ workflowGroup.workflow_name }}</h3>
            <p class="text-sm text-gray-500 mt-1">{{ workflowGroup.jd_name }} · {{ workflowGroup.finished_count }}/{{ workflowGroup.stage_count }} 已完成</p>
          </div>
          <div class="flex items-center gap-2">
            <button class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50" @click="refreshWorkflowGroup">刷新流程</button>
            <button class="w-8 h-8 rounded-lg text-gray-400 hover:bg-gray-100" @click="workflowGroup = null"><i class="fa fa-times"></i></button>
          </div>
        </div>

        <div class="px-6 py-4 bg-gray-50 border-b flex flex-wrap items-center gap-6 text-sm">
          <div>
            <div class="text-gray-400">登录地址</div>
            <div class="font-medium text-[#1677ff]">/user/login</div>
          </div>
          <button
            class="text-left rounded-lg px-3 py-2 -mx-3 hover:bg-blue-50 transition"
            title="点击复制账号和密码"
            @click="copyCredential(workflowGroup, `workflow:${workflowGroup.key}`)"
          >
            <div class="text-gray-400">用户名</div>
            <div class="font-mono text-gray-800 select-all">{{ workflowGroup.candidate_username || '-' }}</div>
          </button>
          <button
            class="text-left rounded-lg px-3 py-2 -mx-3 hover:bg-blue-50 transition"
            title="点击复制账号和密码"
            @click="copyCredential(workflowGroup, `workflow:${workflowGroup.key}`)"
          >
            <div class="text-gray-400">密码</div>
            <div class="font-mono text-gray-800 select-all">{{ workflowGroup.candidate_password || '-' }}</div>
          </button>
          <div v-if="copiedCredentialKey === `workflow:${workflowGroup.key}`" class="text-[#1677ff]">账号密码已复制</div>
        </div>

        <div class="overflow-auto p-6 space-y-4">
          <div v-for="plan in workflowGroup.plans" :key="plan.id" class="border border-gray-200 rounded-xl overflow-hidden">
            <div class="px-4 py-3 bg-gray-50 flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center text-sm font-semibold">{{ plan.stage_order || 1 }}</span>
                <div>
                  <div class="font-semibold text-gray-900">{{ plan.interview_round || '面试环节' }}</div>
                  <div class="text-xs text-gray-400">计划 ID：{{ plan.id }} · {{ plan.question_count }} 道题 · {{ formatSchedule(plan.scheduled_at) }}</div>
                </div>
                <span :class="['px-2 py-1 text-xs rounded', statusBadge(plan.status)]">{{ statusLabel(plan.status) }}</span>
                <span :class="['px-2 py-1 text-xs rounded border', resultBadgeClass(plan.interview_result)]">{{ resultLabel(plan) }}</span>
              </div>
              <div class="flex items-center gap-2">
                <button class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm hover:bg-white" @click="openPlanPreview(plan)">预览</button>
                <button class="px-3 py-1.5 rounded-lg border border-indigo-200 text-indigo-600 text-sm hover:bg-indigo-50" @click="goPlanArchive(plan, 'records')">档案</button>
                <button class="px-3 py-1.5 rounded-lg border border-[#1677ff] text-[#1677ff] text-sm hover:bg-blue-50" @click="startEditPlan(plan)">{{ editingPlanId === plan.id ? '正在编辑' : '编辑' }}</button>
                <button v-if="plan.status === 'wait'" class="px-3 py-1.5 rounded-lg border border-green-200 text-green-600 text-sm hover:bg-green-50" @click="createInterview(plan)">发起</button>
                <button v-else-if="plan.status === 'running'" class="px-3 py-1.5 rounded-lg border border-blue-200 text-blue-600 text-sm hover:bg-blue-50" @click="createInterview(plan)">查看入口</button>
                <span v-else-if="plan.status === 'pending'" class="px-3 py-1.5 rounded-lg border border-gray-200 text-gray-400 text-sm">等待上一轮完成</span>
                <button v-if="plan.status === 'cancel'" class="px-3 py-1.5 rounded-lg border border-blue-200 text-blue-600 text-sm hover:bg-blue-50" @click="updateStatus(plan.id, 'wait')">重新发起</button>
                <button class="px-3 py-1.5 rounded-lg border border-red-200 text-red-500 text-sm hover:bg-red-50" @click="removePlan(plan.id)">删除</button>
              </div>
            </div>

            <div v-if="editingPlanId === plan.id" class="p-4 space-y-5">
              <div>
                <div class="mb-3 text-sm font-semibold text-gray-900">基础信息</div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">候选人</span>
                <input v-model="editForm.candidate_name" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
              </label>
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">目标岗位</span>
                <input v-model="editForm.jd_name" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
              </label>
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">流程名称</span>
                <input v-model="editForm.workflow_name" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
              </label>
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">面试轮次</span>
                <input v-model="editForm.interview_round" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="一面 / 二面 / HR 面">
              </label>
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">题目数</span>
                <input v-model="editForm.question_count" type="number" min="1" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
              </label>
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">匹配度</span>
                <input v-model="editForm.match_score" type="number" min="0" max="100" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
              </label>
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">状态</span>
                <select v-model="editForm.status" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
                  <option value="wait">待发起面试</option>
                  <option value="pending">待前序完成</option>
                  <option value="running">已发起/面试中</option>
                  <option value="finish">已完成面试</option>
                  <option value="cancel">已作废</option>
                </select>
              </label>
                </div>
              </div>

              <div>
                <div class="mb-3 text-sm font-semibold text-gray-900">预约安排</div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <label class="text-sm">
                    <span class="block text-gray-500 mb-1">预约时间</span>
                    <input v-model="editForm.scheduled_at" type="datetime-local" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
                  </label>
                  <label class="text-sm">
                    <span class="block text-gray-500 mb-1">面试官</span>
                    <input v-model="editForm.interviewer" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="如：王工 / HR 李">
                  </label>
                  <label class="text-sm">
                    <span class="block text-gray-500 mb-1">会议链接</span>
                    <input v-model="editForm.meeting_url" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="https://...">
                  </label>
                </div>
              </div>

              <div>
                <div class="mb-3 text-sm font-semibold text-gray-900">面试结论</div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <label class="text-sm">
                    <span class="block text-gray-500 mb-1">结论</span>
                    <select v-model="editForm.interview_result" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
                      <option value="">未录入</option>
                      <option value="pass">通过</option>
                      <option value="pending">待定</option>
                      <option value="reject">不通过</option>
                    </select>
                  </label>
                  <label class="text-sm">
                    <span class="block text-gray-500 mb-1">评分</span>
                    <input v-model="editForm.result_score" type="number" min="0" max="100" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
                  </label>
                  <label class="text-sm md:col-span-1">
                    <span class="block text-gray-500 mb-1">备注</span>
                    <input v-model="editForm.result_note" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="面试结论摘要">
                  </label>
                </div>
              </div>

              <div>
                <div class="mb-3 text-sm font-semibold text-gray-900">账号与题目</div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">候选人用户名</span>
                <input v-model="editForm.candidate_username" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
              </label>
              <label class="text-sm">
                <span class="block text-gray-500 mb-1">候选人密码</span>
                <input v-model="editForm.candidate_password" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
              </label>
              <label class="text-sm md:col-span-2">
                <span class="block text-gray-500 mb-1">题目 JSON</span>
                <textarea v-model="editForm.questions" rows="4" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder='["请做一下自我介绍"]'></textarea>
              </label>
                </div>
              </div>
              <div class="flex justify-end gap-2">
                <button class="px-4 py-2 rounded-lg border border-indigo-200 text-indigo-600 hover:bg-indigo-50" @click="goPlanArchive(plan, 'records')">查看记录</button>
                <button class="px-4 py-2 rounded-lg border border-violet-200 text-violet-600 hover:bg-violet-50" @click="goPlanArchive(plan, 'reports')">查看报告</button>
                <button class="px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50" @click="cancelEditPlan">取消</button>
                <button class="px-4 py-2 rounded-lg bg-[#1677ff] text-white hover:bg-blue-600 disabled:opacity-50" :disabled="savingPlan" @click="savePlanEdit(plan)">
                  <i v-if="savingPlan" class="fa fa-spinner fa-spin mr-1"></i>保存
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="launchPlan" class="fixed inset-0 bg-black/40 z-[60] flex items-center justify-center p-4" @click.self="launchPlan = null">
      <div class="bg-white rounded-xl w-full max-w-xl shadow-xl overflow-hidden">
        <div class="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold text-gray-900">{{ launchPlan.status === 'running' ? '面试入口' : '发起面试' }}</h3>
            <p class="text-sm text-gray-500 mt-1">{{ launchPlan.candidate_name }} · {{ launchPlan.interview_round || '面试' }}</p>
          </div>
          <button class="w-8 h-8 rounded-lg text-gray-400 hover:bg-gray-100" @click="launchPlan = null"><i class="fa fa-times"></i></button>
        </div>

        <div class="p-6 space-y-4 text-sm">
          <div class="rounded-xl border border-blue-100 bg-blue-50 p-4 text-blue-700">
            当前环节已标记为“已发起/面试中”。把下面这组地址和账号发给候选人，对方登录后会自动进入当前可参加的面试环节。
          </div>

          <div class="grid grid-cols-1 gap-3">
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">登录地址</div>
              <div class="text-[#1677ff] break-all">{{ launchLoginUrl(launchPlan) }}</div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="rounded-lg border border-gray-200 p-4">
                <div class="text-gray-400 mb-1">用户名</div>
                <div class="font-mono text-gray-900 select-all">{{ launchPlan.candidate_username || '-' }}</div>
              </div>
              <div class="rounded-lg border border-gray-200 p-4">
                <div class="text-gray-400 mb-1">密码</div>
                <div class="font-mono text-gray-900 select-all">{{ launchPlan.candidate_password || '-' }}</div>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button class="px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50" @click="copyLaunchText(launchPlan)">复制信息</button>
            <button class="px-4 py-2 rounded-lg bg-[#1677ff] text-white hover:bg-blue-600" @click="openCandidateLogin(launchPlan)">打开候选人登录页</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="previewPlan" class="fixed inset-0 bg-black/40 z-[70] flex items-center justify-center p-4" @click.self="previewPlan = null">
      <div class="bg-white rounded-xl w-full max-w-3xl max-h-[88vh] shadow-xl overflow-hidden flex flex-col">
        <div class="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold text-gray-900">面试计划预览</h3>
            <p class="text-sm text-gray-500 mt-1">{{ previewPlan.candidate_name }} · {{ previewPlan.interview_round || '面试环节' }}</p>
          </div>
          <div class="flex items-center gap-2">
            <button class="h-8 px-3 rounded-lg border border-indigo-200 text-indigo-600 text-xs hover:bg-indigo-50" @click="goPlanArchive(previewPlan, 'records')">记录</button>
            <button class="h-8 px-3 rounded-lg border border-violet-200 text-violet-600 text-xs hover:bg-violet-50" @click="goPlanArchive(previewPlan, 'reports')">报告</button>
            <button class="w-8 h-8 rounded-lg text-gray-400 hover:bg-gray-100" @click="previewPlan = null"><i class="fa fa-times"></i></button>
          </div>
        </div>

        <div class="overflow-auto p-6 space-y-5">
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">候选人</div>
              <div class="font-medium text-gray-900">{{ previewPlan.candidate_name || '-' }}</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">目标岗位</div>
              <div class="font-medium text-gray-900">{{ previewPlan.jd_name || '-' }}</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">流程名称</div>
              <div class="font-medium text-gray-900">{{ previewPlan.workflow_name || '单轮面试' }}</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">状态</div>
              <span :class="['px-2 py-1 text-xs rounded', statusBadge(previewPlan.status)]">{{ statusLabel(previewPlan.status) }}</span>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">轮次</div>
              <div class="font-medium text-gray-900">{{ previewPlan.interview_round || '-' }}</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">题目数</div>
              <div class="font-medium text-gray-900">{{ previewPlan.question_count || 0 }} 道</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">预约时间</div>
              <div class="font-medium text-gray-900">{{ formatSchedule(previewPlan.scheduled_at) }}</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">面试官</div>
              <div class="font-medium text-gray-900">{{ previewPlan.interviewer || '未分配' }}</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">会议链接</div>
              <a
                v-if="previewPlan.meeting_url"
                :href="previewPlan.meeting_url"
                target="_blank"
                class="font-medium text-[#1677ff] break-all hover:underline"
              >{{ previewPlan.meeting_url }}</a>
              <div v-else class="font-medium text-gray-900">未填写</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">面试结论</div>
              <span :class="['px-2 py-1 text-xs rounded border', resultBadgeClass(previewPlan.interview_result)]">{{ resultLabel(previewPlan) }}</span>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">面试评分</div>
              <div class="font-medium text-gray-900">{{ previewPlan.result_score || 0 }} 分</div>
            </div>
            <div class="rounded-lg border border-gray-200 p-4">
              <div class="text-gray-400 mb-1">结果备注</div>
              <div class="font-medium text-gray-900 whitespace-pre-line">{{ previewPlan.result_note || '未填写' }}</div>
            </div>
          </div>

          <div class="rounded-xl border border-gray-200 overflow-hidden">
            <div class="px-4 py-3 bg-gray-50 border-b text-sm font-semibold text-gray-800">预设题目</div>
            <div v-if="previewQuestions.length" class="p-4 space-y-3">
              <div v-for="(question, index) in previewQuestions" :key="index" class="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                <span class="text-[#1677ff] font-medium mr-2">Q{{ index + 1 }}</span>{{ question }}
              </div>
            </div>
            <div v-else class="p-6 text-sm text-gray-400">当前计划还没有预设题目，面试开始时会按默认逻辑生成或使用流程配置。</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
