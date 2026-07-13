<script setup>
import Sidebar from '../components/Sidebar.vue'
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-white">
    <Sidebar />

    <!-- 主内容区域 -->
    <main class="flex-1 overflow-auto flex flex-col items-center justify-center p-8 bg-white">
      <div class="text-center mb-10">
        <h1 class="text-[42px] font-bold text-gray-900 mb-3">欢迎使用 AI 面试助手</h1>
        <p class="text-xl text-gray-500">选择你的使用模式，开始你的面试之旅</p>
      </div>

      <div class="flex gap-8 flex-wrap justify-center">
        <!-- 我是面试者 -->
        <div class="w-[380px] bg-white rounded-xl border border-gray-200 shadow-sm p-8 flex flex-col items-center">
          <div class="w-[100px] h-[100px] rounded-full bg-blue-50 flex items-center justify-center mb-4">
            <img class="w-[70px]" src="https://ui-avatars.com/api/?name=面试者&background=e6f0ff&color=1677ff&size=120" alt="面试者">
          </div>
          <h2 class="text-[26px] font-bold text-gray-900 mb-3">我是面试者</h2>
          <p class="text-gray-500 text-center mb-6 leading-relaxed">模拟真实面试场景，AI面试官提问，帮助你提升面试能力</p>
          <ul class="w-full space-y-3 mb-8">
            <li class="flex items-center gap-2 text-gray-600"><i class="fa fa-check text-[#1677ff]"></i><span>AI 模拟面试</span></li>
            <li class="flex items-center gap-2 text-gray-600"><i class="fa fa-check text-[#1677ff]"></i><span>多轮对话问答</span></li>
            <li class="flex items-center gap-2 text-gray-600"><i class="fa fa-check text-[#1677ff]"></i><span>智能评分反馈</span></li>
            <li class="flex items-center gap-2 text-gray-600"><i class="fa fa-check text-[#1677ff]"></i><span>个性化提升建议</span></li>
          </ul>
          <router-link to="/interviewee" class="w-full bg-[#1677ff] text-white py-3 rounded-lg text-lg font-medium hover:bg-blue-600 transition flex items-center justify-center gap-2 no-underline">
            开始模拟面试 <i class="fa fa-arrow-right"></i>
          </router-link>
        </div>

        <!-- 我是面试官 -->
        <div class="w-[380px] bg-white rounded-xl border border-gray-200 shadow-sm p-8 flex flex-col items-center">
          <div class="w-[100px] h-[100px] rounded-full bg-green-50 flex items-center justify-center mb-4">
            <img class="w-[70px]" src="https://ui-avatars.com/api/?name=面试官&background=e6f9ef&color=22c55e&size=120" alt="面试官">
          </div>
          <h2 class="text-[26px] font-bold text-gray-900 mb-3">面试官训练台</h2>
          <p class="text-gray-500 text-center mb-6 leading-relaxed">从 JD 库和简历库里拉一组训练组合，让 AI 扮演候选人，帮你练提问、追问和控场</p>
          <ul class="w-full space-y-3 mb-8">
            <li class="flex items-center gap-2 text-gray-600"><i class="fa fa-check text-[#22c55e]"></i><span>岗位&简历匹配分析</span></li>
            <li class="flex items-center gap-2 text-gray-600"><i class="fa fa-check text-[#22c55e]"></i><span>模拟不同候选人状态</span></li>
            <li class="flex items-center gap-2 text-gray-600"><i class="fa fa-check text-[#22c55e]"></i><span>训练追问与项目深挖</span></li>
            <li class="flex items-center gap-2 text-gray-600"><i class="fa fa-check text-[#22c55e]"></i><span>自动生成训练复盘报告</span></li>
          </ul>
          <router-link to="/interviewer" class="w-full bg-[#22c55e] text-white py-3 rounded-lg text-lg font-medium hover:bg-green-600 transition flex items-center justify-center gap-2 no-underline">
            开始训练 <i class="fa fa-arrow-right"></i>
          </router-link>
        </div>
      </div>
    </main>
  </div>
</template>
