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
const editing = ref(false)

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
  } catch (e) {
    error.value = e.message || '简历加载失败'
  } finally {
    loading.value = false
  }
}

function value(item, keys) {
  for (const key of keys) if (item?.[key] !== undefined && String(item[key]).trim()) return item[key]
  return '-'
}

function list(value) {
  if (Array.isArray(value)) return value
  return value && typeof value === 'object' ? [value] : []
}

function text(value) {
  return value === undefined || value === null || value === '' ? '-' : typeof value === 'string' ? value : JSON.stringify(value, null, 2)
}

function rows(section, item) {
  if (section === '教育经历') return [
    [['学位', value(item, ['学位', '学位名称'])], ['学历', value(item, ['学历', '学业水平'])]],
    [['学校', value(item, ['学校', '院校'])], ['专业', value(item, ['专业', '所学专业'])]],
    [['开始时间', value(item, ['开始时间', '入学时间'])], ['结束时间', value(item, ['结束时间', '毕业时间'])]],
  ]
  const project = section === '项目经历'
  return [
    [[project ? '项目名称' : '公司', value(item, project ? ['项目名称', '项目名', '名称'] : ['公司', '公司名称'])], [project ? '角色' : '职位', value(item, project ? ['角色', '职责'] : ['职位', '岗位'])]],
    [['开始时间', value(item, ['开始时间', '起始时间'])], ['结束时间', value(item, ['结束时间', '终止时间'])]],
    [['描述', value(item, ['描述', '工作内容', '工作描述', '主要职责', '岗位职责', '项目描述', '项目内容', '项目成果', '个人贡献'])]],
  ]
}
</script>

<template>
  <div class="min-h-screen bg-[#f3f5f8] text-[#202838]">
    <header class="sticky top-0 z-20 border-b border-[#e5eaf1] bg-white/95 backdrop-blur">
      <div class="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-6">
        <button class="font-semibold text-[#475467] hover:text-[#4776ff]" @click="router.push('/user')"><i class="fa fa-arrow-left mr-2"></i>返回个人中心</button>
        <div class="flex items-center gap-3">
          <span class="hidden max-w-[420px] truncate text-sm font-bold sm:block">{{ resume?.original_name || '我的简历' }}</span>
          <button class="rounded-lg border border-[#dce5f2] px-3 py-2 text-sm font-bold text-[#475467]" @click="showOriginal = !showOriginal"><i class="fa fa-file-pdf-o mr-1"></i>{{ showOriginal ? '查看解析' : '查看原文件' }}</button>
          <button class="rounded-lg bg-[#4776ff] px-4 py-2 text-sm font-bold text-white"><i class="fa fa-pencil mr-1"></i>编辑简历</button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-[1040px] px-4 py-8 sm:px-8">
      <div v-if="loading" class="rounded-2xl bg-white p-16 text-center text-[#667085]">正在加载简历...</div>
      <div v-else-if="error" class="rounded-2xl bg-white p-16 text-center text-red-500">{{ error }}</div>
      <div v-else-if="showOriginal" class="h-[calc(100vh-150px)] overflow-hidden rounded-2xl bg-[#303030] shadow-[0_18px_50px_rgba(15,35,80,0.12)]">
        <embed v-if="fileUrl" :src="`${fileUrl}#view=FitH`" type="application/pdf" class="h-full w-full" />
      </div>
      <article v-else class="overflow-hidden rounded-2xl bg-white shadow-[0_18px_50px_rgba(15,35,80,0.10)]">
        <section class="bg-[linear-gradient(135deg,#eaf2ff,#ffffff_55%,#eaf9f5)] px-8 py-7 sm:px-14">
          <div class="flex items-center gap-3 text-sm font-bold text-[#344054]">
            <span class="text-xl">我的简历</span><span class="text-[#4776ff]">•</span><span class="font-normal text-[#667085]">最近更新：{{ resume?.updated_at || resume?.created_at || '刚刚' }}</span>
          </div>
          <div class="mt-6 flex items-center justify-between gap-6">
            <div class="flex min-w-0 items-center gap-5">
              <div class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-white text-2xl font-black text-[#4776ff] shadow-sm">{{ (value(data['基础信息'], ['姓名']) || '候').slice(0, 1) }}</div>
              <div class="min-w-0"><h1 class="truncate text-3xl font-black sm:text-4xl">{{ value(data['基础信息'], ['姓名']) || resume?.name || '候选人' }}</h1><p class="mt-1 text-base text-[#667085]">{{ value(data['基础信息'], ['岗位名称', '意向岗位']) || resume?.target_position || '求职者' }}</p></div>
            </div>
            <button class="hidden rounded-full border border-[#4776ff] px-7 py-3 text-sm font-bold text-[#4776ff] transition hover:bg-[#4776ff] hover:text-white sm:inline-flex" @click="editing = !editing"><i class="fa fa-pencil mr-2"></i>{{ editing ? '完成编辑' : '编辑简历' }}</button>
          </div>
          <div class="mt-7 grid gap-3 border-t border-white/80 pt-5 text-sm text-[#475467] sm:grid-cols-3">
            <span><strong class="mr-2 text-[#202838]">电话</strong>{{ value(data['基础信息'], ['电话', '手机']) }}</span><span><strong class="mr-2 text-[#202838]">邮箱</strong>{{ value(data['基础信息'], ['邮箱', '电子邮箱']) }}</span><span><strong class="mr-2 text-[#202838]">地址</strong>{{ value(data['基础信息'], ['地址', '现居住地']) }}</span>
          </div>
        </section>
        <section class="px-8 py-8 sm:px-14">
          <div class="mb-8">
            <h2 class="mb-3 text-lg font-black">基础信息</h2>
            <div class="grid gap-x-12 gap-y-4 border-t border-[#edf1f7] pt-5 text-sm sm:grid-cols-2"><div>籍贯：{{ value(data['基础信息'], ['籍贯', '户籍', '出生地']) }}</div><div>年龄：{{ value(data['基础信息'], ['年龄']) }}</div><div class="sm:col-span-2">自我评价：{{ value(data, ['自我评价']) }}</div></div>
          </div>
          <template v-for="section in ['教育经历', '工作经历', '项目经历']" :key="section">
            <section v-if="list(data[section]).length" class="mb-9">
              <h2 class="mb-5 text-lg font-black">{{ section }}</h2>
              <div v-for="(item, itemIndex) in list(data[section])" :key="`${section}-${itemIndex}`" class="border-t border-[#edf1f7] py-5">
                <div v-for="(row, rowIndex) in rows(section, item)" :key="rowIndex" class="grid gap-3 py-2 text-sm sm:grid-cols-[110px_1fr_110px_1fr]">
                  <template v-if="row.length === 2"><span class="font-bold text-[#667085]">{{ row[0][0] }}</span><span class="whitespace-pre-wrap">{{ text(row[0][1]) }}</span><span class="font-bold text-[#667085]">{{ row[1][0] }}</span><span class="whitespace-pre-wrap">{{ text(row[1][1]) }}</span></template>
                  <template v-else><span class="font-bold text-[#667085]">描述</span><span class="whitespace-pre-wrap leading-7 sm:col-span-3">{{ text(row[0][1]) }}</span></template>
                </div>
              </div>
            </section>
          </template>
        </section>
      </article>
    </main>
  </div>
</template>
