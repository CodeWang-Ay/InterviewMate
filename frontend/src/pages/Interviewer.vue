<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const loading = ref(true)
const starting = ref(false)
const error = ref('')
const jds = ref([])
const resumes = ref([])
const selectedJdId = ref(null)
const selectedResumeId = ref(null)
const trainingMode = ref('结构化面试')
const candidateStyle = ref('标准型')

const trainingModes = [
  { value: '结构化面试', title: '结构化面试', desc: '按岗位能力维度走标准面试路径' },
  { value: '一面能力摸底', title: '一面摸底', desc: '快速判断基础能力、表达和岗位匹配度' },
  { value: '二面项目深挖', title: '二面深挖', desc: '重点追项目细节、技术深度和决策逻辑' },
  { value: 'HR综合沟通', title: 'HR 综合面', desc: '关注动机、稳定性、协作与沟通方式' },
]

const styleOptions = [
  { value: '标准型', title: '标准型', desc: '回答完整、配合度高，适合日常练习' },
  { value: '紧张型', title: '紧张型', desc: '会犹豫和卡顿，考验安抚与引导能力' },
  { value: '强表达型', title: '强表达型', desc: '会主动延展，适合训练控场和收口' },
  { value: '模糊回答型', title: '模糊回答型', desc: '回答泛，需要持续追问拿到有效信息' },
  { value: '经验包装型', title: '经验包装型', desc: '会适度包装经历，适合训练识别能力' },
]

const selectedJd = computed(() => jds.value.find(item => item.id === selectedJdId.value) || null)
const selectedResume = computed(() => resumes.value.find(item => item.id === selectedResumeId.value) || null)

const fitSignals = computed(() => {
  const items = []
  if (selectedResume.value?.target_position) items.push(`候选意向：${selectedResume.value.target_position}`)
  if (selectedResume.value?.experience_years) items.push(`经验：${selectedResume.value.experience_years}`)
  if (selectedResume.value?.education) items.push(`学历：${selectedResume.value.education}`)
  if (selectedJd.value?.category) items.push(`岗位线：${selectedJd.value.category}`)
  if (selectedJd.value?.location) items.push(`地点：${selectedJd.value.location}`)
  return items
})

const jdHighlights = computed(() => {
  const blocks = [selectedJd.value?.responsibilities || '', selectedJd.value?.requirements || '']
  return blocks
    .join('。')
    .split(/[。；;\n]/)
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 5)
})

const resumeHighlights = computed(() => {
  const blocks = [
    selectedResume.value?.skills || '',
    selectedResume.value?.target_position || '',
    selectedResume.value?.education || '',
    selectedResume.value?.experience_years || '',
  ]
  return blocks
    .join('，')
    .split(/[，,]/)
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 6)
})

const canStart = computed(() => selectedJd.value && selectedResume.value && !starting.value)

async function loadResources() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/interviewer-training/resources')
    if (!res.ok) throw new Error('训练资源加载失败')
    const data = await res.json()
    jds.value = data.jds || []
    resumes.value = data.resumes || []
    if (!selectedJdId.value && jds.value.length) selectedJdId.value = jds.value[0].id
    if (!selectedResumeId.value && resumes.value.length) selectedResumeId.value = resumes.value[0].id
  } catch (err) {
    error.value = err.message || '训练资源加载失败'
  } finally {
    loading.value = false
  }
}

async function startTraining() {
  if (!canStart.value) return
  starting.value = true
  error.value = ''
  try {
    const res = await fetch('/api/interviewer-training/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jd_id: selectedJdId.value,
        resume_id: selectedResumeId.value,
        training_mode: trainingMode.value,
        candidate_style: candidateStyle.value,
      }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '训练会话创建失败')
    router.push({ path: '/interviewer/chat', query: { session_id: data.session_id } })
  } catch (err) {
    error.value = err.message || '训练会话创建失败'
  } finally {
    starting.value = false
  }
}

onMounted(loadResources)
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-[#f3f7ff]">
    <Sidebar />

    <main class="flex-1 overflow-y-auto">
      <div class="max-w-[1500px] mx-auto px-8 py-8">
        <section class="rounded-[28px] overflow-hidden border border-[#d7e4ff] bg-white shadow-[0_24px_70px_rgba(70,110,190,0.12)]">
          <div class="grid lg:grid-cols-[1.18fr_0.82fr]">
            <div class="bg-[linear-gradient(135deg,#17305f_0%,#2d68e4_58%,#7da2ff_100%)] px-8 py-8 text-white">
              <div class="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-medium">
                <span class="h-2.5 w-2.5 rounded-full bg-emerald-300"></span>
                Interviewer Lab
              </div>

              <div class="mt-8 max-w-2xl">
                <p class="text-sm uppercase tracking-[0.28em] text-white/65">Admin Workspace</p>
                <h1 class="mt-4 text-[42px] leading-[1.08] font-bold">面试官训练台</h1>
                <p class="mt-5 max-w-xl text-[17px] leading-8 text-white/82">
                  从简历库里挑候选人，从 JD 库里挑岗位，让 AI 扮演候选人，你来完成一场真正有反馈的面试训练。
                </p>
              </div>

              <div class="mt-10 grid gap-4 sm:grid-cols-3">
                <div class="rounded-2xl border border-white/16 bg-white/10 px-4 py-4">
                  <div class="text-sm text-white/65">可用岗位</div>
                  <div class="mt-2 text-3xl font-semibold">{{ jds.length }}</div>
                </div>
                <div class="rounded-2xl border border-white/16 bg-white/10 px-4 py-4">
                  <div class="text-sm text-white/65">可练候选人</div>
                  <div class="mt-2 text-3xl font-semibold">{{ resumes.length }}</div>
                </div>
                <div class="rounded-2xl border border-white/16 bg-white/10 px-4 py-4">
                  <div class="text-sm text-white/65">训练目标</div>
                  <div class="mt-2 text-lg font-semibold">提问能力提升</div>
                </div>
              </div>
            </div>

            <div class="bg-[#f8fbff] px-8 py-8">
              <div class="flex items-center justify-between gap-4">
                <div>
                  <div class="text-sm font-medium text-[#3970e9]">Session Brief</div>
                  <h2 class="mt-2 text-[28px] font-bold text-[#15213f]">先定训练组合，再开始实战</h2>
                </div>
                <button class="rounded-full border border-[#d8e4ff] bg-white px-4 py-2 text-sm font-medium text-[#3f4c67] transition hover:border-[#8fb0ff] hover:text-[#2758d8]" @click="loadResources">
                  刷新资源
                </button>
              </div>

              <div class="mt-8 space-y-4">
                <div class="rounded-2xl border border-[#dbe6fb] bg-white px-5 py-4">
                  <div class="text-xs font-semibold uppercase tracking-[0.18em] text-[#7f8daa]">01 Candidate</div>
                  <div class="mt-3 text-lg font-semibold text-[#16213d]">{{ selectedResume?.name || '请选择候选人' }}</div>
                  <p class="mt-1 text-sm leading-7 text-[#60708f]">挑一个你想练的候选人，系统会按简历背景扮演他。</p>
                </div>
                <div class="rounded-2xl border border-[#dbe6fb] bg-white px-5 py-4">
                  <div class="text-xs font-semibold uppercase tracking-[0.18em] text-[#7f8daa]">02 Position</div>
                  <div class="mt-3 text-lg font-semibold text-[#16213d]">{{ selectedJd?.name || '请选择岗位 JD' }}</div>
                  <p class="mt-1 text-sm leading-7 text-[#60708f]">岗位要求会决定你这场训练应当问什么、追什么、卡什么点。</p>
                </div>
                <div class="rounded-2xl border border-[#dbe6fb] bg-white px-5 py-4">
                  <div class="text-xs font-semibold uppercase tracking-[0.18em] text-[#7f8daa]">03 Output</div>
                  <div class="mt-3 text-lg font-semibold text-[#16213d]">训练结束后自动生成复盘报告</div>
                  <p class="mt-1 text-sm leading-7 text-[#60708f]">系统会给出岗位覆盖、追问深度、案例挖掘、面试节奏和提问结构评分。</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div class="mt-8 grid gap-8 xl:grid-cols-[1.15fr_0.85fr]">
          <section class="space-y-6">
            <div v-if="error" class="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-600">
              {{ error }}
            </div>

            <div class="rounded-[26px] border border-[#dce7fb] bg-white p-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
              <div class="flex items-center justify-between gap-4">
                <div>
                  <h3 class="text-[24px] font-semibold text-[#16213d]">训练配置</h3>
                  <p class="mt-2 text-sm text-[#6a7894]">先选岗位和候选人，再决定这轮训练要练哪一种面试节奏。</p>
                </div>
                <div class="rounded-full bg-[#edf4ff] px-4 py-2 text-sm font-medium text-[#3a66d8]">
                  {{ loading ? '资源加载中' : '已就绪' }}
                </div>
              </div>

              <div v-if="loading" class="py-16 text-center text-[#7a88a4]">
                <div class="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-[#8fb0ff] border-t-transparent"></div>
                <p class="mt-4 text-sm">正在同步训练资源...</p>
              </div>

              <div v-else class="mt-8 space-y-8">
                <div>
                  <div class="mb-4 flex items-center justify-between">
                    <h4 class="text-base font-semibold text-[#16213d]">选择岗位 JD</h4>
                    <span class="text-sm text-[#7b88a3]">{{ jds.length }} 个岗位</span>
                  </div>
                  <div class="grid gap-3 md:grid-cols-2">
                    <button
                      v-for="jd in jds"
                      :key="jd.id"
                      type="button"
                      :class="[
                        'rounded-2xl border px-4 py-4 text-left transition',
                        selectedJdId === jd.id
                          ? 'border-[#4c7fff] bg-[#eef4ff] shadow-[0_10px_24px_rgba(76,127,255,0.12)]'
                          : 'border-[#dde6f7] bg-[#fbfdff] hover:border-[#b3c9ff] hover:bg-white'
                      ]"
                      @click="selectedJdId = jd.id"
                    >
                      <div class="flex items-start justify-between gap-3">
                        <div>
                          <div class="text-base font-semibold text-[#15213f]">{{ jd.name }}</div>
                          <div class="mt-1 text-sm text-[#66758f]">{{ jd.category || '未分类' }}<span v-if="jd.location"> · {{ jd.location }}</span></div>
                        </div>
                        <span :class="selectedJdId === jd.id ? 'bg-[#2f6df6] text-white' : 'bg-[#eef3ff] text-[#5976b6]'" class="rounded-full px-3 py-1 text-xs font-semibold">
                          {{ jd.recruitment_type || '岗位' }}
                        </span>
                      </div>
                      <p class="mt-3 line-clamp-2 text-sm leading-6 text-[#61718c]">{{ jd.requirements || jd.responsibilities || '暂无岗位描述' }}</p>
                    </button>
                  </div>
                </div>

                <div>
                  <div class="mb-4 flex items-center justify-between">
                    <h4 class="text-base font-semibold text-[#16213d]">选择候选人简历</h4>
                    <span class="text-sm text-[#7b88a3]">{{ resumes.length }} 份简历</span>
                  </div>
                  <div class="grid gap-3 md:grid-cols-2">
                    <button
                      v-for="resume in resumes"
                      :key="resume.id"
                      type="button"
                      :class="[
                        'rounded-2xl border px-4 py-4 text-left transition',
                        selectedResumeId === resume.id
                          ? 'border-[#4c7fff] bg-[#eef4ff] shadow-[0_10px_24px_rgba(76,127,255,0.12)]'
                          : 'border-[#dde6f7] bg-[#fbfdff] hover:border-[#b3c9ff] hover:bg-white'
                      ]"
                      @click="selectedResumeId = resume.id"
                    >
                      <div class="flex items-start gap-3">
                        <div class="min-w-0 flex-1">
                          <div class="line-clamp-2 text-base font-semibold leading-6 text-[#15213f]">{{ resume.name || '未命名候选人' }}</div>
                          <div class="mt-1 truncate text-sm text-[#66758f]">{{ resume.target_position || '未填写意向岗位' }}</div>
                        </div>
                        <span
                          :class="selectedResumeId === resume.id ? 'bg-[#17305f] text-white' : resume.parse_status === 'success' ? 'bg-[#eef9f2] text-[#2f8f55]' : 'bg-[#f3f6ff] text-[#5976b6]'"
                          class="shrink-0 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold leading-none"
                        >
                          {{ resume.parse_status === 'success' ? '已解析' : '待补全' }}
                        </span>
                      </div>
                      <p class="mt-3 line-clamp-2 text-sm leading-6 text-[#61718c]">{{ resume.skills || '暂无技能标签' }}</p>
                    </button>
                  </div>
                </div>

                <div class="grid gap-6 lg:grid-cols-2">
                  <div>
                    <h4 class="text-base font-semibold text-[#16213d]">训练模式</h4>
                    <div class="mt-4 space-y-3">
                      <button
                        v-for="mode in trainingModes"
                        :key="mode.value"
                        type="button"
                        :class="[
                          'w-full rounded-2xl border px-4 py-4 text-left transition',
                          trainingMode === mode.value
                            ? 'border-[#17305f] bg-[#17305f] text-white'
                            : 'border-[#dde6f7] bg-[#fbfdff] text-[#1c2845] hover:border-[#b3c9ff]'
                        ]"
                        @click="trainingMode = mode.value"
                      >
                        <div class="text-sm font-semibold">{{ mode.title }}</div>
                        <div :class="trainingMode === mode.value ? 'text-white/72' : 'text-[#66758f]'" class="mt-1 text-sm leading-6">{{ mode.desc }}</div>
                      </button>
                    </div>
                  </div>

                  <div>
                    <h4 class="text-base font-semibold text-[#16213d]">候选人状态</h4>
                    <div class="mt-4 space-y-3">
                      <button
                        v-for="style in styleOptions"
                        :key="style.value"
                        type="button"
                        :class="[
                          'w-full rounded-2xl border px-4 py-4 text-left transition',
                          candidateStyle === style.value
                            ? 'border-[#2e7a54] bg-[#effbf4] text-[#173a2b]'
                            : 'border-[#dde6f7] bg-[#fbfdff] text-[#1c2845] hover:border-[#b6ddc7]'
                        ]"
                        @click="candidateStyle = style.value"
                      >
                        <div class="text-sm font-semibold">{{ style.title }}</div>
                        <div :class="candidateStyle === style.value ? 'text-[#487461]' : 'text-[#66758f]'" class="mt-1 text-sm leading-6">{{ style.desc }}</div>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <aside class="space-y-6">
            <section class="rounded-[26px] border border-[#dce7fb] bg-white p-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-sm font-medium text-[#3970e9]">Live Preview</div>
                  <h3 class="mt-2 text-[24px] font-semibold text-[#16213d]">本轮训练画像</h3>
                </div>
                <div class="rounded-full bg-[#eef4ff] px-4 py-2 text-sm font-medium text-[#355fd6]">
                  {{ trainingMode }}
                </div>
              </div>

              <div class="mt-6 rounded-3xl bg-[linear-gradient(180deg,#f7faff_0%,#eef5ff_100%)] p-5">
                <div class="flex items-center gap-4">
                  <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#17305f] text-lg font-bold text-white">
                    {{ selectedResume?.name?.slice(0, 1) || '候' }}
                  </div>
                  <div>
                    <div class="text-xl font-semibold text-[#16213d]">{{ selectedResume?.name || '请选择候选人' }}</div>
                    <div class="mt-1 text-sm text-[#62718c]">{{ selectedJd?.name || '请选择岗位 JD' }}</div>
                  </div>
                </div>

                <div v-if="fitSignals.length" class="mt-5 flex flex-wrap gap-2">
                  <span v-for="item in fitSignals" :key="item" class="rounded-full bg-white px-3 py-1.5 text-sm text-[#4d5d7c] shadow-sm">
                    {{ item }}
                  </span>
                </div>

                <div class="mt-6 grid gap-5">
                  <div>
                    <div class="text-sm font-semibold text-[#1b2742]">岗位考察重点</div>
                    <ul class="mt-3 space-y-2">
                      <li v-for="item in jdHighlights" :key="item" class="flex gap-3 text-sm leading-6 text-[#5e6d88]">
                        <span class="mt-2 h-1.5 w-1.5 rounded-full bg-[#3a66d8]"></span>
                        <span>{{ item }}</span>
                      </li>
                      <li v-if="!jdHighlights.length" class="text-sm text-[#8b98b1]">选择 JD 后会在这里生成本轮重点。</li>
                    </ul>
                  </div>

                  <div>
                    <div class="text-sm font-semibold text-[#1b2742]">候选人可追问切口</div>
                    <div class="mt-3 flex flex-wrap gap-2">
                      <span v-for="item in resumeHighlights" :key="item" class="rounded-full border border-[#d8e5ff] bg-white px-3 py-1.5 text-sm text-[#4d5d7c]">
                        {{ item }}
                      </span>
                      <span v-if="!resumeHighlights.length" class="text-sm text-[#8b98b1]">选择简历后会显示候选人可深挖的标签。</span>
                    </div>
                  </div>
                </div>
              </div>

              <button
                :disabled="!canStart"
                class="mt-6 flex w-full items-center justify-center gap-3 rounded-2xl bg-[linear-gradient(135deg,#17305f_0%,#2e74ff_100%)] px-5 py-4 text-base font-semibold text-white shadow-[0_18px_36px_rgba(46,116,255,0.24)] transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-50"
                @click="startTraining"
              >
                <i class="fa fa-play-circle-o text-lg"></i>
                {{ starting ? '正在创建训练会话...' : '开始这轮面试官训练' }}
              </button>
            </section>

            <section class="rounded-[26px] border border-[#dce7fb] bg-white p-6 shadow-[0_14px_36px_rgba(80,112,178,0.10)]">
              <div class="text-sm font-medium text-[#3970e9]">How It Works</div>
              <div class="mt-5 space-y-4">
                <div class="flex gap-4">
                  <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#eef4ff] text-sm font-bold text-[#2f6df6]">1</div>
                  <div>
                    <div class="text-base font-semibold text-[#16213d]">挑训练对象</div>
                    <p class="mt-1 text-sm leading-6 text-[#687793]">JD 决定岗位标准，简历决定候选人的真实回答边界。</p>
                  </div>
                </div>
                <div class="flex gap-4">
                  <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#eefbf4] text-sm font-bold text-[#2e7a54]">2</div>
                  <div>
                    <div class="text-base font-semibold text-[#16213d]">AI 扮演候选人</div>
                    <p class="mt-1 text-sm leading-6 text-[#687793]">你负责发问、追问、控场，系统根据简历背景实时回应。</p>
                  </div>
                </div>
                <div class="flex gap-4">
                  <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#f4f0ff] text-sm font-bold text-[#775ae0]">3</div>
                  <div>
                    <div class="text-base font-semibold text-[#16213d]">自动训练复盘</div>
                    <p class="mt-1 text-sm leading-6 text-[#687793]">训练结束后，系统会评价你的问题质量和面试推进能力。</p>
                  </div>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </main>
  </div>
</template>
