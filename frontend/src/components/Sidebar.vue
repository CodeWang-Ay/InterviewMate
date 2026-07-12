<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { icon: 'fa-home', label: '首页', path: '/' },
  { icon: 'fa-file-text', label: '岗位 JD 管理', path: '/jd-manager' },
  { icon: 'fa-id-card-o', label: '简历管理', path: '/resume-manager' },
  { icon: 'fa-list-alt', label: '面试计划管理', path: '/plan-manager' },
  { icon: 'fa-book', label: '题库中心', path: '/' },
  { icon: 'fa-clipboard', label: '面试记录', path: '/interview-record' },
  { icon: 'fa-bar-chart', label: '面试报告', path: '/report' },
  { icon: 'fa-cog', label: '设置', path: '/' },
]
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
        v-for="item in navItems"
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
      <div class="flex items-center gap-3">
        <img
          src="https://ui-avatars.com/api/?name=用户&background=1677ff&color=fff"
          alt="avatar"
          class="w-10 h-10 rounded-full flex-shrink-0"
        />
        <div>
          <div class="font-medium text-gray-800 text-sm">用户</div>
          <div class="text-xs text-gray-500">专业版</div>
        </div>
      </div>
    </div>
  </aside>
</template>
