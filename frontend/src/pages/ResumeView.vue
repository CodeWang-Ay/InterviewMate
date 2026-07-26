<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const resume = ref(null)
const data = ref({})
const loading = ref(true)
const error = ref('')
const showOriginal = ref(false)
const fileUrl = ref('')

onMounted(loadResume)

async function loadResume() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    const filename = route.query.filename || ''
    const response = await fetch(`/api/plans/my-resume?filename=${encodeURIComponent(filename)}`, { headers })
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || '简历不存在')
    resume.value = await response.json()
    try { data.value = JSON.parse(resume.value.structured_data || '{}') } catch (_) { data.value = {} }
    const fileResponse = await fetch(`/api/plans/my-resume/file?filename=${encodeURIComponent(resume.value.file_path || filename)}`, { headers })
    if (fileResponse.ok) fileUrl.value = URL.createObjectURL(await fileResponse.blob())
  } catch (e) { error.value = e.message || '简历加载失败' } finally { loading.value = false }
}

function v(item, keys) {
  for (const key of keys) if (item?.[key] !== undefined && String(item[key]).trim()) return item[key]
  return '-'
}

function arr(val) { return Array.isArray(val) ? val : (val && typeof val === 'object' ? [val] : []) }
function txt(val) { return val === undefined || val === null || val === '' ? '-' : typeof val === 'string' ? val : JSON.stringify(val, null, 2) }

function sectionFields(section) {
  if (section === '教育经历') return [['学校', '院校', '学校'], ['专业', '所学专业', '专业'], ['学位', '学位名称', '学位'], ['学历', '学业水平', '学历'], ['时间', null, null, (item) => [v(item, ['开始时间', '入学时间']), v(item, ['结束时间', '毕业时间'])].filter(Boolean).join(' ~ ') || '-']]
  const isProj = section === '项目经历'
  return [
    [isProj ? '项目' : '公司', isProj ? '项目名称' : '公司名称', isProj ? '项目名' : '公司', (item) => v(item, isProj ? ['项目名称', '项目名', '名称'] : ['公司', '公司名称'])],
    [isProj ? '角色' : '职位', '角色', '职位', (item) => v(item, isProj ? ['角色', '职责'] : ['职位', '岗位'])],
    ['时间', null, null, (item) => [v(item, ['开始时间', '起始时间']), v(item, ['结束时间', '终止时间'])].filter(Boolean).join(' ~ ') || '-'],
    ['描述', null, null, (item) => v(item, ['描述', '工作内容', '工作描述', '主要职责', '岗位职责', '项目描述', '项目内容', '项目成果', '个人贡献'])],
  ]
}

const sectionIcons = { '教育经历': 'fa-graduation-cap', '工作经历': 'fa-briefcase', '项目经历': 'fa-cubes' }
const sectionColors = { '教育经历': 'border-l-blue-500', '工作经历': 'border-l-emerald-500', '项目经历': 'border-l-violet-500' }
const sectionBgs = { '教育经历': 'bg-blue-50 text-blue-600', '工作经历': 'bg-emerald-50 text-emerald-600', '项目经历': 'bg-violet-50 text-violet-600' }
</script>

<template>
  <div class="min-h-screen bg-[#f3f5f8] text-[#202838]">
    <!-- header -->
    <header class="sticky top-0 z-20 border-b border-[#e5eaf1] bg-white/95 backdrop-blur">
      <div class="mx-auto flex h-16 max-w-[1040px] items-center justify-between px-6">
        <button class="flex items-center gap-1.5 text-sm font-semibold text-[#667085] hover:text-[#4776ff]" @click="router.push('/user')">
          <i class="fa fa-arrow-left"></i> 返回个人中心
        </button>
        <div class="flex items-center gap-3">
          <span class="hidden max-w-[320px] truncate text-sm font-bold text-[#475467] sm:block">{{ resume?.original_name || '我的简历' }}</span>
          <button class="rounded-lg border border-[#dce5f2] px-3 py-2 text-sm font-bold text-[#475467] hover:bg-[#f5f7fa]" @click="showOriginal = !showOriginal">
            <i :class="['fa mr-1', showOriginal ? 'fa-table' : 'fa-file-pdf-o']"></i>{{ showOriginal ? '解析视图' : '查看原文件' }}
          </button>
        </div>
      </div>
    </header>

    <main :class="['mx-auto px-4 py-4 sm:px-6', showOriginal ? 'max-w-[1400px]' : 'max-w-[1040px] py-8 sm:px-8']">
      <div v-if="loading" class="flex items-center justify-center rounded-2xl bg-white py-24 text-[#98a2b3]">
        <i class="fa fa-spinner fa-spin mr-3"></i>正在加载简历...
      </div>
      <div v-else-if="error" class="rounded-2xl bg-white py-24 text-center">
        <i class="fa fa-exclamation-circle text-4xl text-red-300 mb-3 block"></i>
        <p class="text-red-500">{{ error }}</p>
      </div>

      <!-- PDF 原文件视图 -->
      <div v-else-if="showOriginal" class="h-[calc(100vh-80px)] overflow-hidden rounded-2xl bg-[#303030] shadow-[0_18px_50px_rgba(15,35,80,0.12)]">
        <embed v-if="fileUrl" :src="`${fileUrl}#view=FitH`" type="application/pdf" class="h-full w-full" />
        <div v-else class="flex h-full items-center justify-center text-white/50">暂无简历文件</div>
      </div>

      <!-- 解析视图 -->
      <article v-else class="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        <!-- 头部卡片 -->
        <section class="relative overflow-hidden bg-gradient-to-br from-slate-800 via-slate-900 to-indigo-950 px-8 py-10 sm:px-12">
          <div class="absolute right-0 top-0 h-64 w-64 translate-x-1/3 -translate-y-1/3 rounded-full bg-indigo-500/10 blur-3xl"></div>
          <div class="absolute bottom-0 left-1/2 h-48 w-96 -translate-x-1/2 translate-y-1/2 rounded-full bg-cyan-500/8 blur-3xl"></div>
          <div class="relative flex flex-wrap items-start justify-between gap-6">
            <div class="flex items-center gap-5">
              <div class="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-white/10 text-3xl font-black text-white shadow-inner ring-1 ring-white/10">
                {{ (v(data['基础信息'], ['姓名']) || '?').slice(0, 1) }}
              </div>
              <div class="min-w-0">
                <h1 class="text-3xl font-black tracking-tight text-white sm:text-4xl">{{ v(data['基础信息'], ['姓名']) || resume?.name || '候选人' }}</h1>
                <p class="mt-1.5 text-base font-semibold text-white/60">{{ v(data['基础信息'], ['意向岗位', '岗位名称']) || resume?.target_position || '求职者' }}</p>
              </div>
            </div>
            <router-link
              :to="{ path: '/resume-edit', query: { filename: route.query.filename || '' } }"
              class="inline-flex items-center gap-2 rounded-xl border border-white/20 px-5 py-2.5 text-sm font-bold text-white/80 backdrop-blur transition hover:bg-white/10 hover:text-white"
            >
              <i class="fa fa-pencil"></i>编辑简历
            </router-link>
          </div>
          <!-- 快捷联系方式 -->
          <div class="relative mt-8 flex flex-wrap gap-x-10 gap-y-3 rounded-2xl bg-white/5 px-6 py-4 text-sm backdrop-blur">
            <span class="flex items-center gap-2 text-white/70"><i class="fa fa-phone w-4 text-center text-white/40"></i>{{ v(data['基础信息'], ['电话', '手机']) }}</span>
            <span class="flex items-center gap-2 text-white/70"><i class="fa fa-envelope w-4 text-center text-white/40"></i>{{ v(data['基础信息'], ['邮箱', '电子邮箱']) }}</span>
            <span class="flex items-center gap-2 text-white/70"><i class="fa fa-map-marker w-4 text-center text-white/40"></i>{{ v(data['基础信息'], ['地址', '现居住地']) }}</span>
            <span class="flex items-center gap-2 text-white/70"><i class="fa fa-venus-mars w-4 text-center text-white/40"></i>{{ v(data['基础信息'], ['性别']) }}</span>
            <span class="flex items-center gap-2 text-white/70"><i class="fa fa-calendar w-4 text-center text-white/40"></i>{{ v(data['基础信息'], ['年龄', '出生年月']) }}</span>
          </div>
        </section>

        <!-- 正文 -->
        <div class="px-8 py-8 sm:px-12">
          <!-- 自我评价 -->
          <div v-if="v(data, ['自我评价']) !== '-'" class="mb-10">
            <h2 class="mb-4 flex items-center gap-2.5 text-base font-black tracking-wide text-slate-800">
              <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-50 text-sm text-amber-500"><i class="fa fa-star"></i></span>自我评价
            </h2>
            <p class="leading-7 text-slate-600 text-sm">{{ v(data, ['自我评价']) }}</p>
          </div>

          <!-- 教育/工作/项目经历 -->
          <template v-for="section in ['教育经历', '工作经历', '项目经历']" :key="section">
            <div v-if="arr(data[section]).length" class="mb-10">
              <h2 class="mb-5 flex items-center gap-2.5 text-base font-black tracking-wide text-slate-800">
                <span :class="['flex h-7 w-7 items-center justify-center rounded-lg text-sm', sectionBgs[section]]"><i :class="['fa', sectionIcons[section]]"></i></span>{{ section }}
              </h2>
              <div class="space-y-4">
                <div
                  v-for="(item, idx) in arr(data[section])"
                  :key="idx"
                  :class="['rounded-xl border border-slate-100 bg-[#fafbfd] p-5 pl-6 border-l-4', sectionColors[section]]"
                >
                  <div class="flex flex-wrap items-center gap-2 mb-3">
                    <span class="text-base font-bold text-slate-800">{{ v(item, section === '教育经历' ? ['学校', '院校'] : section === '工作经历' ? ['公司', '公司名称'] : ['项目名称', '项目名']) }}</span>
                    <span v-if="v(item, section === '教育经历' ? ['专业', '所学专业'] : section === '工作经历' ? ['职位', '岗位'] : ['角色', '职责']) !== '-'" class="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">{{ v(item, section === '教育经历' ? ['专业', '所学专业'] : section === '工作经历' ? ['职位', '岗位'] : ['角色', '职责']) }}</span>
                  </div>
                  <div class="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-400 mb-2">
                    <span v-if="v(item, ['开始时间', '入学时间', '起始时间']) !== '-' || v(item, ['结束时间', '毕业时间', '终止时间']) !== '-'">
                      <i class="fa fa-calendar mr-1"></i>{{ [v(item, ['开始时间', '入学时间', '起始时间']), v(item, ['结束时间', '毕业时间', '终止时间'])].filter(x => x !== '-').join(' ~ ') }}
                    </span>
                    <span v-if="section === '教育经历' && v(item, ['学位', '学位名称']) !== '-'"><i class="fa fa-certificate mr-1"></i>{{ v(item, ['学位', '学位名称']) }}</span>
                    <span v-if="section === '教育经历' && v(item, ['学历', '学业水平']) !== '-'"><i class="fa fa-bookmark mr-1"></i>{{ v(item, ['学历', '学业水平']) }}</span>
                  </div>
                  <p v-if="v(item, ['描述', '工作描述', '项目描述', '工作内容', '主要职责']) !== '-'" class="mt-2 text-sm leading-7 text-slate-500">{{ v(item, ['描述', '工作描述', '项目描述', '工作内容', '主要职责']) }}</p>
                </div>
              </div>
            </div>
          </template>

          <!-- 无内容提示 -->
          <div v-if="!arr(data['教育经历']).length && !arr(data['工作经历']).length && !arr(data['项目经历']).length && v(data, ['自我评价']) === '-'" class="py-16 text-center text-sm text-[#98a2b3]">
            <i class="fa fa-file-text-o text-4xl mb-3 block text-[#dce5f2]"></i>
            暂未解析到详细履历，可上传简历文件自动解析
          </div>
        </div>
      </article>
    </main>
  </div>
</template>
