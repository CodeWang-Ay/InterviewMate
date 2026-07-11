<script setup>
import { ref, computed } from 'vue'

const jdText = ref('')
const jdSaved = ref(false)
const resumeFile = ref(null)
const resumeUploading = ref(false)

const ALLOWED_TYPES = '.pdf,.docx,.txt,.md'

const bothReady = computed(() => jdSaved.value && resumeFile.value)

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
    resumeFile.value = { name: data.original_name, status: 'ok' }
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

function startInterview() {
  // TODO: 进入面试流程
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-2xl">
      <!-- Header -->
      <div class="text-center mb-10">
        <h1 class="text-3xl font-bold text-white mb-2">面试者模式</h1>
        <p class="text-slate-400">填写岗位 JD，上传个人简历，开始模拟面试</p>
      </div>

      <!-- Step 1: Text JD -->
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
            rows="8"
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

      <!-- Step 2: Upload Resume -->
      <div class="mb-8">
        <h2 class="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <span class="w-7 h-7 rounded-full bg-emerald-600 text-sm flex items-center justify-center font-bold">2</span>
          上传个人简历
          <span v-if="resumeFile" class="text-emerald-400 text-sm font-normal ml-auto">
            <svg class="w-5 h-5 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
            {{ resumeFile.name }}
          </span>
        </h2>
        <label
          v-if="!resumeFile"
          class="block w-full border-2 border-dashed border-slate-600 rounded-xl p-10 text-center cursor-pointer transition-all duration-200 hover:border-emerald-500 hover:bg-slate-800/50"
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
          <input
            type="file"
            :accept="ALLOWED_TYPES"
            class="hidden"
            @change="onResumeChange"
          />
        </label>
        <div
          v-else
          class="w-full rounded-xl bg-slate-800/50 border border-emerald-600/30 p-6 flex items-center gap-4"
        >
          <div class="w-10 h-10 bg-emerald-600/20 rounded-lg flex items-center justify-center flex-shrink-0">
            <svg class="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-white text-sm truncate">{{ resumeFile.name }}</p>
            <p class="text-emerald-400 text-xs">上传成功</p>
          </div>
          <button
            class="text-slate-500 hover:text-red-400 transition-colors"
            @click="resumeFile = null"
          >✕</button>
        </div>
      </div>

      <!-- Step 3: Start Interview -->
      <button
        :disabled="!bothReady"
        :class="[
          'w-full py-4 rounded-xl font-semibold text-lg transition-all duration-300',
          bothReady
            ? 'bg-emerald-600 text-white hover:bg-emerald-500 cursor-pointer shadow-lg shadow-emerald-500/25'
            : 'bg-slate-700 text-slate-500 cursor-not-allowed'
        ]"
        @click="startInterview"
      >
        开始面试
      </button>

      <!-- Back -->
      <div class="text-center mt-6">
        <router-link to="/" class="text-slate-500 hover:text-slate-300 text-sm transition-colors">
          ← 返回首页
        </router-link>
      </div>
    </div>
  </div>
</template>
