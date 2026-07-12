<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const nickname = ref('')
const password = ref('')
const password2 = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

async function doRegister() {
  error.value = ''
  if (!username.value.trim() || !password.value) return
  if (password.value !== password2.value) { error.value = '两次密码输入不一致'; return }
  if (password.value.length < 6) { error.value = '密码至少6位'; return }

  loading.value = true
  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value,
        nickname: nickname.value.trim() || username.value.trim(),
      }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '注册失败')
    }
    success.value = true
    setTimeout(() => router.push('/login'), 2000)
  } catch (e) {
    error.value = e.message
  }
  loading.value = false
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="w-14 h-14 bg-[#1677ff] rounded-2xl flex items-center justify-center mx-auto mb-4">
          <span class="text-white font-bold text-2xl">AI</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">创建账号</h1>
        <p class="text-gray-500 mt-1">注册 AI 面试助手</p>
      </div>

      <div class="bg-white rounded-2xl shadow-lg p-8">
        <!-- Success -->
        <div v-if="success" class="text-center py-4">
          <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <i class="fa fa-check text-2xl text-green-500"></i>
          </div>
          <p class="text-lg font-semibold text-gray-900">注册成功！</p>
          <p class="text-sm text-gray-500 mt-1">即将跳转到登录页...</p>
        </div>

        <template v-else>
          <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg">{{ error }}</div>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">用户名 <span class="text-red-500">*</span></label>
              <input v-model="username" type="text" placeholder="至少2个字符" class="w-full border rounded-lg px-4 py-3 focus:outline-none focus:border-[#1677ff] text-sm">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">昵称</label>
              <input v-model="nickname" type="text" placeholder="选填，默认同用户名" class="w-full border rounded-lg px-4 py-3 focus:outline-none focus:border-[#1677ff] text-sm">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">密码 <span class="text-red-500">*</span></label>
              <input v-model="password" type="password" placeholder="至少6位" class="w-full border rounded-lg px-4 py-3 focus:outline-none focus:border-[#1677ff] text-sm">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">确认密码 <span class="text-red-500">*</span></label>
              <input v-model="password2" type="password" placeholder="再次输入密码" class="w-full border rounded-lg px-4 py-3 focus:outline-none focus:border-[#1677ff] text-sm" @keydown.enter="doRegister">
            </div>
          </div>

          <button
            :disabled="!username.trim() || !password || loading"
            class="w-full bg-[#1677ff] text-white py-3 rounded-lg font-medium mt-6 hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
            @click="doRegister"
          >
            {{ loading ? '注册中...' : '注 册' }}
          </button>

          <p class="text-center text-sm text-gray-500 mt-5">
            已有账号？
            <router-link to="/login" class="text-[#1677ff] hover:underline font-medium">立即登录</router-link>
          </p>
        </template>
      </div>

      <p class="text-center text-xs text-gray-400 mt-6">
        <router-link to="/" class="hover:text-gray-600">返回首页</router-link>
      </p>
    </div>
  </div>
</template>
