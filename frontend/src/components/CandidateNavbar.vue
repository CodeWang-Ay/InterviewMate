<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  active: { type: String, default: '' },
  position: { type: String, default: 'sticky' },
})

const router = useRouter()
const mobileOpen = ref(false)

function storeValue(key) {
  try { return localStorage.getItem(key) || '' } catch (_) { return '' }
}

const username = ref(storeValue('username'))
const nickname = ref(storeValue('nickname'))
const role = ref(storeValue('role'))
const isLoggedIn = computed(() => Boolean(storeValue('token')))
const displayName = computed(() => nickname.value || username.value || '用户')
const centerPath = computed(() => role.value === 'candidate' ? '/user' : '/admin/user-center')

const items = computed(() => [
  { key: 'home', label: '首页', path: '/' },
  { key: 'social', label: '社会招聘', path: '/jobs/social' },
  { key: 'campus', label: '校园招聘', path: '/jobs/campus' },
  { key: 'about', label: '了解我们', path: '/about' },
  ...(isLoggedIn.value ? [{ key: 'center', label: '个人中心', path: centerPath.value }] : []),
])

function navigate(path) {
  mobileOpen.value = false
  router.push(path)
}

async function logout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' })
  } catch (_) {}
  try {
    ;['token', 'username', 'nickname', 'avatar', 'role', 'email', 'phone', 'company', 'bio']
      .forEach(key => localStorage.removeItem(key))
  } catch (_) {}
  username.value = ''
  nickname.value = ''
  role.value = ''
  mobileOpen.value = false
  router.push('/')
}
</script>

<template>
  <header
    class="left-0 right-0 top-0 z-30 border-b border-white/10 bg-[#071c22]/95 text-white shadow-[0_8px_24px_rgba(7,28,34,0.16)] backdrop-blur-xl"
    :class="position === 'fixed' ? 'fixed' : 'sticky'"
  >
    <div class="mx-auto flex h-16 max-w-[1680px] items-center justify-between px-5 lg:px-8">
      <button class="flex items-center gap-3" @click="navigate('/')">
        <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-black text-[#0f9f8f]">AI</span>
        <span class="text-lg font-bold">OPC Mate 招聘</span>
      </button>

      <nav class="hidden h-full items-center gap-8 text-sm font-semibold text-white/80 md:flex">
        <button
          v-for="item in items"
          :key="item.key"
          class="relative flex h-full items-center transition hover:text-white"
          :class="active === item.key ? 'text-white after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-[#72f2d1]' : ''"
          @click="navigate(item.path)"
        >
          {{ item.label }}
        </button>
      </nav>

      <div class="hidden items-center gap-3 text-sm font-semibold md:flex">
        <button
          v-if="isLoggedIn"
          class="rounded-full px-3 py-2 text-white/90 transition hover:bg-white/10"
          @click="navigate(centerPath)"
        >
          你好，{{ displayName }} <i class="fa fa-angle-down ml-1"></i>
        </button>
        <button
          v-if="isLoggedIn"
          class="rounded-full border border-white/15 px-3 py-2 text-white/80 transition hover:bg-white/10"
          @click="logout"
        >
          退出
        </button>
        <button
          v-else
          class="rounded-full border border-white/15 px-4 py-2 text-white/90 transition hover:bg-white/10"
          @click="navigate('/user/login')"
        >
          登录/注册
        </button>
      </div>

      <button class="flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 text-white/90 md:hidden" @click="mobileOpen = !mobileOpen">
        <i :class="['fa', mobileOpen ? 'fa-times' : 'fa-bars']"></i>
      </button>
    </div>

    <div v-if="mobileOpen" class="border-t border-white/10 bg-[#071c22] px-5 py-4 md:hidden">
      <div class="grid gap-1">
        <button
          v-for="item in items"
          :key="`mobile-${item.key}`"
          class="rounded-lg px-3 py-2.5 text-left text-sm font-semibold"
          :class="active === item.key ? 'bg-white/10 text-[#72f2d1]' : 'text-white/80'"
          @click="navigate(item.path)"
        >
          {{ item.label }}
        </button>
        <button v-if="isLoggedIn" class="mt-2 rounded-lg border border-white/10 px-3 py-2.5 text-left text-sm text-white/70" @click="logout">退出登录</button>
        <button v-else class="mt-2 rounded-lg bg-white px-3 py-2.5 text-sm font-bold text-[#0f766e]" @click="navigate('/user/login')">登录/注册</button>
      </div>
    </div>
  </header>
</template>
