<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const open = ref(false)
const loading = ref(false)
const items = ref([])
const unread = ref(0)

async function loadNotifications() {
  loading.value = true
  try {
    const res = await fetch('/api/notifications', { cache: 'no-store' })
    if (!res.ok) return
    const data = await res.json()
    items.value = data.items || []
    unread.value = Number(data.unread || 0)
  } finally { loading.value = false }
}

async function toggle() {
  open.value = !open.value
  if (open.value) await loadNotifications()
}

async function openItem(item) {
  if (!item.is_read) {
    await fetch(`/api/notifications/${item.id}/read`, { method: 'POST' })
    item.is_read = 1
    unread.value = Math.max(0, unread.value - 1)
  }
  open.value = false
  router.push(item.target_url || '/user')
}

async function readAll() {
  await fetch('/api/notifications/read-all', { method: 'POST' })
  items.value = items.value.map(item => ({ ...item, is_read: 1 }))
  unread.value = 0
}

function typeClass(type) {
  return { screening: 'bg-sky-50 text-sky-600', interview: 'bg-indigo-50 text-indigo-600', reminder: 'bg-amber-50 text-amber-600', offer: 'bg-violet-50 text-violet-600' }[type] || 'bg-slate-50 text-slate-600'
}

function typeIcon(type) {
  return { screening: 'fa-file-text-o', interview: 'fa-comments-o', reminder: 'fa-clock-o', offer: 'fa-envelope-o' }[type] || 'fa-bell-o'
}

onMounted(loadNotifications)
</script>

<template>
  <div class="relative">
    <button class="relative flex h-9 w-9 items-center justify-center rounded-full text-white/85 transition hover:bg-white/10" title="消息通知" @click.stop="toggle">
      <i class="fa fa-bell-o"></i>
      <span v-if="unread" class="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-[#ff6b57] px-1 text-[10px] font-black text-white">{{ unread > 99 ? '99+' : unread }}</span>
    </button>
    <div v-if="open" class="absolute right-0 top-12 z-50 w-[390px] max-w-[calc(100vw-24px)] overflow-hidden rounded-2xl border border-[#e4e8f0] bg-white text-[#202838] shadow-[0_24px_70px_rgba(15,35,80,0.22)]" @click.stop>
      <div class="flex items-center justify-between border-b border-[#edf1f7] px-5 py-4"><div><div class="font-black">消息中心</div><div class="mt-0.5 text-xs text-[#8a94a6]">招聘流程的重要变化都在这里</div></div><button v-if="unread" class="text-xs font-bold text-[#0f9f8f]" @click="readAll">全部已读</button></div>
      <div class="max-h-[460px] overflow-y-auto p-2">
        <button v-for="item in items" :key="item.id" class="flex w-full gap-3 rounded-xl p-3 text-left transition hover:bg-[#f7f9fc]" :class="item.is_read ? '' : 'bg-[#f3fbf9]'" @click="openItem(item)">
          <span :class="['mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl', typeClass(item.type)]"><i :class="['fa', typeIcon(item.type)]"></i></span>
          <span class="min-w-0 flex-1"><span class="flex items-start gap-2"><strong class="line-clamp-1 flex-1 text-sm">{{ item.title }}</strong><i v-if="!item.is_read" class="fa fa-circle mt-1 text-[7px] text-[#11b89f]"></i></span><span class="mt-1 line-clamp-2 block text-xs leading-5 text-[#667085]">{{ item.content }}</span><span class="mt-1 block text-[11px] text-[#a0a8b8]">{{ String(item.created_at).replace('T', ' ').slice(0, 16) }}</span></span>
        </button>
        <div v-if="loading" class="p-8 text-center text-sm text-[#8a94a6]">正在加载通知...</div>
        <div v-else-if="!items.length" class="p-10 text-center text-sm text-[#8a94a6]"><i class="fa fa-bell-slash-o mb-3 block text-2xl text-[#c7ceda]"></i>暂无新消息</div>
      </div>
    </div>
  </div>
</template>
