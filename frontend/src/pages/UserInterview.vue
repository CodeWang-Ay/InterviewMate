<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(true)
const plans = ref([])
const error = ref('')
const expandedWorkflows = ref(new Set())

const workflowGroups = computed(() => {
  const map = new Map()
  plans.value.forEach(plan => {
    const key = workflowKey(plan)
    if (!map.has(key)) {
      map.set(key, {
        key,
        workflow_id: plan.workflow_id || '',
        workflow_name: plan.workflow_name || '我的面试流程',
        candidate_name: plan.candidate_name || '候选人',
        jd_name: plan.jd_name || '目标岗位',
        plans: [],
      })
    }
    map.get(key).plans.push(plan)
  })
  return Array.from(map.values()).map(group => {
    const sortedPlans = [...group.plans].sort((a, b) => Number(a.stage_order || 1) - Number(b.stage_order || 1))
    const current = sortedPlans.find(p => ['wait', 'running'].includes(p.status)) || null
    const finished = sortedPlans.filter(p => p.status === 'finish').length
    return {
      ...group,
      plans: sortedPlans,
      current_plan: current,
      finished_count: finished,
      progress_percent: sortedPlans.length ? Math.round((finished / sortedPlans.length) * 100) : 0,
    }
  })
})
const currentPlan = computed(() => workflowGroups.value.find(group => group.current_plan)?.current_plan || null)
const activeGroup = computed(() => workflowGroups.value.find(group => group.current_plan) || workflowGroups.value[0] || null)
const currentActionText = computed(() => {
  if (!currentPlan.value) return ''
  return currentPlan.value.status === 'running' ? '继续本轮面试' : '进入本轮面试'
})

onMounted(loadPlans)

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

function workflowKey(plan) {
  return plan.workflow_id || `single:${plan.candidate_username || ''}:${plan.jd_name || ''}:${plan.id || ''}`
}

function ensureDefaultExpanded() {
  const group = workflowGroups.value.find(item => item.current_plan) || workflowGroups.value[0]
  if (!group) return
  expandedWorkflows.value = new Set([group.key])
}

function isExpanded(group) {
  return expandedWorkflows.value.has(group.key)
}

function toggleWorkflow(group) {
  const next = new Set(expandedWorkflows.value)
  if (next.has(group.key)) {
    next.delete(group.key)
  } else {
    next.add(group.key)
  }
  expandedWorkflows.value = next
}

function enterInterview(plan = currentPlan.value) {
  if (!plan) return
  router.push({ path: '/chat', query: { plan_id: plan.id } })
}

function statusLabel(status) {
  return { wait: '待开始', pending: '等待通知', running: '面试中', finish: '已完成', cancel: '已取消' }[status] || status
}

function statusClass(status) {
  return {
    wait: 'border-blue-500/30 bg-blue-500/10 text-blue-200',
    pending: 'border-slate-600 bg-slate-800/70 text-slate-400',
    running: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
    finish: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
    cancel: 'border-red-500/30 bg-red-500/10 text-red-200',
  }[status] || 'border-slate-600 bg-slate-800/70 text-slate-400'
}

function cardTitle(plan) {
  if (plan.status === 'finish') return '本轮已完成'
  if (plan.status === 'running') return '当前轮次进行中'
  if (plan.status === 'wait') return '当前可进入轮次'
  if (plan.status === 'pending') return hasFinishedBefore(plan) ? '等待招聘方评估并开启' : '等待前序轮次完成'
  return '当前轮次已关闭'
}

function hasFinishedBefore(plan) {
  const order = Number(plan.stage_order || 1)
  return plans.value.some(item => Number(item.stage_order || 1) < order && item.status === 'finish')
}

function groupActionText(group) {
  if (!group.current_plan) return ''
  return group.current_plan.status === 'running' ? '继续本轮面试' : '进入本轮面试'
}

function groupStatusText(group) {
  if (group.current_plan) return `${group.current_plan.interview_round || '面试'} · ${statusLabel(group.current_plan.status)}`
  if (group.plans.every(plan => plan.status === 'finish')) return '全部完成'
  return '等待通知'
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6 lg:p-10">
    <div class="mx-auto w-full max-w-7xl">
      <div class="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div>
          <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-600 text-2xl font-bold text-white shadow-xl shadow-emerald-900/30">AI</div>
          <h1 class="text-4xl font-bold tracking-tight text-white">候选人面试入口</h1>
          <p class="mt-3 text-base text-slate-400">查看你的投递流程与面试进度，点击当前开放轮次即可进入。</p>
        </div>
        <div v-if="activeGroup" class="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-5 py-4 text-right">
          <div class="text-sm text-emerald-200">当前流程</div>
          <div class="mt-1 text-xl font-bold text-white">{{ activeGroup.jd_name }}</div>
          <div class="mt-1 text-sm text-slate-300">{{ groupStatusText(activeGroup) }}</div>
        </div>
      </div>

      <div v-if="loading" class="rounded-2xl border border-slate-700 bg-slate-900/70 p-10 text-center text-slate-300">
        <span class="inline-block w-5 h-5 border-2 border-slate-500 border-t-white rounded-full animate-spin mr-2 align-middle"></span>
        正在加载你的面试安排...
      </div>

      <div v-else-if="error" class="rounded-2xl border border-red-500/30 bg-red-500/10 p-8 text-center">
        <p class="text-red-200">{{ error }}</p>
        <button class="mt-4 px-4 py-2 rounded-lg bg-red-500 text-white text-sm hover:bg-red-400" @click="loadPlans">重试</button>
      </div>

      <div v-else-if="workflowGroups.length" class="space-y-5">
        <div
          v-for="group in workflowGroups"
          :key="group.key"
          class="overflow-hidden rounded-[28px] border border-slate-700 bg-slate-900/75 shadow-2xl shadow-slate-950/40"
        >
          <button
            class="flex w-full items-center justify-between gap-5 px-7 py-6 text-left transition hover:bg-slate-800/45"
            @click="toggleWorkflow(group)"
          >
            <div class="flex min-w-0 items-center gap-5">
              <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-950/30">
                <i class="fa fa-bar-chart text-xl"></i>
              </div>
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-3">
                  <h2 class="truncate text-2xl font-bold text-white">{{ group.jd_name }}</h2>
                  <span class="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">{{ group.workflow_name }}</span>
                  <span class="rounded-full px-3 py-1 text-xs" :class="group.current_plan ? 'bg-emerald-500/15 text-emerald-200' : 'bg-slate-700 text-slate-300'">
                    {{ groupStatusText(group) }}
                  </span>
                </div>
                <p class="mt-2 truncate text-sm text-slate-400">
                  {{ group.candidate_name }} · {{ group.finished_count }}/{{ group.plans.length }} 已完成 · 完成度 {{ group.progress_percent }}%
                </p>
              </div>
            </div>
            <div class="flex shrink-0 items-center gap-4">
              <div class="hidden w-44 sm:block">
                <div class="h-2 overflow-hidden rounded-full bg-slate-700">
                  <div class="h-full bg-emerald-500 transition-all duration-500" :style="{ width: `${group.progress_percent}%` }"></div>
                </div>
              </div>
              <i class="fa text-slate-400 transition" :class="isExpanded(group) ? 'fa-angle-up' : 'fa-angle-down'"></i>
            </div>
          </button>

          <div v-show="isExpanded(group)" class="border-t border-slate-700 px-7 py-7">
            <div class="mb-6 rounded-2xl border border-slate-700 bg-slate-800/60 p-6">
              <div class="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div class="text-sm text-slate-400">面试进度</div>
                  <div class="mt-1 text-3xl font-bold text-white">{{ group.finished_count }}/{{ group.plans.length }}</div>
                </div>
                <div class="text-right">
                  <div class="text-sm text-slate-400">完成度</div>
                  <div class="mt-1 text-3xl font-bold text-emerald-300">{{ group.progress_percent }}%</div>
                </div>
              </div>
              <div class="mt-5 h-3 w-full overflow-hidden rounded-full bg-slate-700">
                <div class="h-full bg-emerald-500 transition-all duration-500" :style="{ width: `${group.progress_percent}%` }"></div>
              </div>
            </div>

            <div class="flex items-stretch gap-3 overflow-x-auto pb-3">
              <template v-for="(plan, index) in group.plans" :key="plan.id">
                <div class="min-h-[150px] min-w-[250px] rounded-2xl border p-5" :class="statusClass(plan.status)">
                  <div class="text-xs opacity-80">第 {{ plan.stage_order || index + 1 }}/{{ plan.stage_count || group.plans.length }} 环节</div>
                  <div class="mt-3 text-xl font-semibold">{{ plan.interview_round }}</div>
                  <div class="mt-4 text-sm">{{ statusLabel(plan.status) }}</div>
                  <div class="mt-2 text-sm opacity-80">{{ cardTitle(plan) }}</div>
                </div>
                <div v-if="index < group.plans.length - 1" class="flex items-center text-slate-600">
                  <i class="fa fa-long-arrow-right text-lg"></i>
                </div>
              </template>
            </div>

            <div v-if="group.current_plan" class="mt-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-6">
              <div class="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div class="text-sm text-emerald-200">当前可操作环节</div>
                  <div class="mt-2 text-2xl font-bold text-white">{{ group.current_plan.interview_round }}</div>
                  <p class="mt-3 text-base text-slate-300">
                    {{ group.current_plan.status === 'running' ? '你可以返回继续完成当前面试。' : '当前轮次已经开放，点击即可正式进入面试。' }}
                  </p>
                </div>
                <button
                  class="rounded-xl bg-emerald-500 px-7 py-4 font-semibold text-slate-950 shadow-lg shadow-emerald-950/30 transition hover:bg-emerald-400"
                  @click="enterInterview(group.current_plan)"
                >
                  {{ groupActionText(group) }}
                </button>
              </div>
            </div>

            <div v-else class="mt-5 rounded-xl border border-slate-700 bg-slate-800/70 p-5 text-center text-slate-300">
              <div class="text-base font-semibold text-white">当前暂无可进入的面试</div>
              <p class="mt-2 text-sm text-slate-400">你的上一轮面试已进入后台评估流程。若通过，招聘方会发起下一轮面试，你将在这里看到入口。</p>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="rounded-2xl border border-slate-700 bg-slate-900/70 p-10 text-center">
        <h2 class="text-xl font-bold text-white">暂无面试安排</h2>
        <p class="text-slate-400 mt-2">请确认你使用的是招聘方提供的候选人账号。</p>
      </div>
    </div>
  </div>
</template>
