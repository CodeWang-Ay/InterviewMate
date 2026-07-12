<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const history = ref([])
const loading = ref(true)
const chatBox = ref(null)

onMounted(async () => {
  const sid = route.query.session_id
  if (!sid) { loading.value = false; return }
  try {
    const res = await fetch(`/api/report/${sid}`)
    if (res.ok) {
      const data = await res.json()
      history.value = data.history || []
    }
  } catch (_) { /* ignore */ }
  loading.value = false
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
    <!-- 固定大小的聊天记录卡片 -->
    <div class="w-full max-w-5xl h-[85vh] bg-slate-900/60 backdrop-blur-sm border border-slate-700/50 rounded-2xl shadow-2xl flex flex-col overflow-hidden">

      <!-- Header (固定) -->
      <header class="flex-shrink-0 border-b border-slate-700/50 px-5 py-3 flex items-center gap-3 bg-slate-800/30 rounded-t-2xl">
        <router-link to="/" class="text-slate-400 hover:text-white transition-colors">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
        </router-link>
        <div class="flex-1">
          <h1 class="text-white font-semibold text-sm">面试记录</h1>
          <p class="text-slate-500 text-xs">完整对话回顾</p>
        </div>
        <span class="text-slate-500 text-xs">{{ history.length }} 条消息</span>
      </header>

      <!-- Messages (可滚动) -->
      <div ref="chatBox" class="flex-1 overflow-y-auto px-4 py-4">
        <!-- Loading -->
        <div v-if="loading" class="flex items-center justify-center h-full">
          <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <!-- Empty -->
        <div v-else-if="!history.length" class="flex items-center justify-center h-full">
          <p class="text-slate-500">暂无面试记录</p>
        </div>
        <!-- Messages -->
        <div v-else class="space-y-3">
          <div
            v-for="(msg, i) in history"
            :key="i"
            :class="['flex', msg.role === 'candidate' ? 'justify-end' : 'justify-start']"
          >
            <div v-if="msg.role === 'interviewer'" class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mr-2 mt-1">
              <span class="text-white text-xs font-bold">官</span>
            </div>
            <div
              :class="[
                'rounded-2xl px-4 py-2.5 max-w-[70%] text-sm leading-relaxed whitespace-pre-wrap',
                msg.role === 'interviewer'
                  ? 'bg-slate-700/80 text-slate-200 rounded-tl-sm'
                  : 'bg-emerald-600 text-white rounded-tr-sm'
              ]"
            >
              {{ msg.content }}
            </div>
            <div v-if="msg.role === 'candidate'" class="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0 ml-2 mt-1">
              <span class="text-white text-xs font-bold">我</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer (固定) -->
      <footer class="flex-shrink-0 border-t border-slate-700/50 px-4 py-3 bg-slate-800/30 rounded-b-2xl">
        <div class="text-center">
          <router-link
            :to="{ path: '/report', query: { session_id: route.query.session_id } }"
            class="text-blue-400 hover:text-blue-300 text-sm transition-colors"
          >
            查看面试报告
          </router-link>
          <span class="text-slate-600 mx-2">·</span>
          <router-link to="/" class="text-slate-500 hover:text-slate-300 text-sm transition-colors">
            返回首页
          </router-link>
        </div>
      </footer>
    </div>
  </div>
</template>
