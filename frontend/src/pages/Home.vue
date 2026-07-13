<script setup>
import { computed, onMounted, ref } from 'vue'
import Sidebar from '../components/Sidebar.vue'

const loading = ref(true)
const error = ref('')
const nickname = ref('管理员')
const jdStats = ref({
  total: 0,
  enabled: 0,
  disabled: 0,
  categories: 0,
})
const resumes = ref([])
const plans = ref([])
const records = ref([])

const quickLinks = [
  {
    title: '岗位 JD 管理',
    desc: '维护在招岗位、职责要求和启停状态',
    icon: 'fa-file-text-o',
    to: '/jd-manager',
    accent: 'from-[#2f6df6] to-[#78a0ff]',
  },
  {
    title: '简历管理',
    desc: '查看解析结果，补齐候选人画像与技能标签',
    icon: 'fa-id-card-o',
    to: '/resume-manager',
    accent: 'from-[#159d6d] to-[#52d5a3]',
  },
  {
    title: '面试计划管理',
    desc: '按候选人查看一面、二面、HR 面推进状态',
    icon: 'fa-calendar-check-o',
    to: '/plan-manager',
    accent: 'from-[#7a57f6] to-[#b79dff]',
  },
  {
    title: '面试官训练台',
    desc: '用 JD 和简历对练提问、追问与控场',
    icon: 'fa-comments-o',
    to: '/interviewer',
    accent: 'from-[#f59f0b] to-[#f9c15a]',
  },
]

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 19) return '下午好'
  return '晚上好'
})

const todayLabel = computed(() => {
  const date = new Date()
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(date)
})

const resumeStats = computed(() => {
  const total = resumes.value.length
  const parsed = resumes.value.filter(item => item.parse_status === 'success').length
  const waiting = resumes.value.filter(item => item.parse_status === 'wait').length
  const failed = resumes.value.filter(item => item.parse_status === 'fail').length
  return { total, parsed, waiting, failed }
})

const planStats = computed(() => {
  const total = plans.value.length
  const waiting = plans.value.filter(item => item.status === 'wait').length
  const running = plans.value.filter(item => item.status === 'running').length
  const finished = plans.value.filter(item => item.status === 'finish').length
  return { total, waiting, running, finished }
})

const workflowOverview = computed(() => {
  const map = new Map()
  for (const plan of plans.value) {
    const key = plan.workflow_id || `single-${plan.id}`
    if (!map.has(key)) {
      map.set(key, {
        key,
        workflow_name: plan.workflow_name || `${plan.candidate_name || '候选人'} 的面试流程`,
        candidate_name: plan.candidate_name || '未命名候选人',
        jd_name: plan.jd_name || '待定岗位',
        stage_count: plan.stage_count || 1,
        plans: [],
        created_at: plan.created_at || '',
      })
    }
    map.get(key).plans.push(plan)
  }

  return [...map.values()]
    .map(item => {
      const waiting = item.plans.filter(plan => plan.status === 'wait').length
      const running = item.plans.filter(plan => plan.status === 'running').length
      const finished = item.plans.filter(plan => plan.status === 'finish').length
      const pending = item.plans.filter(plan => plan.status === 'pending').length
      return {
        ...item,
        waiting,
        running,
        finished,
        pending,
        progressText: `${finished}/${item.stage_count} 已完成`,
        currentStage: item.plans.find(plan => ['wait', 'running'].includes(plan.status)) || item.plans[0],
      }
    })
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
})

const focusQueue = computed(() => {
  return workflowOverview.value
    .filter(item => item.waiting > 0 || item.running > 0)
    .slice(0, 4)
})

const recentResumes = computed(() => resumes.value.slice(0, 5))
const recentArchive = computed(() => records.value.slice(0, 5))

const topStats = computed(() => [
  {
    label: '在线岗位',
    value: jdStats.value.enabled,
    sub: `共 ${jdStats.value.total} 个 JD`,
    icon: 'fa-briefcase',
    tone: 'text-[#2f6df6]',
    bg: 'bg-[#eaf1ff]',
  },
  {
    label: '简历库',
    value: resumeStats.value.total,
    sub: `${resumeStats.value.parsed} 份已解析`,
    icon: 'fa-folder-open-o',
    tone: 'text-[#16946a]',
    bg: 'bg-[#eaf9f3]',
  },
  {
    label: '待推进流程',
    value: planStats.value.waiting + planStats.value.running,
    sub: `${planStats.value.finished} 个已完成环节`,
    icon: 'fa-random',
    tone: 'text-[#7a57f6]',
    bg: 'bg-[#f2edff]',
  },
  {
    label: '面试档案',
    value: records.value.length,
    sub: '记录与报告已归档',
    icon: 'fa-archive',
    tone: 'text-[#f08a00]',
    bg: 'bg-[#fff3e2]',
  },
])

function statusText(status) {
  if (status === 'wait') return '待发起'
  if (status === 'running') return '进行中'
  if (status === 'finish') return '已完成'
  if (status === 'pending') return '等待前序完成'
  if (status === 'cancel') return '已关闭'
  return status || '未知'
}

function statusClass(status) {
  if (status === 'wait') return 'bg-[#edf4ff] text-[#2f6df6]'
  if (status === 'running') return 'bg-[#ecfdf3] text-[#1f8f61]'
  if (status === 'finish') return 'bg-[#f2edff] text-[#6d4cf5]'
  if (status === 'pending') return 'bg-[#f5f7fb] text-[#7e8ca6]'
  if (status === 'cancel') return 'bg-[#fff1f1] text-[#d05f5f]'
  return 'bg-[#f5f7fb] text-[#7e8ca6]'
}

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    try {
      nickname.value = window.localStorage?.getItem('nickname') || '管理员'
    } catch (_) {
      nickname.value = '管理员'
    }

    const [jdRes, resumeRes, planRes, recordRes] = await Promise.all([
      fetch('/api/jds/stats'),
      fetch('/api/resumes'),
      fetch('/api/plans'),
      fetch('/api/records'),
    ])

    const [jdData, resumeData, planData, recordData] = await Promise.all([
      jdRes.json(),
      resumeRes.json(),
      planRes.json(),
      recordRes.json(),
    ])

    if (!jdRes.ok) throw new Error(jdData.detail || '岗位统计加载失败')
    if (!resumeRes.ok) throw new Error(resumeData.detail || '简历数据加载失败')
    if (!planRes.ok) throw new Error(planData.detail || '计划数据加载失败')
    if (!recordRes.ok) throw new Error(recordData.detail || '档案数据加载失败')

    jdStats.value = jdData || jdStats.value
    resumes.value = Array.isArray(resumeData) ? resumeData : []
    plans.value = Array.isArray(planData) ? planData : []
    records.value = Array.isArray(recordData) ? recordData : []
  } catch (err) {
    error.value = err.message || '首页数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-[#f3f7fd]">
    <Sidebar />

    <main class="flex-1 overflow-y-auto">
      <div class="mx-auto max-w-[1600px] px-7 py-7">
        <section class="overflow-hidden rounded-[30px] border border-[#d7e5fb] bg-white shadow-[0_22px_60px_rgba(80,112,178,0.12)]">
          <div class="grid gap-0 xl:grid-cols-[1.3fr_0.7fr]">
            <div class="bg-[linear-gradient(135deg,#17305f_0%,#2257ca_58%,#7ea4ff_100%)] px-8 py-8 text-white">
              <div class="inline-flex items-center gap-2 rounded-full bg-white/12 px-4 py-2 text-sm font-semibold tracking-[0.08em] text-white/90">
                <span class="h-2.5 w-2.5 rounded-full bg-emerald-300"></span>
                ADMIN WORKSPACE
              </div>

              <div class="mt-8 max-w-3xl">
                <p class="text-sm uppercase tracking-[0.26em] text-white/62">{{ todayLabel }}</p>
                <h1 class="mt-4 text-[40px] font-bold leading-[1.08]">{{ greeting }}，{{ nickname }}</h1>
                <p class="mt-5 max-w-2xl text-[17px] leading-8 text-white/82">
                  这里不是欢迎页了，而是你的招聘工作台。岗位、简历、流程、训练和归档信息都集中在这儿，方便你一进来就知道今天先动哪一步。
                </p>
              </div>

              <div class="mt-8 flex flex-wrap gap-3">
                <router-link to="/plan-manager" class="inline-flex items-center gap-2 rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-[#163166] no-underline shadow-sm transition hover:translate-y-[-1px]">
                  <i class="fa fa-play-circle-o text-[#2f6df6]"></i>
                  进入面试计划管理
                </router-link>
                <router-link to="/interviewer" class="inline-flex items-center gap-2 rounded-2xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white no-underline transition hover:bg-white/16">
                  <i class="fa fa-comments-o"></i>
                  打开面试官训练台
                </router-link>
              </div>
            </div>

            <div class="bg-[#f8fbff] px-8 py-8">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <div class="text-sm font-semibold text-[#3970e9]">Today Focus</div>
                  <h2 class="mt-2 text-[28px] font-bold text-[#18233e]">今天优先处理</h2>
                </div>
                <button class="rounded-full border border-[#d8e4ff] bg-white px-4 py-2 text-sm font-semibold text-[#506079] transition hover:border-[#99b7ff] hover:text-[#2353cf]" @click="loadDashboard">
                  刷新面板
                </button>
              </div>

              <div class="mt-7 space-y-4">
                <div class="rounded-2xl border border-[#deebff] bg-white px-5 py-4">
                  <div class="text-sm font-semibold text-[#1d2941]">待解析简历</div>
                  <div class="mt-2 flex items-end justify-between">
                    <div class="text-[34px] font-bold text-[#18233e]">{{ resumeStats.waiting }}</div>
                    <div class="text-sm text-[#71819d]">失败 {{ resumeStats.failed }} 份</div>
                  </div>
                </div>
                <div class="rounded-2xl border border-[#deebff] bg-white px-5 py-4">
                  <div class="text-sm font-semibold text-[#1d2941]">待推进面试流程</div>
                  <div class="mt-2 flex items-end justify-between">
                    <div class="text-[34px] font-bold text-[#18233e]">{{ planStats.waiting + planStats.running }}</div>
                    <div class="text-sm text-[#71819d]">进行中 {{ planStats.running }} 个</div>
                  </div>
                </div>
                <div class="rounded-2xl border border-[#deebff] bg-white px-5 py-4">
                  <div class="text-sm font-semibold text-[#1d2941]">候选档案沉淀</div>
                  <div class="mt-2 flex items-end justify-between">
                    <div class="text-[34px] font-bold text-[#18233e]">{{ records.length }}</div>
                    <div class="text-sm text-[#71819d]">可回看记录与报告</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div v-if="error" class="mt-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-600">
          {{ error }}
        </div>

        <div class="mt-6 grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
          <section
            v-for="item in topStats"
            :key="item.label"
            class="rounded-[24px] border border-[#dce7fb] bg-white px-5 py-5 shadow-[0_14px_36px_rgba(80,112,178,0.10)]"
          >
            <div class="flex items-center justify-between">
              <div>
                <div class="text-sm font-medium text-[#7b88a3]">{{ item.label }}</div>
                <div class="mt-3 text-[34px] font-bold text-[#18233e]">{{ loading ? '-' : item.value }}</div>
                <div class="mt-2 text-sm text-[#7b88a3]">{{ item.sub }}</div>
              </div>
              <div :class="[item.bg, item.tone]" class="flex h-14 w-14 items-center justify-center rounded-2xl text-[24px]">
                <i :class="['fa', item.icon]"></i>
              </div>
            </div>
          </section>
        </div>

        <div class="mt-6 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <section class="rounded-[28px] border border-[#dce7fb] bg-white px-6 py-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="text-sm font-semibold text-[#3970e9]">Focus Queue</div>
                <h2 class="mt-2 text-[28px] font-bold text-[#18233e]">当前推进中的流程</h2>
              </div>
              <router-link to="/plan-manager" class="text-sm font-semibold text-[#2f6df6] no-underline hover:text-[#184bbd]">查看全部</router-link>
            </div>

            <div v-if="loading" class="py-16 text-center text-[#7b88a3]">
              <div class="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-[#8fb0ff] border-t-transparent"></div>
              <p class="mt-4 text-sm">正在加载流程总览...</p>
            </div>

            <div v-else-if="!focusQueue.length" class="py-16 text-center text-[#7b88a3]">
              <p class="text-base">当前没有待推进的流程</p>
              <p class="mt-2 text-sm">你可以去面试计划管理里新建一条候选人流程。</p>
            </div>

            <div v-else class="mt-6 space-y-4">
              <article
                v-for="item in focusQueue"
                :key="item.key"
                class="rounded-[24px] border border-[#dfebff] bg-[linear-gradient(180deg,#ffffff_0%,#f8fbff_100%)] px-5 py-5"
              >
                <div class="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div class="text-[21px] font-semibold text-[#18233e]">{{ item.candidate_name }}</div>
                    <div class="mt-1 text-sm text-[#6d7b95]">{{ item.jd_name }} · {{ item.progressText }}</div>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <span :class="statusClass(item.currentStage?.status)" class="rounded-full px-3 py-1.5 text-xs font-semibold">
                      {{ statusText(item.currentStage?.status) }}
                    </span>
                    <span class="rounded-full bg-[#f1f5ff] px-3 py-1.5 text-xs font-semibold text-[#5c6f96]">
                      {{ item.currentStage?.interview_round || '当前环节' }}
                    </span>
                  </div>
                </div>

                <div class="mt-4 grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
                  <div>
                    <div class="h-2 overflow-hidden rounded-full bg-[#e7eefb]">
                      <div class="h-full rounded-full bg-[linear-gradient(90deg,#2f6df6_0%,#78a0ff_100%)]" :style="{ width: `${Math.min(100, (item.finished / Math.max(item.stage_count, 1)) * 100)}%` }"></div>
                    </div>
                    <div class="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm text-[#71819d]">
                      <span>已完成 {{ item.finished }}</span>
                      <span>待发起 {{ item.waiting }}</span>
                      <span>待前序 {{ item.pending }}</span>
                    </div>
                  </div>
                  <router-link to="/plan-manager" class="inline-flex items-center gap-2 rounded-2xl border border-[#dbe7ff] bg-white px-4 py-3 text-sm font-semibold text-[#274fb5] no-underline transition hover:border-[#97b4ff]">
                    进入流程
                    <i class="fa fa-angle-right"></i>
                  </router-link>
                </div>
              </article>
            </div>
          </section>

          <section class="rounded-[28px] border border-[#dce7fb] bg-white px-6 py-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="text-sm font-semibold text-[#3970e9]">Quick Entry</div>
                <h2 class="mt-2 text-[28px] font-bold text-[#18233e]">常用模块</h2>
              </div>
            </div>

            <div class="mt-6 grid gap-4 md:grid-cols-2">
              <router-link
                v-for="link in quickLinks"
                :key="link.title"
                :to="link.to"
                class="rounded-[24px] border border-[#dfebff] bg-[#fbfdff] p-5 no-underline transition hover:border-[#9ab8ff] hover:bg-white hover:shadow-[0_16px_34px_rgba(80,112,178,0.10)]"
              >
                <div class="flex items-start justify-between gap-4">
                  <div :class="['flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br text-white text-xl', link.accent]">
                    <i :class="['fa', link.icon]"></i>
                  </div>
                  <i class="fa fa-arrow-right text-[#9aa7bc]"></i>
                </div>
                <h3 class="mt-5 text-[20px] font-semibold text-[#18233e]">{{ link.title }}</h3>
                <p class="mt-2 text-sm leading-7 text-[#6f7e98]">{{ link.desc }}</p>
              </router-link>
            </div>
          </section>
        </div>

        <div class="mt-6 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <section class="rounded-[28px] border border-[#dce7fb] bg-white px-6 py-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="text-sm font-semibold text-[#3970e9]">Resume Feed</div>
                <h2 class="mt-2 text-[28px] font-bold text-[#18233e]">最近简历</h2>
              </div>
              <router-link to="/resume-manager" class="text-sm font-semibold text-[#2f6df6] no-underline hover:text-[#184bbd]">查看全部</router-link>
            </div>

            <div class="mt-6 space-y-3">
              <div
                v-for="item in recentResumes"
                :key="item.id"
                class="flex items-center justify-between gap-4 rounded-2xl border border-[#e0ebff] bg-[#fbfdff] px-4 py-4"
              >
                <div class="min-w-0">
                  <div class="truncate text-base font-semibold text-[#1d2941]">{{ item.name || '未命名简历' }}</div>
                  <div class="mt-1 truncate text-sm text-[#73839d]">{{ item.target_position || '未填写意向岗位' }}</div>
                </div>
                <div class="flex items-center gap-3">
                  <span :class="item.parse_status === 'success' ? 'bg-[#ecfdf3] text-[#1f8f61]' : item.parse_status === 'fail' ? 'bg-[#fff1f1] text-[#d05f5f]' : 'bg-[#edf4ff] text-[#2f6df6]'" class="rounded-full px-3 py-1.5 text-xs font-semibold">
                    {{ item.parse_status === 'success' ? '已解析' : item.parse_status === 'fail' ? '解析失败' : '待解析' }}
                  </span>
                </div>
              </div>
            </div>
          </section>

          <section class="rounded-[28px] border border-[#dce7fb] bg-white px-6 py-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="text-sm font-semibold text-[#3970e9]">Archive Feed</div>
                <h2 class="mt-2 text-[28px] font-bold text-[#18233e]">最近归档</h2>
              </div>
              <router-link to="/interview-archive" class="text-sm font-semibold text-[#2f6df6] no-underline hover:text-[#184bbd]">查看档案</router-link>
            </div>

            <div class="mt-6 space-y-3">
              <div
                v-for="item in recentArchive"
                :key="item.session_id"
                class="grid gap-3 rounded-2xl border border-[#e0ebff] bg-[#fbfdff] px-4 py-4 md:grid-cols-[1fr_auto]"
              >
                <div class="min-w-0">
                  <div class="truncate text-base font-semibold text-[#1d2941]">{{ item.candidate }}</div>
                  <div class="mt-1 truncate text-sm text-[#73839d]">{{ item.position }} · {{ item.type_label }}</div>
                </div>
                <div class="flex items-center gap-3">
                  <span class="rounded-full bg-[#f3f6fc] px-3 py-1.5 text-xs font-semibold text-[#6f7d98]">{{ item.score_display }}</span>
                  <span class="rounded-full bg-[#eef4ff] px-3 py-1.5 text-xs font-semibold text-[#2f6df6]">{{ item.conclusion }}</span>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>
