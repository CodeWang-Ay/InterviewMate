<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const assignedLoading = ref(true)
const assignedPlans = ref([])
const assignedError = ref('')

// JD
const jdText = ref('')
const jdSaved = ref(false)
const jdFilename = ref('')

// Resume
const resumeFile = ref(null)
const resumeFilename = ref('')
const resumeUploading = ref(false)
const resumeParsing = ref(false)
const resumeParsed = ref(false)
const resumeContent = ref('')
const resumeStructured = ref(null)
const showStructured = ref(true)

// Plan
const planGenerating = ref(false)
const planContent = ref('')

const ALLOWED_TYPES = '.pdf,.docx,.txt,.md'

const canParse = computed(() => resumeFile.value && !resumeParsed.value)
const canGenerate = computed(() => jdSaved.value && resumeParsed.value)
const currentAssignedPlan = computed(() => {
  return assignedPlans.value.find(p => ['wait', 'running'].includes(p.status)) || assignedPlans.value[0] || null
})
const workflowName = computed(() => assignedPlans.value[0]?.workflow_name || '面试流程')

onMounted(fetchAssignedPlans)

async function fetchAssignedPlans() {
  assignedLoading.value = true
  assignedError.value = ''
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/plans/my', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '获取面试计划失败')
    }
    assignedPlans.value = await res.json()
    const plan = currentAssignedPlan.value
    if (plan && ['wait', 'running'].includes(plan.status)) {
      router.replace({ path: '/chat', query: { plan_id: plan.id } })
    }
  } catch (e) {
    assignedError.value = e.message
  } finally {
    assignedLoading.value = false
  }
}

function planStatusLabel(status) {
  return { wait: '待开始', pending: '待前序完成', running: '面试中', finish: '已完成', cancel: '已取消' }[status] || status
}

function planStatusClass(status) {
  return {
    wait: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
    pending: 'bg-slate-700/60 text-slate-400 border-slate-600',
    running: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    finish: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    cancel: 'bg-red-500/15 text-red-300 border-red-500/30',
  }[status] || 'bg-slate-700/60 text-slate-400 border-slate-600'
}

function startAssignedInterview(plan) {
  if (!plan) return
  router.push({ path: '/chat', query: { plan_id: plan.id } })
}

async function saveJD() {
  if (!jdText.value.trim()) return
  try {
    const res = await fetch('/api/save/jd', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: jdText.value }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '保存失败')
    }
    const data = await res.json()
    jdFilename.value = data.filename
    jdSaved.value = true
  } catch (e) {
    alert(e.message)
  }
}

async function handleResumeUpload(file) {
  if (!file) return
  resumeUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch('/api/upload/resume', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '上传失败')
    }
    const data = await res.json()
    resumeFilename.value = data.filename
    resumeFile.value = { name: data.original_name }
    resumeParsed.value = false
    resumeContent.value = ''
    planContent.value = ''
  } catch (e) {
    alert(e.message)
  } finally {
    resumeUploading.value = false
  }
}

function onResumeDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (file) handleResumeUpload(file)
}

function onResumeChange(e) {
  const file = e.target?.files?.[0]
  if (file) handleResumeUpload(file)
}

async function parseResume() {
  resumeParsing.value = true
  try {
    const res = await fetch('/api/parse/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_filename: resumeFilename.value }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '解析失败')
    }
    const data = await res.json()
    resumeContent.value = data.resume
    resumeStructured.value = data.structured || null
    resumeParsed.value = true
  } catch (e) {
    alert(e.message)
  } finally {
    resumeParsing.value = false
  }
}

async function generatePlan() {
  planGenerating.value = true
  try {
    const res = await fetch('/api/generate/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jd_filename: jdFilename.value,
        resume_filename: resumeFilename.value,
      }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '生成失败')
    }
    const data = await res.json()
    planContent.value = data.plan
  } catch (e) {
    alert(e.message)
  } finally {
    planGenerating.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-2xl">
      <div class="text-center mb-10">
        <h1 class="text-3xl font-bold text-white mb-2">面试者模式</h1>
        <p class="text-slate-400">{{ assignedPlans.length ? '查看你的面试流程并开始当前环节' : '填写岗位 JD，上传个人简历，生成面试计划' }}</p>
      </div>

      <div v-if="assignedLoading" class="rounded-2xl border border-slate-700 bg-slate-900/60 p-8 text-center text-slate-400">
        <span class="inline-block w-5 h-5 border-2 border-slate-500 border-t-white rounded-full animate-spin mr-2 align-middle"></span>
        正在加载你的面试流程...
      </div>

      <div v-else-if="assignedPlans.length" class="space-y-6">
        <div class="rounded-2xl border border-emerald-500/25 bg-slate-900/70 shadow-2xl overflow-hidden">
          <div class="px-6 py-5 border-b border-slate-700/60 flex items-center justify-between gap-4">
            <div>
              <h2 class="text-xl font-bold text-white">{{ workflowName }}</h2>
              <p class="text-sm text-slate-400 mt-1">{{ currentAssignedPlan?.candidate_name }} · {{ currentAssignedPlan?.jd_name }}</p>
            </div>
            <span class="px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 text-xs border border-emerald-500/30">
              {{ assignedPlans.length }} 个环节
            </span>
          </div>

          <div class="p-6">
            <div class="flex items-center gap-3 overflow-x-auto pb-2">
              <template v-for="(plan, index) in assignedPlans" :key="plan.id">
                <div class="min-w-[180px] rounded-xl border p-4" :class="planStatusClass(plan.status)">
                  <div class="text-xs opacity-80">第 {{ plan.stage_order || index + 1 }}/{{ plan.stage_count || assignedPlans.length }} 环节</div>
                  <div class="text-base font-semibold mt-2">{{ plan.interview_round }}</div>
                  <div class="text-xs mt-3">{{ planStatusLabel(plan.status) }}</div>
                </div>
                <i v-if="index < assignedPlans.length - 1" class="fa fa-long-arrow-right text-slate-500"></i>
              </template>
            </div>

            <div class="mt-6 rounded-xl bg-slate-800/70 border border-slate-700 p-5">
              <div class="text-sm text-slate-400">当前环节</div>
              <div class="flex items-center justify-between gap-4 mt-2">
                <div>
                  <div class="text-lg font-bold text-white">{{ currentAssignedPlan?.interview_round }}</div>
                  <div class="text-xs text-slate-500 mt-1">状态：{{ planStatusLabel(currentAssignedPlan?.status) }}</div>
                </div>
                <button
                  class="px-5 py-3 rounded-xl bg-emerald-600 text-white font-semibold hover:bg-emerald-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  :disabled="!['wait', 'running'].includes(currentAssignedPlan?.status)"
                  @click="startAssignedInterview(currentAssignedPlan)"
                >
                  开始当前面试
                </button>
              </div>
            </div>
          </div>
        </div>

        <p v-if="assignedError" class="text-red-400 text-sm text-center">{{ assignedError }}</p>
      </div>

      <template v-else>
      <p v-if="assignedError" class="text-red-400 text-sm text-center mb-4">{{ assignedError }}</p>

      <!-- Step 1: JD -->
      <div class="mb-6">
        <h2 class="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <span class="w-7 h-7 rounded-full bg-emerald-600 text-sm flex items-center justify-center font-bold">1</span>
          填写岗位 JD
          <span v-if="jdSaved" class="text-emerald-400 text-sm font-normal ml-auto">
            <svg class="w-5 h-5 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
            已保存
          </span>
        </h2>
        <div class="relative">
          <textarea
            v-model="jdText"
            :disabled="jdSaved"
            rows="6"
            placeholder="请粘贴岗位描述（JD），例如：&#10;&#10;岗位名称：高级前端工程师&#10;岗位职责：&#10;1. 负责公司核心产品的前端架构设计...&#10;2. ...&#10;&#10;任职要求：&#10;1. 3年以上前端开发经验...&#10;2. ..."
            class="w-full rounded-xl border-2 border-slate-600 bg-slate-800/50 text-white text-sm p-5 resize-y placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors disabled:opacity-60 disabled:cursor-default"
          ></textarea>
          <span class="absolute bottom-3 right-3 text-slate-500 text-xs">{{ jdText.length }} 字</span>
        </div>
        <button
          v-if="!jdSaved"
          class="mt-3 w-full py-3 rounded-xl bg-slate-700 text-slate-300 font-medium hover:bg-slate-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="!jdText.trim()"
          @click="saveJD"
        >
          保存岗位 JD
        </button>
        <button
          v-else
          class="mt-3 w-full py-3 rounded-xl bg-emerald-600/20 border border-emerald-600/30 text-emerald-400 text-sm font-medium hover:bg-emerald-600/30 transition-colors"
          @click="jdSaved = false"
        >
          重新编辑
        </button>
      </div>

      <!-- Step 2: Upload Resume + Parse -->
      <div class="mb-6">
        <h2 class="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <span class="w-7 h-7 rounded-full bg-emerald-600 text-sm flex items-center justify-center font-bold">2</span>
          上传个人简历
          <span v-if="resumeFile" class="text-slate-400 text-sm font-normal ml-auto">
            {{ resumeFile.name }}
            <span v-if="resumeParsed" class="text-emerald-400 ml-1">· 已解析</span>
          </span>
        </h2>
        <!-- Upload area -->
        <label
          v-if="!resumeFile"
          class="block w-full border-2 border-dashed border-slate-600 rounded-xl p-8 text-center cursor-pointer transition-all duration-200 hover:border-emerald-500 hover:bg-slate-800/50"
          @dragover.prevent
          @drop.prevent="onResumeDrop"
        >
          <svg class="w-10 h-10 text-slate-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
          </svg>
          <p class="text-slate-400 text-sm mb-1">
            <span class="text-emerald-400 font-medium">点击上传</span> 或拖拽文件到这里
          </p>
          <p class="text-slate-500 text-xs">支持 PDF、DOCX、TXT、MD 格式，最大 10MB</p>
          <input type="file" :accept="ALLOWED_TYPES" class="hidden" @change="onResumeChange" />
        </label>
        <!-- Uploaded -->
        <div v-else class="w-full rounded-xl bg-slate-800/50 border border-slate-600 p-5 flex items-center gap-4">
          <div class="w-10 h-10 bg-emerald-600/20 rounded-lg flex items-center justify-center flex-shrink-0">
            <svg class="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-white text-sm truncate">{{ resumeFile.name }}</p>
            <p class="text-slate-500 text-xs">上传成功</p>
          </div>
          <button class="text-slate-500 hover:text-red-400 transition-colors" @click="resumeFile = null">✕</button>
        </div>
        <!-- Parse button -->
        <button
          v-if="canParse"
          class="mt-3 w-full py-3 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          :disabled="resumeParsing"
          @click="parseResume"
        >
          <span v-if="resumeParsing" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          {{ resumeParsing ? '正在解析...' : '🔍 解析简历' }}
        </button>
        <!-- Parsed preview -->
        <div v-if="resumeParsed" class="mt-3 w-full rounded-xl bg-slate-800/50 border border-blue-600/30 overflow-hidden">
          <div class="px-5 py-3 bg-blue-600/10 border-b border-blue-600/20 flex items-center justify-between">
            <span class="text-blue-400 text-sm font-medium">简历解析结果</span>
            <div class="flex items-center gap-3">
              <button
                class="text-slate-500 hover:text-slate-300 text-xs transition-colors"
                @click="showStructured = !showStructured"
              >
                {{ showStructured ? '查看原文' : '结构化视图' }}
              </button>
              <span class="text-slate-500 text-xs">{{ resumeContent.length }} 字符</span>
            </div>
          </div>

          <!-- 结构化视图 -->
          <div v-if="showStructured && resumeStructured" class="divide-y divide-slate-700/30">
            <!-- 基础信息 -->
            <div v-if="resumeStructured.基础信息" class="px-5 py-3">
              <h4 class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">基础信息</h4>
              <div class="grid grid-cols-2 md:grid-cols-3 gap-2">
                <div v-for="(val, key) in resumeStructured.基础信息" :key="key">
                  <template v-if="val">
                    <span class="text-slate-500 text-xs">{{ key }}</span>
                    <p class="text-white text-sm">{{ val }}</p>
                  </template>
                </div>
              </div>
              <p v-if="resumeStructured.自我评价" class="text-slate-400 text-xs mt-2 leading-relaxed">
                <span class="text-slate-500">自我评价：</span>{{ resumeStructured.自我评价 }}
              </p>
            </div>

            <!-- 教育经历 -->
            <div v-if="resumeStructured.教育经历?.length" class="px-5 py-3">
              <h4 class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">教育经历</h4>
              <div v-for="(edu, i) in resumeStructured.教育经历" :key="i" class="mb-2 last:mb-0">
                <div class="flex items-center gap-2">
                  <span class="text-white text-sm font-medium">{{ edu.学校 }}</span>
                  <span class="text-slate-500 text-xs">{{ edu.专业 }}</span>
                  <span class="text-blue-400 text-xs">{{ edu.学位 }}</span>
                  <span class="text-slate-600 text-xs ml-auto">{{ edu.开始时间 }} ~ {{ edu.结束时间 }}</span>
                </div>
              </div>
            </div>

            <!-- 工作经历 -->
            <div v-if="resumeStructured.工作经历?.length" class="px-5 py-3">
              <h4 class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">工作经历</h4>
              <div v-for="(job, i) in resumeStructured.工作经历" :key="i" class="mb-3 last:mb-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-white text-sm font-medium">{{ job.公司名称 }}</span>
                  <span class="text-emerald-400 text-xs">{{ job.职位 }}</span>
                  <span class="text-slate-600 text-xs ml-auto">{{ job.开始时间 }} ~ {{ job.结束时间 }}</span>
                </div>
                <p class="text-slate-400 text-xs leading-relaxed line-clamp-2">{{ job.工作描述 }}</p>
              </div>
            </div>

            <!-- 项目经历 -->
            <div v-if="resumeStructured.项目经历?.length" class="px-5 py-3">
              <h4 class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">项目经历</h4>
              <div v-for="(proj, i) in resumeStructured.项目经历" :key="i" class="mb-3 last:mb-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-white text-sm font-medium">{{ proj.项目名称 }}</span>
                  <span class="text-purple-400 text-xs">{{ proj.角色 }}</span>
                  <span class="text-slate-600 text-xs ml-auto">{{ proj.开始时间 }} ~ {{ proj.结束时间 }}</span>
                </div>
                <p class="text-slate-400 text-xs leading-relaxed line-clamp-2">{{ proj.项目描述 }}</p>
              </div>
            </div>
          </div>

          <!-- 原始文本视图 -->
          <pre v-if="!showStructured || !resumeStructured" class="text-slate-300 text-sm p-5 whitespace-pre-wrap overflow-auto max-h-48">{{ resumeContent }}</pre>
        </div>
      </div>

      <!-- Step 3: Generate Plan -->
      <div class="mb-8">
        <h2 class="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <span class="w-7 h-7 rounded-full bg-emerald-600 text-sm flex items-center justify-center font-bold">3</span>
          生成面试计划
        </h2>
        <button
          :disabled="!canGenerate || planGenerating"
          :class="[
            'w-full py-4 rounded-xl font-semibold text-lg transition-all duration-300 flex items-center justify-center gap-2',
            canGenerate
              ? 'bg-emerald-600 text-white hover:bg-emerald-500 cursor-pointer shadow-lg shadow-emerald-500/25'
              : 'bg-slate-700 text-slate-500 cursor-not-allowed'
          ]"
          @click="generatePlan"
        >
          <span v-if="planGenerating" class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          {{ planGenerating ? '正在生成...' : '📋 生成面试计划' }}
        </button>
        <p v-if="!canGenerate" class="text-slate-600 text-xs text-center mt-2">
          请先保存岗位 JD 并解析简历
        </p>
        <!-- Plan result -->
        <div v-if="planContent" class="mt-4 w-full rounded-xl bg-slate-800/50 border border-emerald-600/30">
          <div class="px-5 py-3 bg-emerald-600/10 border-b border-emerald-600/20">
            <span class="text-emerald-400 text-sm font-medium">面试计划</span>
          </div>
          <pre class="text-slate-300 text-sm p-5 whitespace-pre-wrap overflow-auto max-h-80">{{ planContent }}</pre>
        </div>
        <!-- Start Interview button -->
        <button
          v-if="planContent"
          class="mt-4 w-full py-4 rounded-xl font-semibold text-lg bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:from-blue-500 hover:to-blue-600 cursor-pointer shadow-lg shadow-blue-500/25 transition-all duration-300 flex items-center justify-center gap-2"
          @click="router.push({ path: '/chat', query: { jd: jdFilename, resume: resumeFilename } })"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 0 1 .778-.332 48.294 48.294 0 0 0 5.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
          </svg>
          开始面试
        </button>
      </div>

      <div class="text-center">
        <router-link to="/" class="text-slate-500 hover:text-slate-300 text-sm transition-colors">
          ← 返回首页
        </router-link>
      </div>
      </template>
    </div>
  </div>
</template>
