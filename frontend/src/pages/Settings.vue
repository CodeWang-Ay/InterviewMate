<script setup>
import { ref } from 'vue'
import Sidebar from '../components/Sidebar.vue'

// AI 面试参数
const aiSettings = ref({
  autoFollowUp: true,
  realtimeComment: true,
  autoReport: true,
  asrEnabled: false,
  difficulty: 'normal',
  maxQuestions: 18,
})

// 通知设置
const notifySettings = ref({
  reportEmail: true,
  parseComplete: true,
})

// 账号信息
const account = ref({
  nickname: '用户',
  email: '',
})

function saveAccount() { alert('账号信息已保存') }
function saveAIConfig() { alert('AI配置已保存') }
function resetAIDefault() {
  aiSettings.value = { autoFollowUp: true, realtimeComment: true, autoReport: true, asrEnabled: false, difficulty: 'normal', maxQuestions: 18 }
  alert('已恢复默认配置')
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <h2 class="text-2xl font-bold text-gray-900 mb-6">系统设置</h2>

      <!-- 1. 账号信息 -->
      <div class="bg-white rounded-xl p-6 shadow-sm mb-6">
        <h3 class="text-lg font-semibold border-b pb-3 mb-4">账号基础信息</h3>
        <div class="grid grid-cols-2 gap-y-5 gap-x-8 max-w-[700px]">
          <div>
            <label class="text-gray-500 text-sm block mb-1">昵称</label>
            <input v-model="account.nickname" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
          </div>
          <div>
            <label class="text-gray-500 text-sm block mb-1">手机号</label>
            <input class="w-full border rounded-lg px-3 py-2 bg-gray-50" value="138****8888" disabled>
          </div>
          <div>
            <label class="text-gray-500 text-sm block mb-1">角色权限</label>
            <input class="w-full border rounded-lg px-3 py-2 bg-gray-50" value="面试官（专业版）" disabled>
          </div>
          <div>
            <label class="text-gray-500 text-sm block mb-1">邮箱（接收报告通知）</label>
            <input v-model="account.email" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="zhangsan@xxx.com">
          </div>
        </div>
        <div class="mt-5">
          <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg hover:bg-blue-600 text-sm" @click="saveAccount">保存账号信息</button>
          <button class="border border-gray-300 px-5 py-2 rounded-lg ml-3 hover:bg-gray-50 text-sm">修改密码</button>
        </div>
      </div>

      <!-- 2. AI 面试参数 -->
      <div class="bg-white rounded-xl p-6 shadow-sm mb-6">
        <h3 class="text-lg font-semibold border-b pb-3 mb-4">AI面试全局参数</h3>
        <div class="space-y-5 max-w-[750px]">
          <div class="flex justify-between items-center">
            <div>
              <div class="font-medium text-sm">允许AI自动追问候选人</div>
              <div class="text-xs text-gray-500">候选人回答不完善时，AI主动发起深度追问</div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="aiSettings.autoFollowUp" class="sr-only peer">
              <div class="w-11 h-6 bg-gray-300 peer-checked:bg-[#1677ff] rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>
          <div class="flex justify-between items-center">
            <div>
              <div class="font-medium text-sm">面试中实时AI点评</div>
              <div class="text-xs text-gray-500">面试官侧边栏实时展示候选人回答优缺点提示</div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="aiSettings.realtimeComment" class="sr-only peer">
              <div class="w-11 h-6 bg-gray-300 peer-checked:bg-[#1677ff] rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>
          <div class="flex justify-between items-center">
            <div>
              <div class="font-medium text-sm">面试结束自动生成面试报告</div>
              <div class="text-xs text-gray-500">面试会话结束后自动执行评分与报告生成</div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="aiSettings.autoReport" class="sr-only peer">
              <div class="w-11 h-6 bg-gray-300 peer-checked:bg-[#1677ff] rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>
          <div class="flex justify-between items-center">
            <div>
              <div class="font-medium text-sm">语音转文字（ASR）开启</div>
              <div class="text-xs text-gray-500">支持候选人语音作答，自动转为文本分析</div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="aiSettings.asrEnabled" class="sr-only peer">
              <div class="w-11 h-6 bg-gray-300 peer-checked:bg-[#1677ff] rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>
          <div>
            <label class="text-gray-500 text-sm block mb-1">AI严格程度（面试难度基准）</label>
            <select v-model="aiSettings.difficulty" class="w-full border rounded-lg px-3 py-2 max-w-[360px]">
              <option value="loose">宽松 - 偏鼓励，评分标准较低</option>
              <option value="normal">标准 - 均衡客观评估（推荐）</option>
              <option value="strict">严格 - 高标准筛选候选人</option>
            </select>
          </div>
          <div>
            <label class="text-gray-500 text-sm block mb-1">单次面试最大题目数量上限</label>
            <input v-model.number="aiSettings.maxQuestions" type="number" class="w-full border rounded-lg px-3 py-2 max-w-[360px]">
          </div>
        </div>
        <div class="mt-5">
          <button class="bg-[#1677ff] text-white px-5 py-2 rounded-lg hover:bg-blue-600 text-sm" @click="saveAIConfig">保存AI配置</button>
          <button class="border border-gray-300 px-5 py-2 rounded-lg ml-3 hover:bg-gray-50 text-sm" @click="resetAIDefault">恢复默认配置</button>
        </div>
      </div>

      <!-- 3. 通知设置 -->
      <div class="bg-white rounded-xl p-6 shadow-sm mb-6">
        <h3 class="text-lg font-semibold border-b pb-3 mb-4">消息通知设置</h3>
        <div class="space-y-5 max-w-[750px]">
          <div class="flex justify-between items-center">
            <div>
              <div class="font-medium text-sm">面试报告完成邮件推送</div>
              <div class="text-xs text-gray-500">报告生成完成后发送邮件通知</div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="notifySettings.reportEmail" class="sr-only peer">
              <div class="w-11 h-6 bg-gray-300 peer-checked:bg-[#1677ff] rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>
          <div class="flex justify-between items-center">
            <div>
              <div class="font-medium text-sm">简历解析完成通知</div>
              <div class="text-xs text-gray-500">大批量简历解析完成提醒</div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="notifySettings.parseComplete" class="sr-only peer">
              <div class="w-11 h-6 bg-gray-300 peer-checked:bg-[#1677ff] rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>
        </div>
      </div>

      <!-- 4. 数据管理 -->
      <div class="bg-white rounded-xl p-6 shadow-sm mb-6">
        <h3 class="text-lg font-semibold border-b pb-3 mb-4">数据管理</h3>
        <div class="flex flex-wrap gap-3">
          <button class="border border-[#1677ff] text-[#1677ff] px-4 py-2 rounded-lg hover:bg-blue-50 text-sm">导出全部简历&面试记录</button>
          <button class="border border-yellow-500 text-yellow-500 px-4 py-2 rounded-lg hover:bg-orange-50 text-sm">清理本地缓存文件</button>
          <button class="border border-red-500 text-red-500 px-4 py-2 rounded-lg hover:bg-red-50 text-sm">注销当前账号</button>
        </div>
      </div>

      <!-- 5. 关于系统 -->
      <div class="bg-white rounded-xl p-6 shadow-sm mb-6">
        <h3 class="text-lg font-semibold border-b pb-3 mb-4">关于AI面试助手</h3>
        <p class="text-gray-600 text-sm">当前版本：V1.0.0</p>
        <p class="text-gray-500 text-xs mt-2">专为招聘面试、求职模拟面试打造的AI面试辅助平台</p>
        <div class="mt-4 flex gap-4">
          <span class="text-[#1677ff] hover:underline cursor-pointer text-sm">使用帮助文档</span>
          <span class="text-[#1677ff] hover:underline cursor-pointer text-sm">联系客服</span>
        </div>
      </div>
    </main>
  </div>
</template>
