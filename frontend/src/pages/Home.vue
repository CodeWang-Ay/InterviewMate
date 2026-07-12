<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const sidebarItems = [
  { icon: 'fa-home', label: '首页', path: '/' },
  { icon: 'fa-file-text', label: '岗位 JD 管理', path: '/interviewee' },
  { icon: 'fa-id-card-o', label: '简历管理', path: '/interviewee' },
  { icon: 'fa-list-alt', label: '面试计划管理', path: '/interviewee' },
  { icon: 'fa-book', label: '题库中心', path: '/' },
  { icon: 'fa-clipboard', label: '面试记录', path: '/interview-record' },
  { icon: 'fa-bar-chart', label: '面试报告', path: '/report' },
  { icon: 'fa-cog', label: '设置', path: '/' },
]

function isActive(path) {
  return route.path === path
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-white">
    <!-- 左侧侧边栏 -->
    <aside class="w-[220px] bg-[#f7f8fa] flex flex-col p-4 flex-shrink-0">
      <!-- Logo -->
      <router-link to="/" class="flex items-center gap-2 mb-8 no-underline">
        <div class="w-9 h-9 bg-[#1677ff] rounded-lg flex items-center justify-center text-white font-bold text-lg">AI</div>
        <span class="text-lg font-semibold text-gray-800">AI 面试助手</span>
      </router-link>

      <!-- 导航菜单 -->
      <nav class="flex-1 space-y-1">
        <router-link
          v-for="item in sidebarItems"
          :key="item.label"
          :to="item.path"
          :class="[
            'flex items-center gap-3 px-3 py-2.5 rounded-lg transition no-underline',
            isActive(item.path)
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

    <!-- 主内容区域 -->
    <main class="flex-1 overflow-auto flex flex-col items-center justify-center p-8 bg-white">
      <div class="text-center mb-10">
        <h1 class="text-[42px] font-bold text-gray-900 mb-3">欢迎使用 AI 面试助手</h1>
        <p class="text-xl text-gray-500">选择你的使用模式，开始你的面试之旅</p>
      </div>

      <!-- 两个功能卡片 -->
      <div class="flex gap-8 flex-wrap justify-center">
        <!-- 卡片1：我是面试者 -->
        <div class="w-[380px] bg-white rounded-xl border border-gray-200 shadow-sm p-8 flex flex-col items-center">
          <div class="w-[100px] h-[100px] rounded-full bg-blue-50 flex items-center justify-center mb-4">
            <img class="w-[70px]" src="https://ui-avatars.com/api/?name=面试者&background=e6f0ff&color=1677ff&size=120" alt="面试者">
          </div>
          <h2 class="text-[26px] font-bold text-gray-900 mb-3">我是面试者</h2>
          <p class="text-gray-500 text-center mb-6 leading-relaxed">
            模拟真实面试场景，AI面试官提问，帮助你提升面试能力
          </p>
          <ul class="w-full space-y-3 mb-8">
            <li class="flex items-center gap-2 text-gray-600">
              <i class="fa fa-check text-[#1677ff]"></i>
              <span>AI 模拟面试</span>
            </li>
            <li class="flex items-center gap-2 text-gray-600">
              <i class="fa fa-check text-[#1677ff]"></i>
              <span>多轮对话问答</span>
            </li>
            <li class="flex items-center gap-2 text-gray-600">
              <i class="fa fa-check text-[#1677ff]"></i>
              <span>智能评分反馈</span>
            </li>
            <li class="flex items-center gap-2 text-gray-600">
              <i class="fa fa-check text-[#1677ff]"></i>
              <span>个性化提升建议</span>
            </li>
          </ul>
          <router-link
            to="/interviewee"
            class="w-full bg-[#1677ff] text-white py-3 rounded-lg text-lg font-medium hover:bg-blue-600 transition flex items-center justify-center gap-2 no-underline"
          >
            开始模拟面试 <i class="fa fa-arrow-right"></i>
          </router-link>
        </div>

        <!-- 卡片2：我是面试官 -->
        <div class="w-[380px] bg-white rounded-xl border border-gray-200 shadow-sm p-8 flex flex-col items-center">
          <div class="w-[100px] h-[100px] rounded-full bg-green-50 flex items-center justify-center mb-4">
            <img class="w-[70px]" src="https://ui-avatars.com/api/?name=面试官&background=e6f9ef&color=22c55e&size=120" alt="面试官">
          </div>
          <h2 class="text-[26px] font-bold text-gray-900 mb-3">我是面试官</h2>
          <p class="text-gray-500 text-center mb-6 leading-relaxed">
            根据JD与简历自动生成面试计划，智能生成问题，记录并总结候选人
          </p>
          <ul class="w-full space-y-3 mb-8">
            <li class="flex items-center gap-2 text-gray-600">
              <i class="fa fa-check text-[#22c55e]"></i>
              <span>岗位&简历匹配分析</span>
            </li>
            <li class="flex items-center gap-2 text-gray-600">
              <i class="fa fa-check text-[#22c55e]"></i>
              <span>自动生成面试计划</span>
            </li>
            <li class="flex items-center gap-2 text-gray-600">
              <i class="fa fa-check text-[#22c55e]"></i>
              <span>面试记录与评分</span>
            </li>
            <li class="flex items-center gap-2 text-gray-600">
              <i class="fa fa-check text-[#22c55e]"></i>
              <span>个性化评估报告</span>
            </li>
          </ul>
          <router-link
            to="/interviewer"
            class="w-full bg-[#22c55e] text-white py-3 rounded-lg text-lg font-medium hover:bg-green-600 transition flex items-center justify-center gap-2 no-underline"
          >
            创建面试任务 <i class="fa fa-arrow-right"></i>
          </router-link>
        </div>
      </div>
    </main>
  </div>
</template>
