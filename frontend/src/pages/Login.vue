<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const isCandidateLogin = computed(() => route.path === '/user/login')
const title = computed(() => isCandidateLogin.value ? '面试者登录界面' : '后台管理员登录界面')
const subtitle = computed(() => isCandidateLogin.value
  ? '使用招聘方提供的候选人账号，查看当前面试进度并进入对应轮次。'
  : '登录招聘管理后台，统一处理岗位、简历、面试流程与候选人档案。')
const roleLabel = computed(() => isCandidateLogin.value ? 'Candidate Access' : 'Admin Console')
const primaryColorClass = computed(() => isCandidateLogin.value ? 'from-emerald-500 to-teal-500' : 'from-sky-600 to-indigo-600')
const buttonClass = computed(() => isCandidateLogin.value ? 'bg-emerald-500 hover:bg-emerald-400 focus:ring-emerald-200' : 'bg-sky-600 hover:bg-sky-500 focus:ring-sky-200')
const inputFocusClass = computed(() => isCandidateLogin.value ? 'focus:border-emerald-400 focus:ring-emerald-100' : 'focus:border-sky-400 focus:ring-sky-100')
const submitLabel = computed(() => loading.value ? '登录中...' : (isCandidateLogin.value ? '进入面试者界面' : '进入后台管理界面'))
const accountLabel = computed(() => isCandidateLogin.value ? '面试者账号' : '管理员账号')
const passwordLabel = computed(() => isCandidateLogin.value ? '面试者密码' : '管理员密码')
const accountPlaceholder = computed(() => isCandidateLogin.value ? '请输入面试者账号' : '请输入管理员账号')
const passwordPlaceholder = computed(() => isCandidateLogin.value ? '请输入面试者密码' : '请输入管理员密码')
const hintItems = computed(() => isCandidateLogin.value
  ? ['确认当前轮次状态', '从断点继续面试', '完成后生成面试记录']
  : ['岗位与简历统一管理', '面试流程分轮推进', '候选人档案集中查看'])
const authPanelTitle = computed(() => isCandidateLogin.value ? '候选人身份验证' : '管理员身份验证')
const authPanelNote = computed(() => isCandidateLogin.value ? '验证通过后将直接进入你的面试空间。' : '验证通过后将恢复你的后台工作台状态。')

onMounted(() => {
  username.value = String(route.query.username || '')
  password.value = String(route.query.password || '')
})

async function doLogin() {
  if (!username.value.trim() || !password.value) return
  loading.value = true
  error.value = ''
  try {
    const endpoint = isCandidateLogin.value ? '/api/auth/candidate-login' : '/api/auth/login'
    const res = await fetch(endpoint, {
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
  <div :class="['min-h-screen flex items-center justify-center p-6 md:p-10 bg-gradient-to-br', isCandidateLogin ? 'from-emerald-50 via-teal-50 to-cyan-100' : 'from-slate-100 via-sky-50 to-indigo-100']">
    <div class="w-full max-w-7xl">
      <div class="grid lg:grid-cols-[0.9fr_1.1fr] overflow-hidden rounded-[34px] border border-white/70 bg-white/85 shadow-[0_32px_100px_rgba(15,23,42,0.14)] backdrop-blur">
        <section class="relative hidden lg:flex flex-col justify-between p-14 xl:p-16 overflow-hidden min-h-[760px]">
          <div :class="['absolute inset-0 opacity-95 bg-gradient-to-br', isCandidateLogin ? 'from-emerald-500 via-teal-500 to-cyan-500' : 'from-slate-800 via-sky-600 to-indigo-500']"></div>
          <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.24),transparent_32%),radial-gradient(circle_at_bottom_left,rgba(255,255,255,0.18),transparent_28%)]"></div>

          <div class="relative z-10">
            <div class="inline-flex items-center gap-4 rounded-[22px] bg-white/14 px-5 py-4 backdrop-blur">
              <div class="w-14 h-14 rounded-[20px] bg-white/18 flex items-center justify-center text-white font-bold text-xl shadow-sm">AI</div>
              <div>
                <div class="text-white font-semibold text-xl">InterviewMate</div>
                <div class="text-white/75 text-sm">{{ roleLabel }}</div>
              </div>
            </div>
          </div>

          <div class="relative z-10 mt-12">
            <div class="inline-flex items-center rounded-full bg-white/14 px-5 py-2 text-sm font-semibold tracking-[0.12em] text-white/90">
              {{ roleLabel }}
            </div>
            <h2 class="mt-6 text-[44px] leading-[1.15] font-bold text-white">{{ title }}</h2>
            <p class="mt-5 max-w-xl text-lg leading-8 text-white/82">{{ subtitle }}</p>
          </div>

          <div class="relative z-10 grid gap-4 mt-12">
            <div
              v-for="item in hintItems"
              :key="item"
              class="flex items-center gap-4 rounded-[22px] bg-white/12 px-5 py-4 text-white/92 backdrop-blur"
            >
              <span class="w-7 h-7 rounded-full bg-white/18 flex items-center justify-center text-sm">•</span>
              <span class="text-base font-medium">{{ item }}</span>
            </div>
          </div>
        </section>

        <section class="p-8 sm:p-10 lg:p-12 xl:p-14 2xl:px-16">
          <div class="flex items-start justify-end">
            <div
              v-if="!isCandidateLogin"
              class="inline-flex rounded-[22px] border border-slate-200 bg-slate-100/80 p-1.5 shadow-sm"
            >
              <router-link
                to="/login"
                :class="[
                  'inline-flex items-center gap-2 rounded-[16px] px-4 py-2.5 text-sm font-semibold no-underline transition-all whitespace-nowrap',
                  'bg-white text-slate-900 shadow-sm'
                ]"
              >
                <span class="w-7 h-7 rounded-lg flex items-center justify-center bg-blue-50 text-sky-600 shadow-sm">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
                    <rect x="4" y="5" width="16" height="14" rx="2"></rect>
                    <path d="M8 9h8M8 13h5"></path>
                  </svg>
                </span>
                管理员
              </router-link>
              <router-link
                to="/user/login"
                class="inline-flex items-center gap-2 rounded-[16px] px-4 py-2.5 text-sm font-semibold no-underline transition-all whitespace-nowrap text-slate-500 hover:text-slate-700"
              >
                <span class="w-7 h-7 rounded-lg flex items-center justify-center bg-white/80 text-slate-400 shadow-sm">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
                    <circle cx="12" cy="8" r="3"></circle>
                    <path d="M6.5 18a5.5 5.5 0 0 1 11 0"></path>
                  </svg>
                </span>
                面试者
              </router-link>
            </div>
          </div>

          <div class="mt-10 w-full max-w-[700px] rounded-[30px] border border-slate-200/80 bg-white p-6 sm:p-7 shadow-sm">
            <div class="flex items-center gap-4">
              <div :class="['w-14 h-14 rounded-[20px] bg-gradient-to-br flex items-center justify-center text-white text-lg font-bold shadow-sm', primaryColorClass]">
                <svg v-if="isCandidateLogin" class="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
                  <circle cx="12" cy="8" r="3"></circle>
                  <path d="M6.5 18a5.5 5.5 0 0 1 11 0"></path>
                </svg>
                <svg v-else class="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
                  <rect x="4" y="5" width="16" height="14" rx="2"></rect>
                  <path d="M8 9h8M8 13h5"></path>
                </svg>
              </div>
              <div>
                <div class="text-lg font-semibold text-slate-900">{{ authPanelTitle }}</div>
                <div class="text-sm text-slate-500 mt-1">{{ authPanelNote }}</div>
              </div>
            </div>

            <div v-if="error" class="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3.5 text-sm text-red-600">{{ error }}</div>

            <div class="mt-7 space-y-5">
              <div>
                <label class="block text-base font-medium text-slate-700 mb-2.5">{{ accountLabel }}</label>
                <input
                  v-model="username"
                  type="text"
                  :placeholder="accountPlaceholder"
                  :class="['w-full rounded-2xl border border-slate-200 bg-slate-50/70 px-5 py-4 text-base text-slate-900 outline-none transition focus:bg-white focus:ring-4', inputFocusClass]"
                  @keydown.enter="doLogin"
                >
              </div>
              <div>
                <label class="block text-base font-medium text-slate-700 mb-2.5">{{ passwordLabel }}</label>
                <div class="relative">
                  <input
                    v-model="password"
                    :type="showPassword ? 'text' : 'password'"
                    :placeholder="passwordPlaceholder"
                    :class="['w-full rounded-2xl border border-slate-200 bg-slate-50/70 px-5 py-4 pr-14 text-base text-slate-900 outline-none transition focus:bg-white focus:ring-4', inputFocusClass]"
                    @keydown.enter="doLogin"
                  >
                  <button
                    type="button"
                    class="absolute inset-y-0 right-3 my-auto h-10 w-10 rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
                    :title="showPassword ? '隐藏密码' : '查看密码'"
                    @click="showPassword = !showPassword"
                  >
                    <svg v-if="showPassword" class="mx-auto w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path d="M3 3l18 18"></path>
                      <path d="M10.6 10.7a2 2 0 0 0 2.8 2.8"></path>
                      <path d="M9.9 5.1A10.9 10.9 0 0 1 12 5c5 0 9.3 3 11 7-0.7 1.7-1.9 3.2-3.4 4.4"></path>
                      <path d="M6.6 6.7C4.8 8 3.5 9.8 3 12c1.7 4 6 7 11 7 1.3 0 2.5-.2 3.6-.6"></path>
                    </svg>
                    <svg v-else class="mx-auto w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <button
              :disabled="!username.trim() || !password || loading"
              :class="['mt-7 w-full rounded-2xl py-4 text-base font-semibold text-white transition focus:outline-none focus:ring-4 disabled:cursor-not-allowed disabled:opacity-50', buttonClass]"
              @click="doLogin"
            >
              {{ submitLabel }}
            </button>

            <div class="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p v-if="!isCandidateLogin" class="text-base text-slate-500">
                还没有账号？
                <router-link to="/register" class="font-medium text-[#1677ff] hover:text-blue-600 no-underline">立即注册</router-link>
              </p>
              <router-link to="/" class="text-base text-slate-400 hover:text-slate-600 no-underline">
                返回首页
              </router-link>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
