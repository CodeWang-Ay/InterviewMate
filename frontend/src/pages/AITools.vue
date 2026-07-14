<script setup>
import { computed, onMounted, ref } from 'vue'
import Sidebar from '../components/Sidebar.vue'

const mode = ref('score')
const sourceType = ref('upload')
const selectedFile = ref(null)
const selectedFileName = ref('')
const running = ref(false)
const result = ref(null)
const rawPreview = ref('')
const selectedJdId = ref('')
const jdOptions = ref([])
const resumeOptions = ref([])
const selectedResumeId = ref('')
const selectedResume = computed(() => resumeOptions.value.find(item => String(item.id) === String(selectedResumeId.value)) || null)

const acceptedFormats = '.pdf,.docx,.txt,.md'
const hasResult = computed(() => Boolean(result.value))
const actionLabel = computed(() => mode.value === 'score' ? '开始简历评估' : '开始简历润色')
const modeTitle = computed(() => mode.value === 'score' ? '简历打分' : '简历润色')
const modeDesc = computed(() => mode.value === 'score'
  ? '根据上传简历和可选 JD，输出综合评分、风险提醒与优化建议。'
  : '生成一版不污染正式简历库的润色建议和优化稿。')

async function loadJds() {
  try {
    const res = await fetch('/api/jds?page_size=999')
    if (!res.ok) return
    const data = await res.json()
    jdOptions.value = (data.items || []).filter(item => item.status === 'enable')
  } catch (_) {
    jdOptions.value = []
  }
}

async function loadParsedResumes() {
  try {
    const res = await fetch('/api/resumes?parse_status=success')
    if (!res.ok) return
    const data = await res.json()
    resumeOptions.value = Array.isArray(data) ? data : []
  } catch (_) {
    resumeOptions.value = []
  }
}

function onFileChange(event) {
  const file = event.target?.files?.[0]
  selectedFile.value = file || null
  selectedFileName.value = file?.name || ''
  result.value = null
  rawPreview.value = ''
}

async function runTool() {
  if (running.value) return
  if (sourceType.value === 'upload' && !selectedFile.value) return
  if (sourceType.value === 'library' && !selectedResume.value) return
  running.value = true
  result.value = null
  rawPreview.value = ''
  try {
    if (sourceType.value === 'upload') {
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      if (selectedJdId.value) formData.append('jd_id', selectedJdId.value)
      if (mode.value === 'polish') formData.append('mode', selectedJdId.value ? 'jd' : 'general')

      const endpoint = mode.value === 'score' ? '/api/ai-tools/resume/score' : '/api/ai-tools/resume/polish'
      const res = await fetch(endpoint, { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `${modeTitle.value}失败`)
      result.value = data.result
      rawPreview.value = data.raw || ''
    } else {
      const endpoint = mode.value === 'score'
        ? `/api/resumes/${selectedResume.value.id}/score`
        : `/api/resumes/${selectedResume.value.id}/polish`
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jd_id: selectedJdId.value || selectedResume.value.jd_id || null,
          mode: mode.value === 'polish' ? (selectedJdId.value || selectedResume.value.jd_id ? 'jd' : 'general') : 'jd',
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `${modeTitle.value}失败`)
      result.value = data
      rawPreview.value = ''
    }
  } catch (err) {
    alert(err.message || `${modeTitle.value}失败`)
  } finally {
    running.value = false
  }
}

async function copyText(text) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(String(text))
  } catch (_) {
    const textarea = document.createElement('textarea')
    textarea.value = String(text)
    textarea.style.position = 'absolute'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  }
}

function switchSource(next) {
  sourceType.value = next
  result.value = null
  rawPreview.value = ''
}

function switchMode(next) {
  mode.value = next
  result.value = null
}

onMounted(() => {
  loadJds()
  loadParsedResumes()
})
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-[#f3f7fd]">
    <Sidebar />

    <main class="flex-1 overflow-y-auto">
      <div class="mx-auto max-w-[1580px] px-7 py-7">
        <section class="overflow-hidden rounded-[30px] border border-[#d7e5fb] bg-white shadow-[0_22px_60px_rgba(80,112,178,0.12)]">
          <div class="grid xl:grid-cols-[1.15fr_0.85fr]">
            <div class="bg-[linear-gradient(135deg,#17305f_0%,#2257ca_58%,#7ea4ff_100%)] px-8 py-8 text-white">
              <div class="inline-flex items-center gap-2 rounded-full bg-white/12 px-4 py-2 text-sm font-semibold tracking-[0.08em] text-white/90">
                <span class="h-2.5 w-2.5 rounded-full bg-emerald-300"></span>
                AI TOOLBOX
              </div>
              <div class="mt-8 max-w-2xl">
                <p class="text-sm uppercase tracking-[0.24em] text-white/62">Temporary Workspace</p>
                <h1 class="mt-4 text-[40px] font-bold leading-[1.08]">AI 辅助中心</h1>
                <p class="mt-5 text-[17px] leading-8 text-white/82">
                  这里是临时实验室。你可以单独上传一份简历做打分和润色，不会写入正式简历库，也不会影响现有候选人档案。
                </p>
              </div>
              <div class="mt-8 grid gap-4 sm:grid-cols-3">
                <div class="rounded-2xl border border-white/16 bg-white/10 px-4 py-4">
                  <div class="text-sm text-white/66">用途一</div>
                  <div class="mt-2 text-lg font-semibold">简历打分</div>
                </div>
                <div class="rounded-2xl border border-white/16 bg-white/10 px-4 py-4">
                  <div class="text-sm text-white/66">用途二</div>
                  <div class="mt-2 text-lg font-semibold">简历润色</div>
                </div>
                <div class="rounded-2xl border border-white/16 bg-white/10 px-4 py-4">
                  <div class="text-sm text-white/66">数据边界</div>
                  <div class="mt-2 text-lg font-semibold">不入正式简历库</div>
                </div>
              </div>
            </div>

            <div class="bg-[#f8fbff] px-8 py-8">
              <div class="text-sm font-semibold text-[#3970e9]">How It Works</div>
              <h2 class="mt-2 text-[28px] font-bold text-[#18233e]">用法很简单</h2>
              <div class="mt-7 space-y-4">
                <div class="rounded-2xl border border-[#deebff] bg-white px-5 py-4">
                  <div class="text-sm font-semibold text-[#1d2941]">1. 上传一份简历</div>
                  <p class="mt-2 text-sm leading-7 text-[#71819d]">支持 PDF、DOCX、TXT、MD，仅用于本次分析。</p>
                </div>
                <div class="rounded-2xl border border-[#deebff] bg-white px-5 py-4">
                  <div class="text-sm font-semibold text-[#1d2941]">2. 可选绑定一个目标 JD</div>
                  <p class="mt-2 text-sm leading-7 text-[#71819d]">绑定后会按岗位视角做评估或定向润色。</p>
                </div>
                <div class="rounded-2xl border border-[#deebff] bg-white px-5 py-4">
                  <div class="text-sm font-semibold text-[#1d2941]">3. 输出结果可直接复制使用</div>
                  <p class="mt-2 text-sm leading-7 text-[#71819d]">适合实验、练习、模拟，不污染你正式候选人数据。</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div class="mt-7 grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
          <section class="rounded-[28px] border border-[#dce7fb] bg-white px-6 py-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
            <div class="inline-flex p-1 rounded-xl bg-[#f3f7ff] border border-[#dce7fb]">
              <button
                :class="['px-4 py-2 rounded-lg text-sm font-medium transition', sourceType === 'upload' ? 'bg-white text-[#2f6df6] shadow-sm' : 'text-gray-500 hover:text-gray-700']"
                @click="switchSource('upload')"
              >
                <i class="fa fa-upload mr-1"></i>临时上传
              </button>
              <button
                :class="['px-4 py-2 rounded-lg text-sm font-medium transition', sourceType === 'library' ? 'bg-white text-[#2f6df6] shadow-sm' : 'text-gray-500 hover:text-gray-700']"
                @click="switchSource('library')"
              >
                <i class="fa fa-database mr-1"></i>从简历库选择
              </button>
            </div>

            <div class="mt-4 inline-flex p-1 rounded-xl bg-[#f3f7ff] border border-[#dce7fb]">
              <button
                :class="['px-4 py-2 rounded-lg text-sm font-medium transition', mode === 'score' ? 'bg-white text-[#d97706] shadow-sm' : 'text-gray-500 hover:text-gray-700']"
                @click="switchMode('score')"
              >
                <i class="fa fa-star-o mr-1"></i>简历打分
              </button>
              <button
                :class="['px-4 py-2 rounded-lg text-sm font-medium transition', mode === 'polish' ? 'bg-white text-[#0891b2] shadow-sm' : 'text-gray-500 hover:text-gray-700']"
                @click="switchMode('polish')"
              >
                <i class="fa fa-magic mr-1"></i>简历润色
              </button>
            </div>

            <div class="mt-6 rounded-[26px] border border-dashed border-[#b8ccf5] bg-[#f8fbff] p-6">
              <div class="flex items-center gap-4">
                <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-[#2f6df6] shadow-sm">
                  <i :class="['fa text-xl', sourceType === 'upload' ? 'fa-upload' : 'fa-database']"></i>
                </div>
                <div>
                  <div class="text-lg font-semibold text-[#18233e]">{{ modeTitle }}</div>
                  <div class="mt-1 text-sm text-[#71819d]">{{ modeDesc }}</div>
                </div>
              </div>

              <label v-if="sourceType === 'upload'" class="mt-6 block cursor-pointer rounded-2xl border border-[#dce7fb] bg-white px-5 py-5 transition hover:border-[#95b5ff] hover:bg-[#fbfdff]">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <div class="text-sm font-semibold text-[#1d2941]">上传简历文件</div>
                    <div class="mt-1 text-sm text-[#71819d]">{{ selectedFileName || '选择一份临时用于分析的简历文件' }}</div>
                  </div>
                  <div class="rounded-xl bg-[#edf4ff] px-4 py-2 text-sm font-semibold text-[#2f6df6]">选择文件</div>
                </div>
                <input type="file" class="hidden" :accept="acceptedFormats" @change="onFileChange" />
              </label>

              <div v-else class="mt-6 rounded-2xl border border-[#dce7fb] bg-white px-5 py-5">
                <label class="block text-sm font-semibold text-[#1d2941] mb-2">选择已解析简历</label>
                <select v-model="selectedResumeId" class="w-full rounded-2xl border border-[#dce7fb] bg-white px-4 py-3 text-sm text-[#1d2941] outline-none focus:border-[#2f6df6]">
                  <option value="">请选择一份解析成功的简历</option>
                  <option v-for="resume in resumeOptions" :key="resume.id" :value="resume.id">
                    {{ resume.name || '未命名候选人' }} · {{ resume.target_position || '未填写岗位' }} · {{ resume.jd_name || '未关联 JD' }}
                  </option>
                </select>
                <div v-if="selectedResume" class="mt-4 rounded-2xl bg-[#f8fbff] px-4 py-4">
                  <div class="text-sm font-semibold text-[#1d2941]">{{ selectedResume.name || '未命名候选人' }}</div>
                  <div class="mt-1 text-sm text-[#71819d]">{{ selectedResume.target_position || '未填写意向岗位' }}</div>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <span class="rounded-full bg-white px-3 py-1 text-xs text-[#5f708f] border border-[#dce7fb]">{{ selectedResume.education || '学历待补充' }}</span>
                    <span class="rounded-full bg-white px-3 py-1 text-xs text-[#5f708f] border border-[#dce7fb]">{{ selectedResume.jd_name || '未关联 JD' }}</span>
                    <span class="rounded-full bg-white px-3 py-1 text-xs text-[#5f708f] border border-[#dce7fb]">{{ selectedResume.skills || '暂无技能标签' }}</span>
                  </div>
                </div>
              </div>

              <div class="mt-5">
                <label class="block text-sm font-semibold text-[#1d2941] mb-2">目标岗位 JD（可选）</label>
                <select v-model="selectedJdId" class="w-full rounded-2xl border border-[#dce7fb] bg-white px-4 py-3 text-sm text-[#1d2941] outline-none focus:border-[#2f6df6]">
                  <option value="">不绑定 JD，按通用标准处理</option>
                  <option v-for="jd in jdOptions" :key="jd.id" :value="jd.id">{{ jd.name }} · {{ jd.category }} · {{ jd.location }}</option>
                </select>
              </div>

              <button
                :disabled="(sourceType === 'upload' ? !selectedFile : !selectedResume) || running"
                class="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#17305f_0%,#2f6df6_100%)] px-5 py-4 text-base font-semibold text-white transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-45"
                @click="runTool"
              >
                <i :class="['fa', running ? 'fa-spinner fa-spin' : mode === 'score' ? 'fa-star-o' : 'fa-magic']"></i>
                {{ running ? '处理中...' : actionLabel }}
              </button>
            </div>
          </section>

          <section class="rounded-[28px] border border-[#dce7fb] bg-white px-6 py-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="text-sm font-semibold text-[#3970e9]">Result Panel</div>
                <h2 class="mt-2 text-[28px] font-bold text-[#18233e]">{{ mode === 'score' ? '评分结果' : '润色结果' }}</h2>
              </div>
            </div>

            <div v-if="running" class="py-24 text-center text-[#7b88a3]">
              <div class="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[#8fb0ff] border-t-transparent"></div>
              <p class="mt-4 text-sm">AI 正在处理这份临时简历...</p>
            </div>

            <div v-else-if="!hasResult" class="py-24 text-center text-[#7b88a3]">
              <i class="fa fa-lightbulb-o text-4xl mb-4 block text-[#a1b3d3]"></i>
              <p class="text-base">上传一份简历后，这里会显示结果</p>
              <p class="mt-2 text-sm">你可以先试试简历打分，再切到简历润色看看优化稿。</p>
            </div>

            <div v-else-if="mode === 'score'" class="space-y-5">
              <div class="grid gap-5 lg:grid-cols-[240px_1fr]">
                <div class="rounded-2xl border border-amber-100 bg-amber-50 p-5">
                  <div class="text-sm font-semibold text-amber-700">综合评分</div>
                  <div class="mt-4 text-[56px] font-bold text-gray-900">{{ result.total_score }}</div>
                  <div class="mt-2 text-sm text-gray-500">评估基准：{{ result.matched_jd_name || '通用标准' }}</div>
                  <p class="mt-5 text-sm leading-7 text-gray-700">{{ result.summary }}</p>
                </div>
                <div class="rounded-2xl border border-gray-200 p-5">
                  <div class="text-base font-semibold text-gray-900 mb-4">分维度评分</div>
                  <div class="space-y-4">
                    <div v-for="item in result.dimensions || []" :key="item.name">
                      <div class="flex items-center justify-between mb-1">
                        <span class="text-sm font-medium text-gray-700">{{ item.name }}</span>
                        <span class="text-sm font-semibold text-gray-900">{{ item.score }}</span>
                      </div>
                      <div class="h-2 rounded-full bg-gray-100 overflow-hidden">
                        <div class="h-full rounded-full bg-[linear-gradient(90deg,#f59e0b_0%,#f7c25f_100%)]" :style="{ width: `${item.score}%` }"></div>
                      </div>
                      <p class="mt-2 text-sm text-gray-500 leading-6">{{ item.comment }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="grid gap-4 md:grid-cols-3">
                <div class="rounded-2xl border border-green-100 bg-green-50 p-4">
                  <div class="text-sm font-semibold text-green-700 mb-3">优势亮点</div>
                  <ul class="space-y-2 text-sm text-gray-700">
                    <li v-for="(item, idx) in result.strengths || []" :key="'strength-' + idx">• {{ item }}</li>
                  </ul>
                </div>
                <div class="rounded-2xl border border-red-100 bg-red-50 p-4">
                  <div class="text-sm font-semibold text-red-700 mb-3">风险提醒</div>
                  <ul class="space-y-2 text-sm text-gray-700">
                    <li v-for="(item, idx) in result.risks || []" :key="'risk-' + idx">• {{ item }}</li>
                  </ul>
                </div>
                <div class="rounded-2xl border border-blue-100 bg-blue-50 p-4">
                  <div class="text-sm font-semibold text-blue-700 mb-3">优化建议</div>
                  <ul class="space-y-2 text-sm text-gray-700">
                    <li v-for="(item, idx) in result.suggestions || []" :key="'suggestion-' + idx">• {{ item }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <div v-else class="space-y-5">
              <div class="rounded-2xl border border-cyan-100 bg-cyan-50 p-5">
                <div class="text-sm font-semibold text-cyan-700">润色总结</div>
                <p class="mt-3 text-sm leading-7 text-gray-700">{{ result.summary }}</p>
                <div class="mt-3 text-xs text-gray-500">评估基准：{{ result.matched_jd_name || '通用标准' }}</div>
              </div>

              <div class="grid gap-4">
                <div v-for="(section, idx) in result.sections || []" :key="'section-' + idx" class="rounded-2xl border border-gray-200 overflow-hidden">
                  <div class="px-5 py-4 bg-gray-50 border-b">
                    <div class="font-semibold text-gray-900">{{ section.title }}</div>
                    <div class="text-sm text-gray-500 mt-1">{{ section.reason }}</div>
                  </div>
                  <div class="grid md:grid-cols-2 gap-0">
                    <div class="p-5 border-r border-gray-100">
                      <div class="text-xs uppercase tracking-[0.08em] text-gray-400 mb-3">原始表达</div>
                      <div class="text-sm text-gray-700 leading-7 whitespace-pre-wrap">{{ section.original || '-' }}</div>
                    </div>
                    <div class="p-5 bg-cyan-50/40">
                      <div class="flex items-center justify-between gap-3 mb-3">
                        <div class="text-xs uppercase tracking-[0.08em] text-cyan-600">润色建议</div>
                        <button class="text-xs text-cyan-700 hover:text-cyan-900" @click="copyText(section.polished)">复制</button>
                      </div>
                      <div class="text-sm text-gray-800 leading-7 whitespace-pre-wrap">{{ section.polished || '-' }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="rounded-2xl border border-cyan-100 overflow-hidden">
                <div class="px-5 py-4 bg-cyan-50 border-b flex items-center justify-between gap-3">
                  <div>
                    <div class="font-semibold text-gray-900">可直接使用的润色版本</div>
                    <div class="text-sm text-gray-500 mt-1">这版是临时优化稿，不会写回正式简历库</div>
                  </div>
                  <button class="px-3 py-2 rounded-lg bg-cyan-600 text-white text-sm hover:bg-cyan-700" @click="copyText(result.polished_version)">
                    <i class="fa fa-copy mr-1"></i>复制全文
                  </button>
                </div>
                <div class="p-5 text-sm text-gray-800 leading-7 whitespace-pre-wrap bg-white">{{ result.polished_version || '-' }}</div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>
