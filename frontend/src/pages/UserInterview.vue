<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(true)
const plans = ref([])
const error = ref('')
const expandedWorkflows = ref(new Set())
const activeMenu = ref('overview')
const menus = [
  { key: 'overview', label: '公司概览', icon: 'fa-building-o' },
  { key: 'resume', label: '我的简历', icon: 'fa-file-text-o' },
  { key: 'jobs', label: '投递岗位', icon: 'fa-briefcase' },
  { key: 'progress', label: '面试进度', icon: 'fa-check-circle-o' },
  { key: 'message', label: '消息', icon: 'fa-bell-o' },
  { key: 'settings', label: '设置', icon: 'fa-cog' },
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
const allPlanCount = computed(() => plans.value.length)
const allFinishedCount = computed(() => plans.value.filter(plan => plan.status === 'finish').length)
const resumeFileName = computed(() => activeGroup.value?.plans.find(plan => plan.resume_filename)?.resume_filename || '')
const resumeMatchPercent = computed(() => {
  const score = activeGroup.value?.current_plan?.match_score || activeGroup.value?.plans.find(plan => plan.match_score)?.match_score || 0
  return score ? Math.min(Math.max(Number(score), 0), 100) : 85
})
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
  <div class="min-h-screen bg-[#061024] text-slate-100">
    <div class="grid min-h-screen lg:grid-cols-[280px_1fr]">
      <aside class="border-r border-white/10 bg-[#07142a]/95 p-5 lg:sticky lg:top-0 lg:h-screen">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-xl shadow-blue-950/40">
          <div class="flex items-end gap-1">
            <span class="h-7 w-2 rounded bg-blue-400"></span>
            <span class="h-10 w-2 rounded bg-blue-500"></span>
            <span class="h-5 w-2 rounded bg-cyan-400"></span>
          </div>
        </div>

        <nav class="mt-8 space-y-2">
          <button
            v-for="item in menus"
            :key="item.key"
            class="flex w-full items-center gap-4 rounded-xl px-4 py-4 text-left text-base font-semibold transition"
            :class="activeMenu === item.key ? 'bg-emerald-500/20 text-emerald-300 shadow-lg shadow-emerald-950/20' : 'text-slate-300 hover:bg-white/5 hover:text-white'"
            @click="activeMenu = item.key"
          >
            <i class="fa w-6 text-center text-xl" :class="item.icon"></i>
            <span>{{ item.label }}</span>
            <span v-if="item.key === 'message'" class="ml-auto rounded-full bg-red-500 px-2 py-0.5 text-xs text-white">2</span>
          </button>
        </nav>

        <div class="mt-10 border-t border-white/10 pt-5 lg:absolute lg:bottom-6 lg:left-5 lg:right-5">
          <div class="flex items-center gap-3">
            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-emerald-400 font-bold text-slate-950">
              {{ (activeGroup?.candidate_name || '候').slice(0, 1) }}
            </div>
            <div class="min-w-0">
              <div class="truncate font-bold text-white">{{ activeGroup?.candidate_name || '候选人' }}</div>
              <div class="truncate text-xs text-slate-400">candidate account</div>
            </div>
            <i class="fa fa-angle-down ml-auto text-slate-500"></i>
          </div>
        </div>
      </aside>

      <main class="min-w-0 p-6 lg:p-8 xl:p-10">
        <div class="mx-auto max-w-[1540px]">
          <div class="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 class="text-4xl font-bold tracking-tight text-white">候选人面试中心</h1>
              <p class="mt-3 text-base text-slate-400">查看你的简历、投递岗位与面试进度</p>
            </div>
            <button class="rounded-xl border border-white/10 px-5 py-3 text-sm font-semibold text-slate-200 hover:bg-white/5">
              招聘方入口 <i class="fa fa-external-link ml-2"></i>
            </button>
          </div>

          <div v-if="loading" class="rounded-2xl border border-white/10 bg-white/[0.04] p-10 text-center text-slate-300">
            <span class="mr-2 inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-500 border-t-white align-middle"></span>
            正在加载你的面试安排...
          </div>

          <div v-else-if="error" class="rounded-2xl border border-red-500/30 bg-red-500/10 p-8 text-center">
            <p class="text-red-200">{{ error }}</p>
            <button class="mt-4 rounded-lg bg-red-500 px-4 py-2 text-sm text-white hover:bg-red-400" @click="loadPlans">重试</button>
          </div>

          <div v-else-if="workflowGroups.length" class="grid gap-6 xl:grid-cols-[1fr_380px]">
            <section class="min-w-0 space-y-6">
              <div class="rounded-2xl border border-white/10 bg-white/[0.045] p-6 shadow-2xl shadow-blue-950/20">
                <h2 class="text-2xl font-bold text-white">我的简历</h2>
                <div class="mt-5 grid gap-6 xl:grid-cols-[420px_1fr]">
                  <div class="flex gap-5">
                    <div class="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 text-lg font-bold text-white shadow-lg shadow-blue-950/40">
                      PDF
                    </div>
                    <div class="min-w-0">
                      <div class="break-all text-xl font-bold text-white">{{ resumeFileName || '暂未绑定简历文件' }}</div>
                      <div class="mt-2 text-sm text-slate-400">绑定候选人：{{ activeGroup?.candidate_name || '-' }}</div>
                      <div class="mt-6">
                        <div class="mb-2 flex items-center justify-between text-sm">
                          <span class="text-slate-300">匹配度</span>
                          <span class="font-bold text-emerald-300">{{ resumeMatchPercent }}%</span>
                        </div>
                        <div class="h-2.5 overflow-hidden rounded-full bg-slate-700">
                          <div class="h-full rounded-full bg-emerald-400" :style="{ width: `${resumeMatchPercent}%` }"></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
                    <div class="space-y-3 text-sm">
                      <div class="flex items-center gap-3">
                        <i class="fa fa-id-card-o w-5 text-slate-400"></i>
                        <span class="w-20 text-slate-400">当前岗位</span>
                        <span class="truncate text-slate-100">{{ activeGroup?.jd_name || '-' }}</span>
                      </div>
                      <div class="flex items-center gap-3">
                        <i class="fa fa-briefcase w-5 text-slate-400"></i>
                        <span class="w-20 text-slate-400">投递流程</span>
                        <span class="text-slate-100">{{ workflowGroups.length }} 个</span>
                      </div>
                      <div class="flex items-center gap-3">
                        <i class="fa fa-clock-o w-5 text-slate-400"></i>
                        <span class="w-20 text-slate-400">面试环节</span>
                        <span class="text-slate-100">{{ allPlanCount }} 个</span>
                      </div>
                    </div>
                    <div>
                      <div class="mb-3 font-bold text-white">核心技能</div>
                      <div class="flex flex-wrap gap-2">
                        <span v-for="skill in ['AI 面试', '岗位匹配', '简历解析', '语音问答', '面试报告', '流程追踪']" :key="skill" class="rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-200">
                          {{ skill }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h2 class="text-2xl font-bold text-white">该公司投递岗位</h2>
                <p class="mt-1 text-slate-400">你在当前招聘流程中的岗位及面试进度</p>
              </div>

              <div class="space-y-4">
                <div
                  v-for="group in workflowGroups"
                  :key="group.key"
                  class="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.045] shadow-xl shadow-blue-950/10"
                >
                  <button class="flex w-full items-center justify-between gap-5 px-5 py-5 text-left hover:bg-white/[0.035]" @click="toggleWorkflow(group)">
                    <div class="flex min-w-0 items-center gap-4">
                      <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white">
                        <i class="fa fa-bar-chart"></i>
                      </div>
                      <div class="min-w-0">
                        <div class="flex flex-wrap items-center gap-3">
                          <h3 class="truncate text-2xl font-bold text-white">{{ group.jd_name }}</h3>
                          <span class="rounded-lg bg-blue-500/15 px-3 py-1 text-sm text-blue-300">{{ groupStatusText(group) }}</span>
                        </div>
                        <div class="mt-2 text-sm text-slate-400">{{ group.workflow_name }} · 已完成 {{ group.finished_count }}/{{ group.plans.length }}</div>
                      </div>
                    </div>
                    <i class="fa text-xl text-slate-400" :class="isExpanded(group) ? 'fa-angle-up' : 'fa-angle-down'"></i>
                  </button>

                  <div v-show="isExpanded(group)" class="border-t border-white/10 p-5">
                    <div class="rounded-xl border border-white/10 bg-[#0b1831]/80 p-5">
                      <div class="mb-5 font-bold text-white">面试进度</div>
                      <div class="flex min-w-full items-start gap-3 overflow-x-auto pb-4">
                        <template v-for="(plan, index) in group.plans" :key="plan.id">
                          <div class="flex min-w-[130px] flex-col items-center text-center">
                            <div class="flex h-9 w-9 items-center justify-center rounded-full font-bold" :class="plan.status === 'finish' ? 'bg-emerald-400 text-slate-950' : plan.status === 'running' ? 'bg-blue-500 text-white' : plan.status === 'wait' ? 'bg-amber-400 text-slate-950' : 'bg-slate-600 text-slate-200'">
                              <i v-if="plan.status === 'finish'" class="fa fa-check"></i>
                              <span v-else>{{ plan.stage_order || index + 1 }}</span>
                            </div>
                            <div class="mt-2 font-semibold" :class="plan.status === 'finish' ? 'text-emerald-300' : plan.status === 'running' ? 'text-blue-300' : 'text-slate-300'">{{ plan.interview_round }}</div>
                            <div class="mt-1 text-xs text-slate-500">{{ statusLabel(plan.status) }}</div>
                          </div>
                          <div v-if="index < group.plans.length - 1" class="mt-4 h-px min-w-[80px] flex-1 bg-slate-700"></div>
                        </template>
                      </div>

                      <div class="mt-2 overflow-hidden rounded-xl border border-white/10">
                        <table class="w-full text-left text-sm">
                          <thead class="bg-white/[0.035] text-slate-400">
                            <tr>
                              <th class="px-4 py-3 font-medium">环节</th>
                              <th class="px-4 py-3 font-medium">面试官 / 方式</th>
                              <th class="px-4 py-3 font-medium">时间</th>
                              <th class="px-4 py-3 font-medium">状态</th>
                              <th class="px-4 py-3 font-medium">操作</th>
                            </tr>
                          </thead>
                          <tbody class="divide-y divide-white/10">
                            <tr v-for="plan in group.plans" :key="plan.id">
                              <td class="px-4 py-3 text-white">{{ plan.interview_round }}</td>
                              <td class="px-4 py-3 text-slate-300">{{ plan.interviewer || 'AI 面试官' }}</td>
                              <td class="px-4 py-3 text-slate-400">{{ plan.scheduled_at || '-' }}</td>
                              <td class="px-4 py-3" :class="plan.status === 'finish' ? 'text-emerald-300' : plan.status === 'running' ? 'text-blue-300' : 'text-slate-400'">{{ statusLabel(plan.status) }}</td>
                              <td class="px-4 py-3">
                                <button v-if="['wait', 'running'].includes(plan.status)" class="text-blue-300 hover:text-blue-200" @click.stop="enterInterview(plan)">进入面试</button>
                                <span v-else class="text-slate-500">-</span>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <aside class="space-y-5">
              <div class="rounded-2xl border border-white/10 bg-emerald-500/10 p-6 shadow-2xl shadow-emerald-950/20">
                <div class="border-l-4 border-emerald-400 pl-4 text-xl font-bold text-white">当前可操作岗位</div>
                <div class="mt-8 flex items-center gap-4">
                  <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-600 text-white">
                    <i class="fa fa-bar-chart text-2xl"></i>
                  </div>
                  <div>
                    <div class="text-2xl font-bold text-white">{{ activeGroup?.jd_name || '-' }}</div>
                    <div class="mt-2 rounded-lg bg-blue-500/20 px-3 py-1 text-sm text-blue-300">{{ currentPlan ? groupStatusText(activeGroup) : '等待通知' }}</div>
                  </div>
                </div>
                <div class="mt-8 space-y-3 text-sm text-slate-300">
                  <div><i class="fa fa-info-circle mr-2 text-slate-500"></i>下一环节：{{ currentPlan?.interview_round || '等待招聘方通知' }}</div>
                  <div><i class="fa fa-clock-o mr-2 text-slate-500"></i>面试时间：{{ currentPlan?.scheduled_at || '暂未设置' }}</div>
                </div>
                <button
                  v-if="currentPlan"
                  class="mt-7 w-full rounded-xl bg-emerald-500 px-5 py-4 font-bold text-slate-950 transition hover:bg-emerald-400"
                  @click="enterInterview(currentPlan)"
                >
                  {{ currentActionText }}
                </button>
                <button v-else class="mt-7 w-full cursor-not-allowed rounded-xl bg-slate-700 px-5 py-4 font-bold text-slate-400">等待通知</button>
              </div>

              <div class="rounded-2xl border border-white/10 bg-white/[0.045] p-6">
                <div class="text-xl font-bold text-white">面试信息</div>
                <div class="mt-5 space-y-4 text-sm">
                  <div class="flex justify-between gap-4">
                    <span class="text-slate-400">候选人</span>
                    <span class="font-semibold text-slate-100">{{ activeGroup?.candidate_name || '-' }}</span>
                  </div>
                  <div class="flex justify-between gap-4">
                    <span class="text-slate-400">流程</span>
                    <span class="font-semibold text-slate-100">{{ activeGroup?.workflow_name || '-' }}</span>
                  </div>
                  <div class="flex justify-between gap-4">
                    <span class="text-slate-400">进度</span>
                    <span class="font-semibold text-emerald-300">{{ allFinishedCount }}/{{ allPlanCount }}</span>
                  </div>
                </div>
              </div>

              <div class="rounded-2xl border border-white/10 bg-white/[0.045] p-6">
                <div class="text-xl font-bold text-white">面试小贴士</div>
                <p class="mt-4 text-sm leading-7 text-slate-400">提前了解面试流程，准备好项目经历、技术细节和岗位匹配说明。离开页面后可回到这里继续当前轮次。</p>
                <div class="mt-5 rounded-xl bg-blue-500/10 p-4 text-blue-200">
                  <i class="fa fa-lightbulb-o mr-2"></i>
                  回答时尽量按背景、动作、结果说明。
                </div>
              </div>
            </aside>
          </div>

          <div v-else class="rounded-2xl border border-white/10 bg-white/[0.04] p-10 text-center">
            <h2 class="text-xl font-bold text-white">暂无面试安排</h2>
            <p class="mt-2 text-slate-400">请确认你使用的是招聘方提供的候选人账号。</p>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
