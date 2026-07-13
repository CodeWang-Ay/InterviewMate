<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(true)
const plans = ref([])
const error = ref('')

const currentPlan = computed(() => plans.value.find(p => ['wait', 'running'].includes(p.status)) || null)
const workflowName = computed(() => plans.value[0]?.workflow_name || '我的面试流程')

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
    if (currentPlan.value) {
      router.replace({ path: '/chat', query: { plan_id: currentPlan.value.id } })
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function statusLabel(status) {
  return { wait: '待开始', pending: '待前序完成', running: '面试中', finish: '已完成', cancel: '已取消' }[status] || status
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
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-6">
    <div class="w-full max-w-4xl">
      <div class="text-center mb-8">
        <div class="w-14 h-14 bg-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">AI</div>
        <h1 class="text-3xl font-bold text-white">候选人面试入口</h1>
        <p class="text-slate-400 mt-2">系统会自动进入你当前可参加的面试</p>
      </div>

      <div v-if="loading" class="rounded-2xl border border-slate-700 bg-slate-900/70 p-10 text-center text-slate-300">
        <span class="inline-block w-5 h-5 border-2 border-slate-500 border-t-white rounded-full animate-spin mr-2 align-middle"></span>
        正在加载你的面试安排...
      </div>

      <div v-else-if="error" class="rounded-2xl border border-red-500/30 bg-red-500/10 p-8 text-center">
        <p class="text-red-200">{{ error }}</p>
        <button class="mt-4 px-4 py-2 rounded-lg bg-red-500 text-white text-sm hover:bg-red-400" @click="loadPlans">重试</button>
      </div>

      <div v-else-if="plans.length" class="rounded-2xl border border-slate-700 bg-slate-900/70 shadow-2xl overflow-hidden">
        <div class="px-6 py-5 border-b border-slate-700 flex items-center justify-between">
          <div>
            <h2 class="text-xl font-bold text-white">{{ workflowName }}</h2>
            <p class="text-sm text-slate-400 mt-1">{{ plans[0].candidate_name }} · {{ plans[0].jd_name }}</p>
          </div>
          <span class="px-3 py-1 rounded-full bg-slate-800 text-slate-300 text-xs">{{ plans.length }} 个环节</span>
        </div>

        <div class="p-6">
          <div class="flex items-center gap-3 overflow-x-auto pb-2">
            <template v-for="(plan, index) in plans" :key="plan.id">
              <div class="min-w-[180px] rounded-xl border p-4" :class="statusClass(plan.status)">
                <div class="text-xs opacity-80">第 {{ plan.stage_order || index + 1 }}/{{ plan.stage_count || plans.length }} 环节</div>
                <div class="text-base font-semibold mt-2">{{ plan.interview_round }}</div>
                <div class="text-xs mt-3">{{ statusLabel(plan.status) }}</div>
              </div>
              <i v-if="index < plans.length - 1" class="fa fa-long-arrow-right text-slate-600"></i>
            </template>
          </div>

          <div class="mt-6 rounded-xl border border-slate-700 bg-slate-800/70 p-5 text-center text-slate-300">
            当前没有可开始的面试。请等待招聘方开启下一环节。
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
