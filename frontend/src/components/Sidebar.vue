<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

function getStore(key, fallback = '') {
  try { return localStorage.getItem(key) || fallback } catch (_) { return fallback }
}

const nickname = ref(getStore('nickname', '用户'))
const avatarUrl = ref(getStore('avatar', ''))
const role = ref(getStore('role', 'user'))
if (!avatarUrl.value) {
  avatarUrl.value = `https://ui-avatars.com/api/?name=${encodeURIComponent(nickname.value)}&background=1677ff&color=fff`
}

function doLogout() {
  localStorage.clear()
  router.push('/login')
}

const navItems = [
  { icon: 'fa-home', label: '首页', path: '/' },
  { icon: 'fa-comments-o', label: '面试官训练台', path: '/interviewer' },
  { icon: 'fa-file-text', label: '岗位 JD 管理', path: '/jd-manager' },
  { icon: 'fa-id-card-o', label: '简历管理', path: '/resume-manager' },
  { icon: 'fa-magic', label: 'AI 辅助中心', path: '/ai-tools' },
  { icon: 'fa-list-alt', label: '面试计划管理', path: '/plan-manager' },
  { icon: 'fa-archive', label: '面试档案', path: '/interview-archive', adminOnly: true },
  { icon: 'fa-cog', label: '设置', path: '/settings' },
]

const visibleNavItems = navItems.filter((item) => !item.adminOnly || role.value === 'admin')
</script>

<template>
  <aside class="w-[220px] bg-[#f7f8fa] flex flex-col p-4 flex-shrink-0 h-screen">
    <!-- Logo -->
    <router-link to="/" class="flex items-center gap-2 mb-8 no-underline">
      <div class="w-9 h-9 bg-[#1677ff] rounded-lg flex items-center justify-center text-white font-bold text-lg">AI</div>
      <span class="text-lg font-semibold text-gray-800">AI 面试助手</span>
    </router-link>

    <!-- 导航菜单 -->
    <nav class="flex-1 space-y-1">
      <router-link
        v-for="item in visibleNavItems"
        :key="item.label"
        :to="item.path"
        :class="[
          'flex items-center gap-3 px-3 py-2.5 rounded-lg transition no-underline',
          route.path === item.path
            ? 'bg-blue-50 text-[#1677ff]'
            : 'text-gray-600 hover:bg-gray-200'
        ]"
      >
        <i :class="['fa', item.icon, 'text-lg w-5 text-center']"></i>
        <span class="text-sm">{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- 底部用户信息 -->
    <div class="mt-auto pt-4 border-t border-gray-200">
      <router-link to="/user-center" class="flex items-center gap-3 hover:bg-gray-100 rounded-lg p-2 -mx-2 transition cursor-pointer no-underline">
        <img :src="avatarUrl" alt="avatar" class="w-10 h-10 rounded-full flex-shrink-0">
        <div class="flex-1">
          <div class="font-medium text-gray-800 text-sm">{{ nickname }}</div>
          <div class="text-xs text-gray-500">专业版</div>
        </div>
      </router-link>
      <button type="button" class="mt-2 w-full text-left text-xs text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors flex items-center gap-2 px-2 py-1.5 cursor-pointer" @click="doLogout">
        <i class="fa fa-sign-out"></i> 退出登录
      </button>
    </div>
  </aside>
</template>
