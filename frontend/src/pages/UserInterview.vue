<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CandidateNavbar from '../components/CandidateNavbar.vue'

const router = useRouter()
const route = useRoute()
const loading = ref(true)
const jobLoading = ref(false)
const plans = ref([])
const recommendedJobs = ref([])
const error = ref('')
const expandedWorkflows = ref(new Set())
const selectedWorkflowKey = ref('')
const activeTab = ref('social')
const username = ref('')
const nickname = ref('')
const phone = ref('')
const email = ref('')
const viewingResume = ref(null)
const resumePreviewLoading = ref(false)
const resumePreviewSrc = ref('')
const showOriginalResume = ref(false)
const favoriteJobs = ref([])
const favoriteRefreshing = ref(false)
const resumeUploading = ref(false)
const pendingApplyJob = ref(null)
const uploadedResumeFile = ref('')
const resumeParseStatus = ref('')
const applicationQuota = ref({
  limit_per_type: 3,
  window_months: 6,
  buckets: {
    社招: { limit: 3, used: 0, remaining: 3, available_at: '' },
    校招: { limit: 3, used: 0, remaining: 3, available_at: '' },
    实习生: { limit: 3, used: 0, remaining: 3, available_at: '' },
  },
})
const quotaTypes = [
  { key: '社招', label: '社招' },
  { key: '校招', label: '校招' },
  { key: '实习生', label: '实习' },
]

function quotaRemaining(key) {
  return Math.max(0, Number(applicationQuota.value.buckets?.[key]?.remaining ?? 3))
}

function showToast(message, type = 'info', duration = 4200) {
  window.appNotify?.(message, type, duration)
}

const hasResume = computed(() => {
  return Boolean(resumeFileName.value && resumeFileName.value !== '暂未上传简历')
})

const resumeParseLabel = computed(() => ({
  success: '已解析',
  fail: '解析失败',
  wait: '未解析',
}[resumeParseStatus.value] || '未解析'))

const resumeParseBadgeClass = computed(() => ({
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  fail: 'border-rose-200 bg-rose-50 text-rose-600',
  wait: 'border-amber-200 bg-amber-50 text-amber-700',
}[resumeParseStatus.value] || 'border-amber-200 bg-amber-50 text-amber-700'))

const tabs = [
  { key: 'social', label: '社会招聘' },
  { key: 'campus', label: '校园招聘' },
  { key: 'internship', label: '实习生招聘' },
]

function recruitmentTypeForTab(tabKey) {
  return {
    social: '社招',
    campus: '校招',
    internship: '实习生',
  }[tabKey] || '社招'
}

function tabApplicationCount(tabKey) {
  const recruitmentType = recruitmentTypeForTab(tabKey)
  return currentWorkflowGroups.value.filter(group => group.recruitment_type === recruitmentType).length
}

function isScreeningPlaceholder(plan) {
  return Number(plan?.stage_order) === 0 || (
    Number(plan?.id) < 0 &&
    String(plan?.interview_round || '').trim() === '简历筛选'
  )
}

const activeQuotaItem = computed(() => {
  const quotaKey = {
    social: '社招',
    campus: '校招',
    internship: '实习生',
  }[activeTab.value] || '社招'
  return quotaTypes.find(item => item.key === quotaKey) || quotaTypes[0]
})

const activeQuotaText = computed(() => {
  const item = activeQuotaItem.value
  const bucket = applicationQuota.value.buckets?.[item.key] || {}
  const remaining = quotaRemaining(item.key)
  const limit = Math.max(0, Number(bucket.limit ?? applicationQuota.value.limit_per_type ?? 3))
  return `${item.label} · 还可投 ${remaining}/${limit}`
})

const workflowGroups = computed(() => {
  const map = new Map()
  plans.value.forEach(plan => {
    const key = workflowKey(plan)
    if (!map.has(key)) {
      map.set(key, {
        key,
        workflow_id: plan.workflow_id || '',
        workflow_name: plan.workflow_name || '我的面试流程',
        application_id: plan.application_id || null,
        application_status: plan.application_status || '',
        application_current_stage: plan.application_current_stage || '',
        screening_status: plan.screening_status || '',
        application_created_at: plan.application_created_at || '',
        offer_status: plan.offer_status || '',
        offer_updated_at: plan.offer_updated_at || '',
        match_score: Number(plan.match_score || 0),
        candidate_name: plan.candidate_name || nickname.value || username.value || '候选人',
        jd_name: plan.jd_name || '目标岗位',
        recruitment_type: normalizeRecruitmentType(plan.recruitment_type),
        location: plan.location || '',
        resume_filename: plan.resume_filename || '',
        plans: [],
      })
    }
    const group = map.get(key)
    group.plans.push(plan)
    if (!group.resume_filename && plan.resume_filename) group.resume_filename = plan.resume_filename
    if (!group.application_id && plan.application_id) group.application_id = plan.application_id
    if (!group.application_status && plan.application_status) group.application_status = plan.application_status
    if (!group.application_current_stage && plan.application_current_stage) group.application_current_stage = plan.application_current_stage
    if (!group.screening_status && plan.screening_status) group.screening_status = plan.screening_status
    if (!group.application_created_at && plan.application_created_at) group.application_created_at = plan.application_created_at
    if (!group.offer_status && plan.offer_status) group.offer_status = plan.offer_status
    if (!group.offer_updated_at && plan.offer_updated_at) group.offer_updated_at = plan.offer_updated_at
    if (!group.match_score && Number(plan.match_score) > 0) group.match_score = Number(plan.match_score)
    if (!group.location && plan.location) group.location = plan.location
  })
  return Array.from(map.values()).map(group => {
    // application 尚未创建正式面试流程时，接口会返回一条“简历筛选”占位项。
    // 简历筛选已经由 application 固定节点展示，不能再次当作面试计划绘制。
    const sortedPlans = group.plans
      .filter(plan => !isScreeningPlaceholder(plan))
      .sort((a, b) => Number(a.stage_order || 1) - Number(b.stage_order || 1))
    const current = group.application_status === 'active' && group.application_current_stage === 'interview'
      ? sortedPlans.find(p => p.interview_ready === true) || null
      : null
    const finished = sortedPlans.filter(p => p.status === 'finish').length
    const last = sortedPlans[sortedPlans.length - 1] || null
    return {
      ...group,
      plans: sortedPlans,
      current_plan: current,
      finished_count: finished,
      progress_percent: sortedPlans.length ? Math.round((finished / sortedPlans.length) * 100) : 0,
      latest_status: current?.status || last?.status || 'pending',
    }
  })
})

// 用户主动取消的投递隐藏；后台初筛不通过的投递继续保留并展示结果。
const currentWorkflowGroups = computed(() => {
  const visible = workflowGroups.value.filter((group) => {
    if (['withdrawn', 'cancel'].includes(group.application_status)) return false
    if (['rejected', 'reject', 'hired'].includes(group.application_status)) return true
    return !group.plans.length || !group.plans.every(plan => plan.status === 'cancel')
  })
  const byApplication = new Map()
  visible.forEach((group) => {
    const key = group.application_id ? `application:${group.application_id}` : group.key
    const previous = byApplication.get(key)
    const shouldReplace = previous && String(previous.workflow_id || '').startsWith('apply_')
      && !String(group.workflow_id || '').startsWith('apply_')
    if (!previous || shouldReplace) byApplication.set(key, group)
  })
  return Array.from(byApplication.values())
})

const filteredWorkflowGroups = computed(() => {
  const recruitmentType = {
    social: '社招',
    campus: '校招',
    internship: '实习生',
  }[activeTab.value] || '社招'
  return currentWorkflowGroups.value.filter(group => group.recruitment_type === recruitmentType)
})

function isWorkflowOngoing(group) {
  return !['rejected', 'withdrawn', 'cancel', 'hired', 'closed'].includes(group.application_status)
}

const operableWorkflowGroups = computed(() => currentWorkflowGroups.value.filter(isWorkflowOngoing))
const activeGroup = computed(() => {
  const selected = operableWorkflowGroups.value.find(group => group.key === selectedWorkflowKey.value)
  return selected || operableWorkflowGroups.value.find(group => group.current_plan) || operableWorkflowGroups.value[0] || null
})
const currentPlan = computed(() => activeGroup.value?.current_plan || null)
const applicationCount = computed(() => currentWorkflowGroups.value.length)
const closedWorkflowCount = computed(() => currentWorkflowGroups.value.filter(group => {
  return ['rejected', 'hired', 'closed'].includes(group.application_status)
}).length)
const activeInterviewCount = computed(() => plans.value.filter(plan => ['wait', 'running'].includes(plan.status)).length)
const displayName = computed(() => nickname.value || activeGroup.value?.candidate_name || username.value || '候选人')
const resumeFileName = computed(() => (
  uploadedResumeFile.value ||
  activeGroup.value?.resume_filename ||
  activeGroup.value?.plans.find(plan => plan.resume_filename)?.resume_filename ||
  currentWorkflowGroups.value[0]?.resume_filename ||
  '暂未上传简历'
))
const currentActionText = computed(() => {
  if (!currentPlan.value) return '等待通知'
  return currentPlan.value.status === 'running' ? '继续本轮面试' : '进入本轮面试'
})
const nextStepText = computed(() => {
  if (currentPlan.value) return currentPlan.value.interview_round || '面试'
  if (activeGroup.value?.application_current_stage === 'offer') return 'Offer'
  if (activeGroup.value?.application_current_stage === 'screening') return '简历筛选'
  return '等待招聘方开启下一轮'
})

watch(operableWorkflowGroups, (groups) => {
  if (!groups.some(group => group.key === selectedWorkflowKey.value)) {
    selectedWorkflowKey.value = (groups.find(group => group.current_plan) || groups[0])?.key || ''
  }
}, { immediate: true })

onMounted(async () => {
  readUser()
  await loadPlans()
  const applyJobId = route.query.apply_job
  if (applyJobId) {
    if (hasResume.value) {
      // 有简历，直接投递（携带简历文件名）
      const resumeFile = plans.value.find(p => p.resume_filename)?.resume_filename || ''
      await applyForJob(Number(applyJobId), resumeFile)
    } else {
      // 无简历，先提示上传
      pendingApplyJob.value = Number(applyJobId)
    }
    router.replace({ path: '/user', query: {} })
  }
  loadRecommendedJobs()
  loadFavoriteJobs()
})

async function loadFavoriteJobs(withAnimation = false) {
  if (favoriteRefreshing.value) return
  const startedAt = Date.now()
  if (withAnimation) favoriteRefreshing.value = true
  try {
    try { localStorage.removeItem('favorite_jobs') } catch (_) {}
    const res = await fetch('/api/jds/favorites', { cache: 'no-store' })
    favoriteJobs.value = res.ok ? await res.json() : []
  } catch (_) { favoriteJobs.value = [] }
  finally {
    if (withAnimation) {
      const remaining = Math.max(0, 520 - (Date.now() - startedAt))
      if (remaining) await new Promise(resolve => window.setTimeout(resolve, remaining))
      favoriteRefreshing.value = false
    }
  }
}

watch(activeTab, loadRecommendedJobs)

const avatar = ref('')

function readUser() {
  try {
    username.value = localStorage.getItem('username') || ''
    nickname.value = localStorage.getItem('nickname') || ''
    phone.value = localStorage.getItem('phone') || ''
    email.value = localStorage.getItem('email') || ''
    avatar.value = localStorage.getItem('avatar') || ''
  } catch (_) {
    username.value = ''
    nickname.value = ''
    phone.value = ''
    email.value = ''
    avatar.value = ''
  }
}

async function uploadAvatar(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const fd = new FormData(); fd.append('file', file)
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/auth/candidate-avatar', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd })
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || '上传失败')
    const data = await res.json()
    avatar.value = data.avatar_url
    localStorage.setItem('avatar', data.avatar_url)
  } catch (e) { showToast(e.message, 'error') }
  e.target.value = ''
}

async function loadPlans(silent = false) {
  if (!silent) loading.value = true
  error.value = ''
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/plans/my', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: 'no-store',
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '获取面试计划失败')
    }
    plans.value = await res.json()
    await loadApplicationQuota()
    await loadMyResume()
    ensureDefaultExpanded()
    // 从简历数据中补全电话/邮箱（如果 localStorage 没有）
    syncProfileFromResume()
  } catch (e) {
    error.value = e.message
  } finally {
    if (!silent) loading.value = false
  }
}

async function loadApplicationQuota() {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/plans/my/application-quota', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: 'no-store',
    })
    if (res.ok) applicationQuota.value = await res.json()
  } catch (_) {}
}

async function loadMyResume() {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/plans/my-resume', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: 'no-store',
    })
    if (res.ok) {
      const resume = await res.json()
      uploadedResumeFile.value = resume.file_path || ''
      resumeParseStatus.value = resume.parse_status || 'wait'
    } else if (res.status === 404) {
      uploadedResumeFile.value = ''
      resumeParseStatus.value = ''
    }
  } catch (_) {
    // 保留当前页面中刚上传成功的文件，避免短暂网络错误导致卡片消失
  }
}

async function applyForJob(jobId, resumeFile = '') {
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams()
    if (resumeFile) params.set('resume_filename', resumeFile)
    const qs = params.toString()
    const res = await fetch(`/api/plans/apply/${jobId}${qs ? '?' + qs : ''}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      const message = err.detail || '投递失败，请稍后重试'
      console.error('投递失败:', message)
      showToast(message, res.status === 429 ? 'warning' : 'error', 5000)
      return false
    }
    const data = await res.json()
    const appliedType = normalizeRecruitmentType(data.application?.recruitment_type)
    activeTab.value = {
      社招: 'social',
      校招: 'campus',
      实习生: 'internship',
    }[appliedType] || activeTab.value
    // 投递接口已经创建了 application 和 plan；成功后立即重新拉取，
    // 避免页面仍使用进入个人中心时取得的旧投递列表。
    await loadPlans()
    console.log('投递结果:', data.message)
    showToast(data.message || '投递成功', 'success')
    return true
  } catch (e) {
    console.error('投递异常:', e)
    showToast(e.message || '投递失败，请稍后重试', 'error')
    return false
  }
}

async function uploadResume(e) {
  const file = e.target.files?.[0]
  if (!file) return
  resumeUploading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/plans/my-resume/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    })
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || '上传失败')
    const resume = await res.json()
    uploadedResumeFile.value = resume.file_path || ''
    resumeParseStatus.value = resume.parse_status || 'wait'
    // 刷新计划和候选人自己的简历
    await loadPlans()
    // 如果有待投递的岗位，现在投递（携带简历文件名）
    if (pendingApplyJob.value) {
      const ok = await applyForJob(pendingApplyJob.value, uploadedResumeFile.value)
      if (ok) {
        pendingApplyJob.value = null
      }
    }
  } catch (err) {
    showToast(err.message || '简历上传失败，请重试', 'error')
  } finally {
    resumeUploading.value = false
    e.target.value = ''
  }
}

async function syncProfileFromResume() {
  if (phone.value && email.value) return  // 已经有了，跳过
  const resumeFile = resumeFileName.value === '暂未上传简历' ? '' : resumeFileName.value
  if (!resumeFile) return
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/plans/my-resume?filename=${encodeURIComponent(resumeFile)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) return
    const resume = await res.json()
    const structured = JSON.parse(resume.structured_data || '{}')
    const basic = structured['基础信息'] || {}
    if (!phone.value && basic['电话']) { phone.value = basic['电话']; try { localStorage.setItem('phone', basic['电话']) } catch (_) {} }
    if (!email.value && basic['邮箱']) { email.value = basic['邮箱']; try { localStorage.setItem('email', basic['邮箱']) } catch (_) {} }
  } catch (_) {}
}

async function loadRecommendedJobs() {
  jobLoading.value = true
  try {
    const recruitmentType = {
      social: '社招',
      campus: '校招',
      internship: '实习生',
    }[activeTab.value] || '社招'
    const params = new URLSearchParams({
      page: '1',
      page_size: '5',
      recruitment_type: recruitmentType,
    })
    const res = await fetch(`/api/jds/public?${params.toString()}`)
    const data = await res.json().catch(() => ({}))
    recommendedJobs.value = res.ok && Array.isArray(data.items) ? data.items.slice(0, 3) : []
  } catch (_) {
    recommendedJobs.value = []
  } finally {
    jobLoading.value = false
  }
}

function workflowKey(plan) {
  return plan.workflow_id || `single:${plan.candidate_username || ''}:${plan.jd_name || ''}:${plan.id || ''}`
}

function normalizeRecruitmentType(value) {
  const text = String(value || '').trim()
  if (text.includes('实习')) return '实习生'
  if (text.includes('校')) return '校招'
  return '社招'
}

function ensureDefaultExpanded() {
  // Keep application cards compact on entry; the full interview timeline is opt-in.
  expandedWorkflows.value = new Set()
}

function isExpanded(group) {
  return expandedWorkflows.value.has(group.key)
}

function selectWorkflow(group) {
  if (isWorkflowOngoing(group)) selectedWorkflowKey.value = group.key
}

function selectAndToggleWorkflow(group) {
  selectWorkflow(group)
  toggleWorkflow(group)
}

function toggleWorkflow(group) {
  const next = new Set(expandedWorkflows.value)
  if (next.has(group.key)) next.delete(group.key)
  else next.add(group.key)
  expandedWorkflows.value = next
}

function enterInterview(plan = currentPlan.value) {
  if (!canEnterInterview(plan)) {
    showToast(plan?.interview_block_reason || '当前面试环节尚未开放', 'warning')
    return
  }
  router.push({ path: '/chat', query: { plan_id: plan.id } })
}

async function viewResume() {
  if (!resumeFileName.value || resumeFileName.value === '暂未上传简历') return
  router.push({ path: '/resume-view', query: { filename: resumeFileName.value } })
  return
  /* legacy inline preview kept below for compatibility */
  resumePreviewLoading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/plans/my-resume?filename=${encodeURIComponent(resumeFileName.value)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('暂未找到绑定的简历')
    viewingResume.value = await res.json()
    showOriginalResume.value = false
    const fileRes = await fetch(`/api/plans/my-resume/file?filename=${encodeURIComponent(viewingResume.value.file_path || resumeFileName.value)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (fileRes.ok) {
      if (resumePreviewSrc.value) URL.revokeObjectURL(resumePreviewSrc.value)
      resumePreviewSrc.value = URL.createObjectURL(await fileRes.blob())
    }
  } catch (e) {
    showToast(e.message || '简历暂时无法查看', 'error')
  } finally {
    resumePreviewLoading.value = false
  }
}

function closeResumePreview() {
  viewingResume.value = null
  showOriginalResume.value = false
  if (resumePreviewSrc.value) {
    URL.revokeObjectURL(resumePreviewSrc.value)
    resumePreviewSrc.value = ''
  }
}

function parsedResumeData() {
  try {
    return viewingResume.value?.structured_data ? JSON.parse(viewingResume.value.structured_data) : {}
  } catch (_) {
    return {}
  }
}

function resumeValue(data, keys) {
  for (const key of keys) {
    if (data && data[key] !== undefined && data[key] !== null && String(data[key]).trim()) return data[key]
  }
  return '-'
}

function resumeList(value) {
  if (Array.isArray(value)) return value
  if (value && typeof value === 'object') return [value]
  return []
}

function resumeText(value) {
  if (value === undefined || value === null || value === '') return '-'
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2)
}

function resumeField(item, keys) {
  return resumeValue(item || {}, keys)
}

function resumeSectionRows(section, item) {
  if (section === '教育经历') {
    return [
      [['学位', resumeField(item, ['学位', '学位名称'])], ['学历', resumeField(item, ['学历', '学业水平'])]],
      [['学校', resumeField(item, ['学校', '院校'])], ['专业', resumeField(item, ['专业', '所学专业'])]],
      [['开始时间', resumeField(item, ['开始时间', '入学时间'])], ['结束时间', resumeField(item, ['结束时间', '毕业时间'])]],
    ]
  }
  const nameLabel = section === '工作经历' ? '公司' : '项目名称'
  const nameKeys = section === '工作经历' ? ['公司', '公司名称'] : ['项目名称', '项目名', '名称']
  const roleLabel = section === '工作经历' ? '职位' : '角色'
  const roleKeys = section === '工作经历' ? ['职位', '岗位'] : ['角色', '职责']
  return [
    [[nameLabel, resumeField(item, nameKeys)], [roleLabel, resumeField(item, roleKeys)]],
    [['开始时间', resumeField(item, ['开始时间', '起始时间'])], ['结束时间', resumeField(item, ['结束时间', '终止时间'])]],
    [['描述', resumeField(item, ['描述', '工作内容', '工作描述', '主要职责', '岗位职责', '项目描述', '项目内容', '项目成果', '个人贡献'])]],
  ]
}

async function logout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' })
  } catch (_) {}
  try {
    ;['token', 'username', 'nickname', 'avatar', 'role', 'email', 'phone', 'company', 'bio'].forEach(key => localStorage.removeItem(key))
  } catch (_) {}
  router.push('/')
}

function statusLabel(status) {
  return { wait: '待进入', pending: '等待通知', running: '进行中', finish: '已完成', cancel: '已取消' }[status] || status || '等待通知'
}

function formatDateTime(value) {
  const text = String(value || '').trim().replace('T', ' ')
  return text ? text.slice(0, 16) : '-'
}

function statusPillClass(status) {
  return {
    wait: 'bg-[#fff7df] text-[#a66b00]',
    pending: 'bg-[#eef1f6] text-[#7c8595]',
    running: 'bg-[#e8f2ff] text-[#246bdb]',
    finish: 'bg-[#e7f8ef] text-[#15a05f]',
    cancel: 'bg-[#fff0f0] text-[#e14a4a]',
  }[status] || 'bg-[#eef1f6] text-[#7c8595]'
}

function lineClass(plan, group) {
  if (plan.interview_result === 'pass') return 'bg-[#22c55e]'
  if (['wait', 'running'].includes(plan.status)) return 'bg-[#4776ff]'
  return 'bg-[#ccd4e2]'
}

function screeningStatusText(group) {
  if (group.screening_status === '初筛通过') return '初筛通过'
  if (group.screening_status === '不合适') return '筛选不通过'
  return '筛选中'
}

function screeningNodeClass(group) {
  if (group.screening_status === '初筛通过') return 'bg-[#22c55e] text-white'
  if (group.screening_status === '不合适' || group.application_status === 'rejected') return 'bg-[#c7ccd6] text-white'
  return 'bg-[#4776ff] text-white'
}

function screeningLineClass(group) {
  return group.screening_status === '初筛通过' ? 'bg-[#22c55e]' : 'bg-[#ccd4e2]'
}

function screeningStatusPillClass(group) {
  if (group.screening_status === '初筛通过') return 'bg-[#e7f8ef] text-[#15a05f]'
  if (group.screening_status === '不合适' || group.application_status === 'rejected') return 'bg-[#eef1f6] text-[#667085]'
  return 'bg-[#e8f2ff] text-[#246bdb]'
}

function shouldShowOfferStage(group) {
  return Boolean(
    group.plans.length ||
    group.offer_status ||
    group.application_current_stage === 'offer' ||
    group.application_status === 'hired'
  )
}

function nodeClass(plan, group) {
  if (plan.interview_result === 'pass') return 'bg-[#22c55e] text-white'
  if (group.application_status === 'rejected' || plan.interview_result === 'reject' || plan.status === 'cancel') return 'bg-[#c7ccd6] text-white'
  if (plan.status === 'finish') return 'bg-[#f59e0b] text-white'
  if (plan.status === 'running') return 'bg-[#4776ff] text-white'
  if (plan.status === 'wait') return 'bg-[#11b89f] text-white'
  return 'bg-[#d8deea] text-[#657084]'
}

function groupStatusPillClass(group) {
  if (group.application_status === 'rejected') return 'bg-[#d8dce5] text-[#667085]'
  if (group.application_status === 'hired') return 'bg-[#e7f8ef] text-[#15a05f]'
  return statusPillClass(group.latest_status)
}

function groupStatusText(group) {
  if (group.application_status === 'hired') return 'Offer 已接受 · 招聘完成'
  if (group.application_status === 'rejected' && group.screening_status === '不合适') {
    return '初筛不通过 · 流程已结束'
  }
  const rejectedPlan = group.plans.find(plan => plan.interview_result === 'reject')
  if (group.application_status === 'rejected' && rejectedPlan) {
    return `${rejectedPlan.interview_round || '面试'}不通过 · 流程已结束`
  }
  if (group.application_status === 'rejected' && group.offer_status === 'declined') return '候选人拒绝 Offer · 流程已结束'
  if (group.application_status === 'rejected' && group.offer_status === 'rejected') return '未发放 Offer · 流程已结束'
  if (group.application_current_stage === 'offer' && group.offer_status === 'pending') return '全部面试通过 · 待发放 Offer'
  if (group.application_current_stage === 'offer' && group.offer_status === 'offered') return 'Offer 已发放 · 待确认'
  if (group.application_current_stage === 'screening') {
    return group.screening_status === '初筛通过' ? '初筛通过 · 待创建面试流程' : '简历筛选中'
  }
  if (group.current_plan) return `${group.current_plan.interview_round || '面试'} · ${statusLabel(group.current_plan.status)}`
  return '等待通知'
}

function planStatusText(plan, group) {
  if (group.application_status === 'rejected' && plan.status === 'cancel') {
    return '流程已终止'
  }
  if (plan.interview_result === 'reject') return '面试不通过'
  if (group.plans.some(item => item.interview_result === 'reject') && plan.status === 'cancel') return '流程已终止'
  return statusLabel(plan.status)
}

function offerStatusText(status, applicationStatus = '') {
  if (applicationStatus === 'rejected' && !status) return '流程终止'
  return {
    pending: '待发放',
    offered: '待确认',
    accepted: '已接受',
    declined: '已拒绝',
    rejected: '不发放',
  }[status] || '未开始'
}

function offerNodeClass(status, applicationStatus = '') {
  if (applicationStatus === 'rejected') return 'bg-[#c7ccd6] text-white'
  if (status === 'accepted') return 'bg-[#22c55e] text-white'
  if (status === 'offered') return 'bg-[#7c3aed] text-white'
  if (['declined', 'rejected'].includes(status)) return 'bg-[#c7ccd6] text-white'
  if (status === 'pending') return 'bg-[#f59e0b] text-white'
  return 'bg-[#d8deea] text-[#657084]'
}

function offerLineClass(group) {
  if (group.offer_status === 'accepted') return 'bg-[#22c55e]'
  if (group.application_status === 'rejected' || ['declined', 'rejected'].includes(group.offer_status)) return 'bg-[#ccd4e2]'
  if (group.offer_status) return 'bg-[#8b5cf6]'
  return 'bg-[#ccd4e2]'
}

async function respondOffer(group, action) {
  if (!group.application_id) return
  const accept = action === 'accept'
  const confirmed = await window.appConfirm(
    accept ? `确认接受「${group.jd_name}」的 Offer 吗？` : `确认拒绝「${group.jd_name}」的 Offer 吗？`,
    { title: accept ? '接受 Offer' : '拒绝 Offer', confirmText: accept ? '确认接受' : '确认拒绝' },
  )
  if (!confirmed) return
  const token = safeGetLocalStorage('token', '')
  const res = await fetch(`/api/plans/my/applications/${group.application_id}/offer`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ action }),
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    alert(error.detail || '更新 Offer 状态失败')
    return
  }
  await loadPlans()
}

function groupMatchPercent(group) {
  const score = Number(group?.match_score || group?.plans?.find(plan => Number(plan.match_score) > 0)?.match_score || 0)
  if (score <= 0) return null
  return Math.min(Math.max(score, 0), 100)
}

function canCancelApplication(group) {
  return Boolean(
    group?.application_id &&
    group.application_status === 'active' &&
    group.application_current_stage === 'screening' &&
    group.screening_status === '待筛选'
  )
}

function canEnterInterview(plan) {
  return Boolean(plan?.interview_ready === true && ['wait', 'running'].includes(plan.status))
}

async function cancelApplication(group) {
  if (!canCancelApplication(group)) return
  const confirmed = await window.appConfirm(`确定取消「${group.jd_name || '该岗位'}」的投递吗？取消后将立即释放对应招聘类型的投递名额。`, {
    title: '取消岗位投递',
    confirmText: '确认取消',
  })
  if (!confirmed) return
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/plans/applications/${group.application_id}/cancel`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '取消投递失败')
    }
    await loadPlans()
    showToast(`已取消「${group.jd_name || '该岗位'}」的投递，并释放 1 个名额`, 'success')
  } catch (e) {
    showToast(e.message || '取消投递失败', 'error')
  }
}

function jobSummary(job) {
  const text = `${job.responsibilities || ''}`.replace(/\s+/g, ' ').trim()
  return text || '根据你的投递记录与面试方向，为你推荐相近岗位。'
}
</script>

<template>
  <div class="min-h-screen bg-[linear-gradient(180deg,#f2f5fb_0%,#f8fafc_260px,#f6f7fb_100%)] text-[#202838]">
    <CandidateNavbar active="center" />

    <main class="mx-auto grid max-w-[1680px] gap-10 px-6 py-10 lg:px-10 xl:grid-cols-[minmax(0,1fr)_380px] 2xl:px-12">
      <section class="min-w-0 space-y-6">
        <div class="overflow-hidden rounded-2xl bg-white shadow-[0_16px_42px_rgba(15,35,80,0.08)]">
          <div class="relative min-h-[220px] bg-[linear-gradient(135deg,#e9f3ff_0%,#f8fbff_48%,#eef8f5_100%)] p-8 lg:p-10">
            <div class="absolute right-8 top-8 hidden h-44 w-80 rounded-full bg-[radial-gradient(circle,rgba(76,111,255,0.13),transparent_65%)] md:block"></div>
            <div class="relative flex flex-wrap items-start justify-between gap-5">
              <div>
                <h1 class="text-2xl font-black tracking-tight">个人中心</h1>
                <p class="mt-2 text-sm text-[#667085]">查看你的简历、投递岗位和 AI 面试安排</p>
              </div>
              <div class="flex gap-3 text-sm">
                <button class="rounded-full px-3 py-2 font-semibold text-[#475467] hover:bg-white/70" @click="router.push('/jobs/social')">查看职位</button>
                <button class="rounded-full bg-[#11b89f] px-4 py-2 font-semibold text-white hover:bg-[#0d9488]">我的进度</button>
              </div>
            </div>

            <div class="relative mt-9 flex flex-wrap items-center gap-7">
              <label class="relative flex h-24 w-24 shrink-0 cursor-pointer items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-[#4b6cff] to-[#11b89f] text-3xl font-black text-white shadow-lg shadow-blue-100 transition hover:opacity-80 group">
                <img v-if="avatar" :src="avatar" class="h-full w-full object-cover" alt="">
                <span v-else>{{ displayName.slice(0, 1) }}</span>
                <span class="absolute inset-0 flex items-center justify-center rounded-full bg-black/30 text-xs font-bold text-white opacity-0 transition group-hover:opacity-100"><i class="fa fa-camera mr-1"></i>更换</span>
                <input type="file" accept=".png,.jpg,.jpeg,.gif,.webp" class="hidden" @change="uploadAvatar">
              </label>
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-3">
                  <h2 class="truncate text-3xl font-black lg:text-4xl">{{ displayName }}</h2>
                  <span class="rounded-full bg-[#ecfdf6] px-3 py-1 text-sm font-bold text-[#0f9f8f]">候选人</span>
                </div>
                <div class="mt-4 grid gap-4 text-sm text-[#3f4b5f] md:grid-cols-3">
                  <div><span class="font-bold text-[#202838]">账号</span><span class="ml-3">{{ username || '-' }}</span></div>
                  <div><span class="font-bold text-[#202838]">移动电话</span><span class="ml-3">{{ phone || '-' }}</span></div>
                  <div><span class="font-bold text-[#202838]">电子邮件</span><span class="ml-3">{{ email || '-' }}</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="rounded-2xl bg-white p-8 shadow-[0_16px_42px_rgba(15,35,80,0.08)] lg:p-9">
          <div class="mb-7 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 class="text-2xl font-black">我的简历</h2>
              <p class="mt-1 text-sm text-[#667085]">当前简历会用于岗位匹配和面试题生成</p>
            </div>
            <div v-if="hasResume" class="flex gap-3 text-sm">
              <button class="font-semibold text-[#344054] hover:text-[#11b89f] disabled:cursor-wait disabled:opacity-50" :disabled="resumePreviewLoading" @click="viewResume">
                <i :class="['fa mr-1', resumePreviewLoading ? 'fa-spinner fa-spin' : 'fa-eye']"></i>{{ resumePreviewLoading ? '加载中...' : '查看简历' }}
              </button>
              <button class="font-semibold text-[#344054] hover:text-[#11b89f]" @click="router.push({ path: '/resume-edit', query: { filename: resumeFileName } })"><i class="fa fa-pencil mr-1"></i> 编辑</button>
            </div>
          </div>

          <div class="mb-5 flex flex-col gap-3 rounded-xl border border-[#dbe7ff] bg-[#f5f8ff] px-4 py-3 text-sm text-[#53627a] sm:flex-row sm:items-center sm:justify-between">
            <div class="flex items-start gap-2.5">
              <i class="fa fa-info-circle mt-0.5 text-[#4776ff]"></i>
              <div>
                <span class="font-bold text-[#344054]">投递规则：</span>
                滚动 6 个月内，社招、校招、实习岗位各可同时投递 {{ applicationQuota.limit_per_type }} 个；取消成功后立即释放对应名额。
              </div>
            </div>
            <div class="flex shrink-0 flex-wrap gap-2 text-xs font-semibold text-[#596275]">
              <div class="inline-flex h-7 items-center gap-1.5 rounded-lg bg-white px-2.5">
                <span class="flex h-4 w-4 items-center justify-center rounded-full bg-[#4776ff] text-[9px] text-white">
                  <i class="fa fa-paper-plane"></i>
                </span>
                <span>投递岗位</span>
                <strong class="font-black text-[#344054]">{{ applicationCount }}</strong>
              </div>
              <div class="inline-flex h-7 items-center gap-1.5 rounded-lg bg-white px-2.5">
                <span class="flex h-4 w-4 items-center justify-center rounded-full bg-[#11b89f] text-[10px] text-white">
                  <i class="fa fa-check"></i>
                </span>
                <span>结束流程</span>
                <strong class="font-black text-[#344054]">{{ closedWorkflowCount }}</strong>
              </div>
              <div class="inline-flex h-7 items-center gap-1.5 rounded-lg bg-white px-2.5">
                <span class="flex h-4 w-4 items-center justify-center rounded-full bg-[#f59e0b] text-[8px] text-white">
                  <i class="fa fa-circle"></i>
                </span>
                <span>进行中</span>
                <strong class="font-black text-[#344054]">{{ activeInterviewCount }}</strong>
              </div>
            </div>
          </div>

          <!-- 无简历时的上传提示 -->
          <div v-if="pendingApplyJob && !hasResume" class="mb-6 rounded-2xl border-2 border-dashed border-amber-300 bg-amber-50/50 p-6 text-center">
            <i class="fa fa-exclamation-triangle text-3xl text-amber-400 mb-3 block"></i>
            <p class="text-base font-bold text-amber-700">请先上传简历再投递岗位</p>
            <p class="mt-1 text-sm text-amber-600">上传简历后会自动完成投递，并在后台简历管理中可见</p>
            <label class="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-xl bg-[#11b89f] px-6 py-3 font-bold text-white hover:bg-[#0d9488] transition">
              <i :class="['fa', resumeUploading ? 'fa-spinner fa-spin' : 'fa-upload']"></i>
              {{ resumeUploading ? '上传解析中...' : '上传简历' }}
              <input type="file" accept=".pdf,.docx,.txt,.md" class="hidden" @change="uploadResume">
            </label>
          </div>
          <div>
            <!-- 无简历状态 -->
            <div v-if="!hasResume && !pendingApplyJob" class="flex min-h-[160px] items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-gray-200 bg-[#f8fafc] p-6 lg:p-7">
              <label class="flex cursor-pointer flex-col items-center gap-3 text-center">
                <i class="fa fa-cloud-upload text-4xl text-gray-300"></i>
                <span class="text-sm font-bold text-gray-500">尚未上传简历，点击上传</span>
                <span class="text-xs text-gray-400">支持 PDF / DOCX / TXT / MD</span>
                <span class="rounded-lg bg-[#11b89f] px-5 py-2 text-sm font-bold text-white hover:bg-[#0d9488] transition">
                  <i :class="['fa mr-1', resumeUploading ? 'fa-spinner fa-spin' : 'fa-upload']"></i>{{ resumeUploading ? '上传中...' : '上传简历' }}
                </span>
                <input type="file" accept=".pdf,.docx,.txt,.md" class="hidden" @change="uploadResume">
              </label>
            </div>
            <!-- 有简历状态 -->
            <div v-else class="rounded-2xl bg-[#f2f6fb] p-5 lg:p-6">
              <div class="flex min-w-0 gap-5">
                <div class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-[#2f80ff] to-[#11b89f] text-base font-black text-white shadow-sm">PDF</div>
                <div class="min-w-0 flex-1">
                  <div class="flex min-w-0 flex-wrap items-center gap-2.5">
                    <div class="min-w-0 truncate text-xl font-black lg:text-2xl">{{ resumeFileName }}</div>
                    <span
                      class="inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold"
                      :class="resumeParseBadgeClass"
                    >
                      <i :class="['fa', resumeParseStatus === 'success' ? 'fa-check-circle' : resumeParseStatus === 'fail' ? 'fa-exclamation-circle' : 'fa-clock-o']"></i>
                      {{ resumeParseLabel }}
                    </span>
                  </div>
                  <div class="mt-2 text-sm text-[#667085]">{{ applicationCount ? `已用于 ${applicationCount} 个岗位投递` : '当前简历尚未投递岗位' }}</div>
                  <div class="mt-4 inline-flex items-center rounded-lg bg-white/70 px-3 py-1.5 text-xs font-semibold text-[#667085]">
                    <i class="fa fa-file-text-o mr-1.5 text-[#11b89f]"></i>当前使用版本
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="rounded-2xl bg-white p-7 shadow-[0_16px_42px_rgba(15,35,80,0.08)]">
          <div class="mb-7 flex flex-wrap items-center justify-between gap-4">
            <div>
              <div class="flex flex-wrap items-center gap-3">
                <h2 class="text-2xl font-black">投递记录 - {{ filteredWorkflowGroups.length }} 条</h2>
                <div
                  class="rounded-full border px-2.5 py-1.5 text-xs font-bold"
                  :class="quotaRemaining(activeQuotaItem.key) > 0
                    ? 'border-[#dbe7ff] bg-[#f5f8ff] text-[#4776ff]'
                    : 'border-[#ffd9d9] bg-[#fff3f3] text-[#d94242]'"
                >
                  {{ activeQuotaText }}
                </div>
              </div>
              <p class="mt-1 text-sm text-[#667085]">展开岗位后可以查看每一轮面试状态，并进入当前可操作轮次</p>
            </div>
            <div class="flex overflow-hidden rounded-full bg-[#e9ecf5] p-1">
              <button
                v-for="tab in tabs"
                :key="tab.key"
                class="rounded-full px-5 py-2 text-sm font-bold transition"
                :class="activeTab === tab.key ? 'bg-[#4b6cff] text-white shadow-sm' : 'text-[#667085]'"
                @click="activeTab = tab.key"
              >
                {{ tab.label }}
                <span
                  class="ml-1.5 inline-flex min-w-5 items-center justify-center rounded-full px-1.5 py-0.5 text-[11px]"
                  :class="activeTab === tab.key ? 'bg-white/20 text-white' : 'bg-white text-[#667085]'"
                >
                  {{ tabApplicationCount(tab.key) }}
                </span>
              </button>
            </div>
          </div>

          <div v-if="loading" class="rounded-xl bg-[#f7f9fc] p-10 text-center text-[#667085]">正在加载你的面试安排...</div>
          <div v-else-if="error" class="rounded-xl border border-red-200 bg-red-50 p-8 text-center text-red-600">
            {{ error }}
            <button class="ml-3 font-bold underline" @click="loadPlans()">重试</button>
          </div>
          <div v-else-if="filteredWorkflowGroups.length" class="space-y-4">
            <article
              v-for="group in filteredWorkflowGroups"
              :key="group.key"
              class="overflow-hidden rounded-xl border border-[#e8edf5] bg-[#f8fbff]"
            >
              <button
                class="flex w-full items-center justify-between gap-5 px-5 py-5 text-left transition"
                :class="activeGroup?.key === group.key ? 'bg-[#f2f7ff]' : ''"
                @click="selectAndToggleWorkflow(group)"
              >
                <div class="flex min-w-0 items-center gap-4">
                  <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#2f80ff] text-white">
                    <i class="fa fa-bar-chart"></i>
                  </div>
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-3">
                      <h3 class="truncate text-2xl font-black">{{ group.jd_name }}</h3>
                      <span class="rounded-full px-3 py-1 text-sm font-bold" :class="groupStatusPillClass(group)">{{ groupStatusText(group) }}</span>
                      <span
                        class="rounded-full border px-3 py-1 text-sm font-bold"
                        :class="groupMatchPercent(group) === null ? 'border-[#e4e9f1] bg-white text-[#98a2b3]' : 'border-[#ccefe7] bg-[#ecfdf8] text-[#0f9f8f]'"
                      >
                        <i class="fa fa-bullseye mr-1"></i>
                        岗位匹配 {{ groupMatchPercent(group) === null ? '待评估' : `${groupMatchPercent(group)}%` }}
                      </span>
                      <button
                        v-if="canCancelApplication(group)"
                        class="rounded-full border border-red-100 bg-white px-3 py-1 text-sm font-bold text-red-500 transition hover:border-red-200 hover:bg-red-50"
                        @click.stop="cancelApplication(group)"
                      >
                        取消投递
                      </button>
                    </div>
                    <div class="mt-2 text-sm text-[#667085]">
                      {{ group.workflow_name }} ｜ 投递时间：{{ formatDateTime(group.application_created_at) }} ｜ 已完成 {{ group.finished_count }}/{{ group.plans.length }} ｜ {{ group.location || '地点待定' }}
                    </div>
                  </div>
                </div>
                <i class="fa text-xl text-[#667085]" :class="isExpanded(group) ? 'fa-angle-up' : 'fa-angle-down'"></i>
              </button>

              <div class="overflow-x-auto border-t border-[#e8edf5] bg-[#f8fbff] px-5 py-4 pb-5">
                <div
                  class="flex items-start"
                  :class="group.plans.length || shouldShowOfferStage(group) ? 'min-w-[680px]' : 'min-w-0'"
                >
                  <div class="flex w-[128px] shrink-0 flex-col items-center text-center">
                    <div class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-black" :class="screeningNodeClass(group)">
                      <i v-if="group.screening_status === '初筛通过'" class="fa fa-check"></i>
                      <i v-else-if="group.screening_status === '不合适' || group.application_status === 'rejected'" class="fa fa-exclamation"></i>
                      <span v-else>1</span>
                    </div>
                    <div class="mt-2 font-bold" :class="group.screening_status === '初筛通过' ? 'text-[#15a05f]' : 'text-[#667085]'">简历筛选</div>
                    <div class="mt-1 text-xs text-[#8a94a6]">{{ screeningStatusText(group) }}</div>
                  </div>
                  <div
                    v-if="group.plans.length"
                    class="mx-2 mt-4 h-0.5 min-w-8 flex-1 rounded-full"
                    :class="screeningLineClass(group)"
                  ></div>
                  <template v-for="(plan, index) in group.plans" :key="`summary-${plan.id}`">
                    <div class="flex w-[128px] shrink-0 flex-col items-center text-center">
                      <div class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-black" :class="nodeClass(plan, group)">
                        <i v-if="group.application_status === 'rejected' || plan.interview_result === 'reject'" class="fa fa-exclamation"></i>
                        <i v-else-if="plan.status === 'finish'" class="fa fa-check"></i>
                        <span v-else>{{ plan.stage_order || index + 1 }}</span>
                      </div>
                      <div class="mt-2 font-bold" :class="plan.interview_result === 'pass' ? 'text-[#15a05f]' : ['wait', 'running'].includes(plan.status) ? 'text-[#246bdb]' : 'text-[#667085]'">
                        {{ plan.interview_round }}
                      </div>
                      <div class="mt-1 text-xs text-[#8a94a6]">{{ planStatusText(plan, group) }}</div>
                    </div>
                    <div v-if="index < group.plans.length - 1" class="mx-2 mt-4 h-0.5 min-w-8 flex-1 rounded-full" :class="lineClass(plan, group)"></div>
                  </template>
                  <div v-if="shouldShowOfferStage(group)" class="mx-2 mt-4 h-0.5 min-w-8 flex-1 rounded-full" :class="offerLineClass(group)"></div>
                  <div v-if="shouldShowOfferStage(group)" class="flex w-[128px] shrink-0 flex-col items-center text-center">
                    <div class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-black" :class="offerNodeClass(group.offer_status, group.application_status)">
                      <i v-if="group.offer_status === 'accepted'" class="fa fa-check"></i>
                      <i v-else-if="group.application_status === 'rejected' || ['declined', 'rejected'].includes(group.offer_status)" class="fa fa-exclamation"></i>
                      <i v-else class="fa fa-envelope-o"></i>
                    </div>
                    <div class="mt-2 font-bold" :class="group.offer_status === 'accepted' ? 'text-[#15a05f]' : group.application_status === 'rejected' ? 'text-[#667085]' : group.offer_status ? 'text-[#6d28d9]' : 'text-[#667085]'">Offer</div>
                    <div class="mt-1 text-xs text-[#8a94a6]">{{ offerStatusText(group.offer_status, group.application_status) }}</div>
                  </div>
                </div>
              </div>

              <div v-show="isExpanded(group)" class="border-t border-[#e8edf5] bg-white px-5 py-5">
                <div class="mt-5 overflow-hidden rounded-xl border border-[#edf1f7]">
                  <table class="w-full text-left text-sm">
                    <thead class="bg-[#f8fbff] text-[#667085]">
                      <tr>
                        <th class="px-4 py-3 font-bold">环节</th>
                        <th class="px-4 py-3 font-bold">面试官 / 方式</th>
                        <th class="px-4 py-3 font-bold">时间</th>
                        <th class="px-4 py-3 font-bold">状态</th>
                        <th class="px-4 py-3 font-bold">操作</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-[#edf1f7]">
                      <tr>
                        <td class="px-4 py-3 font-semibold">简历筛选</td>
                        <td class="px-4 py-3 text-[#475467]">招聘团队</td>
                        <td class="px-4 py-3 text-[#667085]">{{ formatDateTime(group.application_created_at) }}</td>
                        <td class="px-4 py-3">
                          <span class="rounded-full px-3 py-1 text-xs font-bold" :class="screeningStatusPillClass(group)">{{ screeningStatusText(group) }}</span>
                        </td>
                        <td class="px-4 py-3 text-[#98a2b3]">—</td>
                      </tr>
                      <tr v-for="plan in group.plans" :key="plan.id">
                        <td class="px-4 py-3 font-semibold">{{ plan.interview_round }}</td>
                        <td class="px-4 py-3 text-[#475467]">{{ plan.interviewer || 'AI 面试官' }}</td>
                        <td class="px-4 py-3 text-[#667085]">{{ plan.scheduled_at || '待安排' }}</td>
                        <td class="px-4 py-3"><span class="rounded-full px-3 py-1 text-xs font-bold" :class="statusPillClass(plan.status)">{{ planStatusText(plan, group) }}</span></td>
                        <td class="px-4 py-3">
                          <button v-if="canEnterInterview(plan)" class="font-bold text-[#1677ff] hover:text-[#0958d9]" @click.stop="enterInterview(plan)">进入面试</button>
                          <span v-else class="text-[#98a2b3]">{{ plan.interview_block_reason || '等待' }}</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="shouldShowOfferStage(group)" class="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-violet-100 bg-violet-50/60 px-4 py-4">
                  <div>
                    <div class="font-black text-violet-900"><i class="fa fa-envelope-o mr-2"></i>Offer 阶段</div>
                    <div class="mt-1 text-sm text-violet-600">{{ offerStatusText(group.offer_status, group.application_status) }}</div>
                  </div>
                  <div v-if="group.offer_status === 'offered'" class="flex gap-2">
                    <button class="rounded-lg border border-red-200 bg-white px-4 py-2 font-bold text-red-600 hover:bg-red-50" @click="respondOffer(group, 'decline')">拒绝 Offer</button>
                    <button class="rounded-lg bg-violet-600 px-4 py-2 font-bold text-white hover:bg-violet-700" @click="respondOffer(group, 'accept')">接受 Offer</button>
                  </div>
                </div>
              </div>
            </article>
          </div>
          <div v-else class="rounded-xl bg-[#f7f9fc] p-10 text-center text-[#667085]">
            暂无投递记录，请先在职位页选择适合的岗位。
          </div>
        </div>
      </section>

      <aside class="space-y-6 xl:sticky xl:top-24 xl:h-fit">
        <div class="rounded-2xl bg-white p-6 shadow-[0_16px_42px_rgba(15,35,80,0.08)]">
          <div class="flex items-center justify-between border-l-4 border-[#11b89f] pl-4">
            <div class="text-xl font-black">当前进行中的岗位</div>
            <span class="rounded-full bg-[#ecfdf8] px-2.5 py-1 text-xs font-black text-[#0f9f8f]">{{ operableWorkflowGroups.length }}</span>
          </div>

          <div v-if="operableWorkflowGroups.length > 1" class="mt-5 max-h-40 space-y-2 overflow-y-auto pr-1">
            <button
              v-for="group in operableWorkflowGroups"
              :key="`operation-${group.key}`"
              class="flex w-full items-center justify-between gap-3 rounded-xl border px-3 py-2.5 text-left transition"
              :class="activeGroup?.key === group.key
                ? 'border-[#9ce3d6] bg-[#ecfdf8] text-[#087f71]'
                : 'border-[#e8edf5] bg-[#f8fbff] text-[#475467] hover:border-[#cdd9eb]'"
              @click="selectWorkflow(group)"
            >
              <span class="truncate text-sm font-bold">{{ group.jd_name }}</span>
              <i class="fa fa-chevron-right shrink-0 text-xs opacity-60"></i>
            </button>
          </div>

          <div v-if="activeGroup" class="mt-6 flex items-center gap-4">
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#2f80ff] text-white">
              <i class="fa fa-bar-chart text-2xl"></i>
            </div>
            <div class="min-w-0">
              <div class="truncate text-2xl font-black">{{ activeGroup.jd_name }}</div>
              <div class="mt-2 inline-flex rounded-lg bg-[#e8f2ff] px-3 py-1 text-sm font-bold text-[#246bdb]">{{ groupStatusText(activeGroup) }}</div>
            </div>
          </div>
          <div v-if="activeGroup" class="mt-7 space-y-3 text-sm text-[#667085]">
            <div><i class="fa fa-info-circle mr-2 text-[#98a2b3]"></i>下一环节：{{ nextStepText }}</div>
            <div><i class="fa fa-clock-o mr-2 text-[#98a2b3]"></i>面试时间：{{ currentPlan?.scheduled_at || '暂未设置' }}</div>
          </div>
          <button
            v-if="currentPlan"
            class="mt-7 w-full rounded-xl bg-[#11b89f] px-5 py-4 font-black text-white transition hover:bg-[#0d9488]"
            @click="enterInterview(currentPlan)"
          >
            {{ currentActionText }}
          </button>
          <div v-else-if="activeGroup?.offer_status === 'offered'" class="mt-7 grid grid-cols-2 gap-2">
            <button class="rounded-xl border border-[#d8dce8] bg-white px-3 py-3 text-sm font-black text-[#667085] hover:bg-[#f7f9fc]" @click="respondOffer(activeGroup, 'decline')">拒绝 Offer</button>
            <button class="rounded-xl bg-violet-600 px-3 py-3 text-sm font-black text-white hover:bg-violet-700" @click="respondOffer(activeGroup, 'accept')">接受 Offer</button>
          </div>
          <button v-else-if="activeGroup" class="mt-7 w-full cursor-not-allowed rounded-xl bg-[#eef1f6] px-5 py-4 font-black text-[#98a2b3]">等待招聘方处理</button>
          <div v-else class="mt-6 rounded-xl bg-[#f7f9fc] px-4 py-6 text-center text-sm text-[#98a2b3]">暂无进行中的岗位</div>
        </div>

        <div class="rounded-2xl bg-white p-6 shadow-[0_16px_42px_rgba(15,35,80,0.08)]">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-black">智能职位推荐</h2>
            <button class="text-sm font-bold text-[#4b6cff]" @click="router.push('/jobs/social')">全部职位 &gt;</button>
          </div>
          <div v-if="jobLoading" class="mt-5 rounded-xl bg-[#f8fbff] p-5 text-center text-sm text-[#667085]">正在推荐...</div>
          <div v-else class="mt-5 space-y-5">
            <div v-for="job in recommendedJobs" :key="job.id" class="cursor-pointer border-b border-[#edf1f7] pb-5 last:border-b-0 last:pb-0 transition hover:bg-gray-50 rounded-lg -mx-2 px-2" @click="router.push(`/jobs/${job.id}`)">
              <div class="line-clamp-1 text-lg font-black">{{ job.name }}</div>
              <div class="mt-2 flex flex-wrap gap-2">
                <span class="rounded border border-[#11b89f] px-2 py-0.5 text-sm text-[#0f9f8f]">{{ job.category || '技术' }}</span>
                <span class="rounded border border-[#d8dce8] px-2 py-0.5 text-sm text-[#667085]">{{ job.location || '深圳' }}</span>
              </div>
              <div class="mt-3 grid grid-cols-3 gap-px overflow-hidden rounded bg-[#edf3f8] text-center text-xs text-[#4f5a6d]">
                <span class="bg-[#f8fbff] py-2">岗位匹配</span>
                <span class="bg-[#f8fbff] py-2">AI 面试</span>
                <span class="bg-[#f8fbff] py-2">可投递</span>
              </div>
              <p class="mt-3 line-clamp-2 text-sm leading-6 text-[#667085]">{{ jobSummary(job) }}</p>
            </div>
            <div v-if="!recommendedJobs.length" class="rounded-xl bg-[#f8fbff] p-6 text-center text-sm text-[#667085]">暂无推荐职位</div>
          </div>
        </div>

        <div class="rounded-2xl bg-white p-6 shadow-[0_16px_42px_rgba(15,35,80,0.08)]">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-black">我的收藏</h2>
            <button
              class="inline-flex min-w-[76px] items-center justify-center rounded-lg px-2.5 py-1.5 text-sm font-bold text-[#4b6cff] transition hover:bg-[#eef2ff] disabled:cursor-wait disabled:text-[#8fa2e8]"
              :disabled="favoriteRefreshing"
              :aria-busy="favoriteRefreshing"
              @click="loadFavoriteJobs(true)"
            >
              <i :class="['fa fa-refresh mr-1.5', favoriteRefreshing ? 'fa-spin' : '']"></i>
              {{ favoriteRefreshing ? '刷新中' : '刷新' }}
            </button>
          </div>
          <div v-if="favoriteJobs.length" class="space-y-3">
            <div v-for="job in favoriteJobs" :key="job.id" class="flex items-center justify-between rounded-xl border border-[#edf1f7] p-3 hover:bg-[#f8fbff] cursor-pointer" @click="router.push(`/jobs/${job.id}`)">
              <div class="min-w-0 text-left">
                <div class="text-sm font-bold truncate">{{ job.name }}</div>
                <div class="text-xs text-[#98a2b3] mt-0.5">{{ job.location || '' }} ｜ {{ job.category || '' }}</div>
              </div>
              <i class="fa fa-chevron-right text-[#98a2b3] text-sm shrink-0 ml-2"></i>
            </div>
          </div>
          <p v-else class="mt-2 text-[#667085] text-sm">还是空的，快去看看岗位吧</p>
          <button class="mt-4 font-bold text-[#4b6cff] text-sm" @click="router.push('/jobs/social')">查看岗位 &gt;</button>
        </div>
      </aside>
    </main>

    <div v-if="viewingResume" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 lg:p-6" @click.self="closeResumePreview">
      <div class="flex h-[92vh] w-[96vw] max-w-[1180px] flex-col overflow-hidden rounded-2xl bg-[#f5f7fb] shadow-2xl">
        <div class="flex h-14 shrink-0 items-center justify-between border-b border-[#e8edf5] px-5 lg:px-7">
          <div class="min-w-0 truncate text-sm font-bold text-[#202838]">{{ viewingResume.original_name || viewingResume.file_path || '简历预览' }}</div>
          <div class="ml-4 flex shrink-0 items-center gap-2">
            <button class="hidden rounded-lg border border-[#dce5f2] px-3 py-2 text-xs font-bold text-[#475467] hover:bg-[#f8fbff] sm:inline-flex" @click="showOriginalResume = !showOriginalResume">
              <i :class="['fa mr-1', showOriginalResume ? 'fa-table' : 'fa-file-pdf-o']"></i>{{ showOriginalResume ? '查看解析' : '查看原文件' }}
            </button>
            <button class="ml-1 text-xl text-[#98a2b3] hover:text-[#344054]" title="关闭" @click="closeResumePreview"><i class="fa fa-times"></i></button>
          </div>
        </div>
        <div class="flex min-h-0 flex-1 flex-col lg:flex-row">
          <div v-if="showOriginalResume" class="min-h-[46%] flex-1 overflow-hidden bg-[#303030] lg:min-h-0 lg:basis-1/2">
            <embed v-if="resumePreviewSrc" :src="`${resumePreviewSrc}#view=FitH`" type="application/pdf" class="h-full w-full" />
            <div v-else class="flex h-full items-center justify-center text-sm text-white/60">暂无简历文件</div>
          </div>
          <div class="min-h-0 flex-1 overflow-auto border-t border-[#e8edf5] bg-white p-5 lg:basis-full lg:border-l-0 lg:border-t-0 lg:p-8">
            <div class="mb-5 flex items-center justify-between">
              <div>
                <div class="text-xs font-bold uppercase tracking-[0.18em] text-[#4776ff]">Resume Profile</div>
                <h3 class="mt-1 text-xl font-black text-[#202838]">简历解析</h3>
              </div>
              <span
                class="rounded-full px-3 py-1 text-xs font-bold"
                :class="viewingResume.parse_status === 'success'
                  ? 'bg-[#e7f8ef] text-[#15a05f]'
                  : viewingResume.parse_status === 'fail'
                    ? 'bg-red-50 text-red-600'
                    : 'bg-amber-50 text-amber-700'"
              >{{ viewingResume.parse_status === 'success' ? '解析成功' : viewingResume.parse_status === 'fail' ? '解析失败' : '未解析' }}</span>
            </div>
            <div v-if="viewingResume.structured_data" class="overflow-hidden rounded-xl border border-[#dfe6f0]">
              <table class="w-full table-fixed border-collapse text-sm leading-7 text-[#344054]">
                <tbody>
                  <tr>
                    <th class="w-24 border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">姓名</th>
                    <td colspan="2" class="border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData()['基础信息'], ['姓名']) }}</td>
                    <th class="w-24 border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">性别</th>
                    <td class="border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData()['基础信息'], ['性别']) }}</td>
                  </tr>
                  <tr>
                    <th class="border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">岗位名称</th>
                    <td colspan="2" class="border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData()['基础信息'], ['岗位名称', '意向岗位']) }}</td>
                    <th class="border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">邮箱</th>
                    <td class="border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData()['基础信息'], ['邮箱', '电子邮箱']) }}</td>
                  </tr>
                  <tr>
                    <th class="border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">电话</th>
                    <td colspan="2" class="border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData()['基础信息'], ['电话', '手机']) }}</td>
                    <th class="border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">年龄</th>
                    <td class="border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData()['基础信息'], ['年龄']) }}</td>
                  </tr>
                  <tr>
                    <th class="border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">籍贯</th>
                    <td colspan="2" class="border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData()['基础信息'], ['籍贯', '户籍', '户籍所在地', '出生地']) }}</td>
                    <th class="border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">地址</th>
                    <td class="border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData()['基础信息'], ['地址', '现居住地', '居住地址']) }}</td>
                  </tr>
                  <tr>
                    <th class="border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">自我评价</th>
                    <td colspan="3" class="whitespace-pre-line border border-[#dfe6f0] px-3 py-2">{{ resumeValue(parsedResumeData(), ['自我评价']) }}</td>
                  </tr>
                  <template v-for="section in ['教育经历', '工作经历', '项目经历']" :key="section">
                    <template v-for="(item, itemIndex) in resumeList(parsedResumeData()[section])" :key="`${section}-${itemIndex}`">
                      <tr v-for="(row, rowIndex) in resumeSectionRows(section, item)" :key="`${section}-${itemIndex}-${rowIndex}`">
                        <th v-if="itemIndex === 0 && rowIndex === 0" :rowspan="resumeList(parsedResumeData()[section]).length * resumeSectionRows(section, item).length" class="w-24 border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">{{ section }}</th>
                        <template v-if="row.length === 2">
                          <th class="w-28 border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">{{ row[0][0] }}</th>
                          <td class="border border-[#dfe6f0] px-3 py-2">{{ resumeText(row[0][1]) }}</td>
                          <th class="w-28 border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">{{ row[1][0] }}</th>
                          <td class="border border-[#dfe6f0] px-3 py-2">{{ resumeText(row[1][1]) }}</td>
                        </template>
                        <template v-else>
                          <th class="border border-[#dfe6f0] bg-[#f5f7fa] px-3 py-2 text-center font-bold text-[#667085]">{{ row[0][0] }}</th>
                          <td colspan="3" class="whitespace-pre-line border border-[#dfe6f0] px-3 py-3 align-top">{{ resumeText(row[0][1]) }}</td>
                        </template>
                      </tr>
                    </template>
                  </template>
                </tbody>
              </table>
            </div>
            <div v-else class="rounded-xl bg-[#f8fbff] p-6 text-center text-sm text-[#667085]">暂无解析结果</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
