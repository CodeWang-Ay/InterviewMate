<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(true)
const jobLoading = ref(false)
const plans = ref([])
const recommendedJobs = ref([])
const error = ref('')
const expandedWorkflows = ref(new Set())
const activeTab = ref('social')
const username = ref('')
const nickname = ref('')
const phone = ref('')
const email = ref('')

const tabs = [
  { key: 'social', label: '社会招聘' },
  { key: 'campus', label: '校园招聘' },
]

const workflowGroups = computed(() => {
  const map = new Map()
  plans.value.forEach(plan => {
    const key = workflowKey(plan)
    if (!map.has(key)) {
      map.set(key, {
        key,
        workflow_id: plan.workflow_id || '',
        workflow_name: plan.workflow_name || '我的面试流程',
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
    if (!group.location && plan.location) group.location = plan.location
  })
  return Array.from(map.values()).map(group => {
    const sortedPlans = [...group.plans].sort((a, b) => Number(a.stage_order || 1) - Number(b.stage_order || 1))
    const current = sortedPlans.find(p => ['wait', 'running'].includes(p.status)) || null
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

const filteredWorkflowGroups = computed(() => {
  const tabText = activeTab.value === 'campus' ? '校招' : '社招'
  return workflowGroups.value.filter(group => group.recruitment_type === tabText)
})
const activeGroup = computed(() => workflowGroups.value.find(group => group.current_plan) || workflowGroups.value[0] || null)
const currentPlan = computed(() => activeGroup.value?.current_plan || null)
const applicationCount = computed(() => workflowGroups.value.length)
const closedWorkflowCount = computed(() => workflowGroups.value.filter(group => {
  if (!group.plans.length) return false
  return group.plans.every(plan => ['finish', 'cancel'].includes(plan.status))
}).length)
const activeInterviewCount = computed(() => plans.value.filter(plan => ['wait', 'running'].includes(plan.status)).length)
const displayName = computed(() => nickname.value || activeGroup.value?.candidate_name || username.value || '候选人')
const resumeFileName = computed(() => activeGroup.value?.resume_filename || activeGroup.value?.plans.find(plan => plan.resume_filename)?.resume_filename || '暂未上传简历')
const resumeMatchPercent = computed(() => {
  const score = activeGroup.value?.current_plan?.match_score || activeGroup.value?.plans.find(plan => plan.match_score)?.match_score || 0
  return score ? Math.min(Math.max(Number(score), 0), 100) : 85
})
const currentActionText = computed(() => {
  if (!currentPlan.value) return '等待通知'
  return currentPlan.value.status === 'running' ? '继续本轮面试' : '进入本轮面试'
})
const nextStepText = computed(() => currentPlan.value?.interview_round || '等待招聘方开启下一轮')

onMounted(async () => {
  readUser()
  await loadPlans()
  loadRecommendedJobs()
})

watch(activeTab, loadRecommendedJobs)

function readUser() {
  try {
    username.value = localStorage.getItem('username') || ''
    nickname.value = localStorage.getItem('nickname') || ''
    phone.value = localStorage.getItem('phone') || ''
    email.value = localStorage.getItem('email') || ''
  } catch (_) {
    username.value = ''
    nickname.value = ''
    phone.value = ''
    email.value = ''
  }
}

async function loadPlans() {
  loading.value = true
  error.value = ''
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/plans/my', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '获取面试计划失败')
    }
    plans.value = await res.json()
    ensureDefaultExpanded()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function loadRecommendedJobs() {
  jobLoading.value = true
  try {
    const params = new URLSearchParams({
      page: '1',
      page_size: '5',
      recruitment_type: activeTab.value === 'campus' ? '校招' : '社招',
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

function toggleWorkflow(group) {
  const next = new Set(expandedWorkflows.value)
  if (next.has(group.key)) next.delete(group.key)
  else next.add(group.key)
  expandedWorkflows.value = next
}

function enterInterview(plan = currentPlan.value) {
  if (!plan || !['wait', 'running'].includes(plan.status)) return
  router.push({ path: '/chat', query: { plan_id: plan.id } })
}

function logout() {
  try {
    ;['token', 'username', 'nickname', 'avatar', 'role', 'email', 'phone', 'company', 'bio'].forEach(key => localStorage.removeItem(key))
  } catch (_) {}
  router.push('/')
}

function statusLabel(status) {
  return { wait: '待进入', pending: '等待通知', running: '进行中', finish: '已完成', cancel: '已取消' }[status] || status || '等待通知'
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

function lineClass(plan) {
  if (plan.status === 'finish') return 'bg-[#22c55e]'
  if (['wait', 'running'].includes(plan.status)) return 'bg-[#4776ff]'
  return 'bg-[#ccd4e2]'
}

function nodeClass(plan) {
  if (plan.status === 'finish') return 'bg-[#22c55e] text-white'
  if (plan.status === 'running') return 'bg-[#4776ff] text-white'
  if (plan.status === 'wait') return 'bg-[#11b89f] text-white'
  return 'bg-[#d8deea] text-[#657084]'
}

function groupStatusText(group) {
  if (group.current_plan) return `${group.current_plan.interview_round || '面试'} · ${statusLabel(group.current_plan.status)}`
  if (group.plans.every(plan => plan.status === 'finish')) return '全部完成'
  return '等待通知'
}

function jobSummary(job) {
  const text = `${job.responsibilities || ''}`.replace(/\s+/g, ' ').trim()
  return text || '根据你的投递记录与面试方向，为你推荐相近岗位。'
}
</script>

<template>
  <div class="min-h-screen bg-[linear-gradient(180deg,#f2f5fb_0%,#f8fafc_260px,#f6f7fb_100%)] text-[#202838]">
    <header class="sticky top-0 z-30 border-b border-white/10 bg-[#071c22] text-white shadow-[0_8px_24px_rgba(7,28,34,0.18)]">
      <div class="mx-auto flex h-16 max-w-[1680px] items-center justify-between px-5 lg:px-8">
        <button class="flex items-center gap-3" @click="router.push('/')">
          <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-black text-[#0f9f8f]">AI</span>
          <span class="text-lg font-bold">OPC Mate 招聘</span>
        </button>
        <nav class="hidden items-center gap-8 text-sm font-semibold text-white/80 md:flex">
          <button class="transition hover:text-white" @click="router.push('/')">首页</button>
          <button class="transition hover:text-white" @click="router.push('/jobs/social')">社会招聘</button>
          <button class="transition hover:text-white" @click="router.push('/jobs/campus')">校园招聘</button>
          <button class="transition hover:text-white" @click="router.push('/about')">了解我们</button>
          <button class="relative text-white after:absolute after:-bottom-[22px] after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-[#72f2d1]">个人中心</button>
        </nav>
        <div class="flex items-center gap-3 text-sm font-semibold">
          <button class="rounded-full px-3 py-2 text-white/90 hover:bg-white/10">
            你好，{{ displayName }} <i class="fa fa-angle-down ml-1"></i>
          </button>
          <button class="rounded-full border border-white/15 px-3 py-2 text-white/80 hover:bg-white/10" @click="logout">退出</button>
        </div>
      </div>
    </header>

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
              <div class="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-[#4b6cff] to-[#11b89f] text-3xl font-black text-white shadow-lg shadow-blue-100">
                {{ displayName.slice(0, 1) }}
              </div>
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
            <div class="flex gap-3 text-sm">
              <button class="font-semibold text-[#344054] hover:text-[#11b89f]"><i class="fa fa-eye mr-1"></i> 查看简历</button>
              <button class="font-semibold text-[#344054] hover:text-[#11b89f]"><i class="fa fa-pencil mr-1"></i> 编辑</button>
            </div>
          </div>
          <div class="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.9fr)]">
            <div class="flex min-h-[190px] gap-6 rounded-2xl bg-[#f2f6fb] p-6 lg:p-7">
              <div class="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-[#2f80ff] to-[#11b89f] text-lg font-black text-white shadow-sm">PDF</div>
              <div class="min-w-0 flex-1">
                <div class="truncate text-xl font-black lg:text-2xl">{{ resumeFileName }}</div>
                <div class="mt-3 text-sm text-[#667085]">绑定岗位：{{ activeGroup?.jd_name || '暂未绑定岗位' }}</div>
                <div class="mt-8">
                  <div class="mb-2 flex items-center justify-between text-sm">
                    <span class="font-semibold text-[#475467]">岗位匹配</span>
                    <span class="font-black text-[#11b89f]">{{ resumeMatchPercent }}%</span>
                  </div>
                  <div class="h-3 overflow-hidden rounded-full bg-[#dbe3ef]">
                    <div class="h-full rounded-full bg-[#11b89f]" :style="{ width: `${resumeMatchPercent}%` }"></div>
                  </div>
                </div>
              </div>
            </div>
            <div class="grid grid-cols-3 gap-3 lg:gap-4">
              <div class="flex min-h-[190px] flex-col items-center justify-center rounded-2xl bg-[#f7f9fc] p-4 text-center">
                <div class="text-3xl font-black text-[#4776ff]">{{ applicationCount }}</div>
                <div class="mt-1 text-sm text-[#667085]">投递岗位</div>
              </div>
              <div class="flex min-h-[190px] flex-col items-center justify-center rounded-2xl bg-[#f7f9fc] p-4 text-center">
                <div class="text-3xl font-black text-[#11b89f]">{{ closedWorkflowCount }}</div>
                <div class="mt-1 text-sm text-[#667085]">结束流程</div>
              </div>
              <div class="flex min-h-[190px] flex-col items-center justify-center rounded-2xl bg-[#f7f9fc] p-4 text-center">
                <div class="text-3xl font-black text-[#f59e0b]">{{ activeInterviewCount }}</div>
                <div class="mt-1 text-sm text-[#667085]">进行中</div>
              </div>
            </div>
          </div>
        </div>

        <div class="rounded-2xl bg-white p-7 shadow-[0_16px_42px_rgba(15,35,80,0.08)]">
          <div class="mb-7 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 class="text-2xl font-black">投递记录 - {{ filteredWorkflowGroups.length }} 条</h2>
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
              </button>
            </div>
          </div>

          <div v-if="loading" class="rounded-xl bg-[#f7f9fc] p-10 text-center text-[#667085]">正在加载你的面试安排...</div>
          <div v-else-if="error" class="rounded-xl border border-red-200 bg-red-50 p-8 text-center text-red-600">
            {{ error }}
            <button class="ml-3 font-bold underline" @click="loadPlans">重试</button>
          </div>
          <div v-else-if="filteredWorkflowGroups.length" class="space-y-4">
            <article
              v-for="group in filteredWorkflowGroups"
              :key="group.key"
              class="overflow-hidden rounded-xl border border-[#e8edf5] bg-[#f8fbff]"
            >
              <button class="flex w-full items-center justify-between gap-5 px-5 py-5 text-left" @click="toggleWorkflow(group)">
                <div class="flex min-w-0 items-center gap-4">
                  <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#2f80ff] text-white">
                    <i class="fa fa-bar-chart"></i>
                  </div>
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-3">
                      <h3 class="truncate text-2xl font-black">{{ group.jd_name }}</h3>
                      <span class="rounded-full px-3 py-1 text-sm font-bold" :class="statusPillClass(group.latest_status)">{{ groupStatusText(group) }}</span>
                    </div>
                    <div class="mt-2 text-sm text-[#667085]">
                      {{ group.workflow_name }} ｜ 已完成 {{ group.finished_count }}/{{ group.plans.length }} ｜ {{ group.location || '地点待定' }}
                    </div>
                  </div>
                </div>
                <i class="fa text-xl text-[#667085]" :class="isExpanded(group) ? 'fa-angle-up' : 'fa-angle-down'"></i>
              </button>

              <div class="overflow-x-auto border-t border-[#e8edf5] bg-[#f8fbff] px-5 py-4 pb-5">
                <div class="flex min-w-[680px] items-start">
                  <template v-for="(plan, index) in group.plans" :key="`summary-${plan.id}`">
                    <div class="flex w-[128px] shrink-0 flex-col items-center text-center">
                      <div class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-black" :class="nodeClass(plan)">
                        <i v-if="plan.status === 'finish'" class="fa fa-check"></i>
                        <span v-else>{{ plan.stage_order || index + 1 }}</span>
                      </div>
                      <div class="mt-2 font-bold" :class="['wait', 'running'].includes(plan.status) ? 'text-[#246bdb]' : plan.status === 'finish' ? 'text-[#15a05f]' : 'text-[#667085]'">
                        {{ plan.interview_round }}
                      </div>
                      <div class="mt-1 text-xs text-[#8a94a6]">{{ statusLabel(plan.status) }}</div>
                    </div>
                    <div v-if="index < group.plans.length - 1" class="mx-2 mt-4 h-0.5 min-w-8 flex-1 rounded-full" :class="lineClass(plan)"></div>
                  </template>
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
                      <tr v-for="plan in group.plans" :key="plan.id">
                        <td class="px-4 py-3 font-semibold">{{ plan.interview_round }}</td>
                        <td class="px-4 py-3 text-[#475467]">{{ plan.interviewer || 'AI 面试官' }}</td>
                        <td class="px-4 py-3 text-[#667085]">{{ plan.scheduled_at || '待安排' }}</td>
                        <td class="px-4 py-3"><span class="rounded-full px-3 py-1 text-xs font-bold" :class="statusPillClass(plan.status)">{{ statusLabel(plan.status) }}</span></td>
                        <td class="px-4 py-3">
                          <button v-if="['wait', 'running'].includes(plan.status)" class="font-bold text-[#1677ff] hover:text-[#0958d9]" @click.stop="enterInterview(plan)">进入面试</button>
                          <span v-else class="text-[#98a2b3]">等待</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
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
          <div class="border-l-4 border-[#11b89f] pl-4 text-xl font-black">当前可操作岗位</div>
          <div class="mt-7 flex items-center gap-4">
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#2f80ff] text-white">
              <i class="fa fa-bar-chart text-2xl"></i>
            </div>
            <div class="min-w-0">
              <div class="truncate text-2xl font-black">{{ activeGroup?.jd_name || '暂无可操作岗位' }}</div>
              <div class="mt-2 inline-flex rounded-lg bg-[#e8f2ff] px-3 py-1 text-sm font-bold text-[#246bdb]">{{ currentPlan ? groupStatusText(activeGroup) : '等待通知' }}</div>
            </div>
          </div>
          <div class="mt-7 space-y-3 text-sm text-[#667085]">
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
          <button v-else class="mt-7 w-full cursor-not-allowed rounded-xl bg-[#eef1f6] px-5 py-4 font-black text-[#98a2b3]">等待通知</button>
        </div>

        <div class="rounded-2xl bg-white p-6 shadow-[0_16px_42px_rgba(15,35,80,0.08)]">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-black">智能职位推荐</h2>
            <button class="text-sm font-bold text-[#4b6cff]" @click="router.push('/jobs/social')">全部职位 &gt;</button>
          </div>
          <div v-if="jobLoading" class="mt-5 rounded-xl bg-[#f8fbff] p-5 text-center text-sm text-[#667085]">正在推荐...</div>
          <div v-else class="mt-5 space-y-5">
            <div v-for="job in recommendedJobs" :key="job.id" class="border-b border-[#edf1f7] pb-5 last:border-b-0 last:pb-0">
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

        <div class="rounded-2xl bg-white p-6 text-center shadow-[0_16px_42px_rgba(15,35,80,0.08)]">
          <h2 class="text-xl font-black">我的收藏</h2>
          <p class="mt-5 text-[#667085]">还是空的，快去看看岗位吧</p>
          <button class="mt-4 font-bold text-[#4b6cff]" @click="router.push('/jobs/social')">查看岗位 &gt;</button>
        </div>
      </aside>
    </main>
  </div>
</template>
