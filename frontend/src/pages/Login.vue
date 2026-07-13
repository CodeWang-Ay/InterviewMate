<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const isCandidateLogin = computed(() => route.path === '/user/login')

onMounted(() => {
  username.value = String(route.query.username || '')
})

async function doLogin() {
  if (!username.value.trim() || !password.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value.trim(), password: password.value }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '登录失败')
    }
    const data = await res.json()
    localStorage.setItem('token', data.token)
    localStorage.setItem('username', data.username)
    localStorage.setItem('nickname', data.nickname)
    if (data.avatar) localStorage.setItem('avatar', data.avatar)
    localStorage.setItem('role', data.role || 'user')
    router.push(route.query.redirect || (isCandidateLogin.value ? '/user' : '/'))
  } catch (e) {
    error.value = e.message
  }
  loading.value = false
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="w-14 h-14 bg-[#1677ff] rounded-2xl flex items-center justify-center mx-auto mb-4">
          <span class="text-white font-bold text-2xl">AI</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">{{ isCandidateLogin ? '候选人面试入口' : 'AI 面试助手' }}</h1>
        <p class="text-gray-500 mt-1">{{ isCandidateLogin ? '登录后将自动进入你的面试' : '登录你的账号' }}</p>
      </div>

      <!-- Login Card -->
      <div class="bg-white rounded-2xl shadow-lg p-8">
        <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg">{{ error }}</div>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input
              v-model="username"
              type="text"
              placeholder="请输入用户名"
              class="w-full border rounded-lg px-4 py-3 focus:outline-none focus:border-[#1677ff] text-sm"
              @keydown.enter="doLogin"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              v-model="password"
              type="password"
              placeholder="请输入密码"
              class="w-full border rounded-lg px-4 py-3 focus:outline-none focus:border-[#1677ff] text-sm"
              @keydown.enter="doLogin"
            >
          </div>
        </div>

        <button
          :disabled="!username.trim() || !password || loading"
          class="w-full bg-[#1677ff] text-white py-3 rounded-lg font-medium mt-6 hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
          @click="doLogin"
        >
          {{ loading ? '登录中...' : '登 录' }}
        </button>

        <p class="text-center text-sm text-gray-500 mt-5">
          还没有账号？
          <router-link to="/register" class="text-[#1677ff] hover:underline font-medium">立即注册</router-link>
        </p>
      </div>

      <p class="text-center text-xs text-gray-400 mt-6">
        <router-link to="/" class="hover:text-gray-600">返回首页</router-link>
      </p>
    </div>
  </div>
</template>
