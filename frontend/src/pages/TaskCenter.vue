<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Sidebar from '../components/Sidebar.vue'

const tasks = ref([])
const loading = ref(true)
const timer = ref(null)

const runningCount = computed(() => tasks.value.filter(task => ['queued', 'running'].includes(task.status)).length)
const successCount = computed(() => tasks.value.filter(task => task.status === 'success').length)
const failedCount = computed(() => tasks.value.filter(task => task.status === 'failed').length)

async function fetchTasks() {
  try {
    const res = await fetch('/api/tasks?limit=50')
    if (res.ok) tasks.value = await res.json()
  } catch (_) {
    // ignore
  } finally {
    loading.value = false
  }
}

function statusText(status) {
  return {
    queued: '排队中',
    running: '处理中',
    success: '已完成',
    failed: '失败',
  }[status] || status
}

function statusClass(status) {
  return {
    queued: 'bg-slate-100 text-slate-600',
    running: 'bg-blue-50 text-blue-600',
    success: 'bg-green-50 text-green-600',
    failed: 'bg-red-50 text-red-600',
  }[status] || 'bg-gray-100 text-gray-500'
}

function resultSummary(task) {
  const result = task.result || {}
  if (result.name) return result.name
  if (result.status === 'ok') return result.cache_hit ? '使用解析缓存完成' : '处理完成'
  if (result.optimized) return '已生成优化建议'
  return task.message || '-'
}

onMounted(() => {
  fetchTasks()
  timer.value = window.setInterval(fetchTasks, 3000)
})

onUnmounted(() => {
  if (timer.value) window.clearInterval(timer.value)
})
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-gray-50">
    <Sidebar />
    <main class="flex-1 overflow-auto p-6">
      <div class="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">任务状态中心</h2>
          <p class="mt-1 text-sm text-gray-500">集中查看简历解析、JD 生成、JD 优化等耗时任务的处理进度。</p>
        </div>
        <button class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600 hover:bg-gray-50" @click="fetchTasks">
          <i class="fa fa-refresh mr-1"></i>刷新
        </button>
      </div>

      <div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div class="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
          <div class="text-sm text-gray-500">处理中</div>
          <div class="mt-2 text-3xl font-bold text-blue-600">{{ runningCount }}</div>
        </div>
        <div class="rounded-2xl border border-green-100 bg-white p-5 shadow-sm">
          <div class="text-sm text-gray-500">已完成</div>
          <div class="mt-2 text-3xl font-bold text-green-600">{{ successCount }}</div>
        </div>
        <div class="rounded-2xl border border-red-100 bg-white p-5 shadow-sm">
          <div class="text-sm text-gray-500">失败</div>
          <div class="mt-2 text-3xl font-bold text-red-500">{{ failedCount }}</div>
        </div>
      </div>

      <div class="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-100">
        <div v-if="loading" class="py-16 text-center text-gray-400">
          <i class="fa fa-spinner fa-spin mb-2 block text-2xl"></i>加载任务中...
        </div>
        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-5 py-3 text-left text-sm font-medium text-gray-500">任务</th>
              <th class="px-5 py-3 text-left text-sm font-medium text-gray-500">类型</th>
              <th class="px-5 py-3 text-left text-sm font-medium text-gray-500">进度</th>
              <th class="px-5 py-3 text-left text-sm font-medium text-gray-500">状态</th>
              <th class="px-5 py-3 text-left text-sm font-medium text-gray-500">结果</th>
              <th class="px-5 py-3 text-left text-sm font-medium text-gray-500">更新时间</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="task in tasks" :key="task.id" class="hover:bg-gray-50">
              <td class="px-5 py-4">
                <div class="font-medium text-gray-900">{{ task.title }}</div>
                <div class="mt-1 font-mono text-xs text-gray-400">{{ task.id }}</div>
              </td>
              <td class="px-5 py-4 text-sm text-gray-600">{{ task.task_type }}</td>
              <td class="px-5 py-4">
                <div class="h-2 w-40 overflow-hidden rounded-full bg-gray-100">
                  <div class="h-full rounded-full bg-[#1677ff]" :style="{ width: `${task.progress || 0}%` }"></div>
                </div>
                <div class="mt-1 text-xs text-gray-400">{{ task.progress || 0 }}%</div>
              </td>
              <td class="px-5 py-4"><span :class="['rounded-full px-2.5 py-1 text-xs font-medium', statusClass(task.status)]">{{ statusText(task.status) }}</span></td>
              <td class="max-w-sm px-5 py-4 text-sm text-gray-600">
                <div class="line-clamp-2">{{ task.error || resultSummary(task) }}</div>
              </td>
              <td class="px-5 py-4 text-sm text-gray-500">{{ String(task.updated_at || '').replace('T', ' ').slice(0, 19) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !tasks.length" class="py-16 text-center text-gray-400">暂无后台任务</div>
      </div>
    </main>
  </div>
</template>
