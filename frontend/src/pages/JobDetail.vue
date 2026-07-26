<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const job = ref(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const id = route.params.id
    const res = await fetch(`/api/jds/public/${id}`)
    if (!res.ok) throw new Error('职位不存在或已下线')
    job.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

function goLogin() {
  router.push('/user/login?redirect=/user')
}

function goList() {
  const type = job.value?.recruitment_type || '社招'
  router.push(type.includes('校') ? '/jobs/campus' : '/jobs/social')
}
</script>

<template>
  <div class="min-h-screen bg-[#f3f5f8] text-[#202838]">
    <!-- header -->
    <header class="sticky top-0 z-30 border-b border-white/10 bg-[#071c22] text-white shadow-[0_8px_24px_rgba(7,28,34,0.18)]">
      <div class="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-6">
        <button class="flex items-center gap-3" @click="router.push('/')">
          <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-black text-[#0f9f8f]">AI</span>
          <span class="text-lg font-bold">OPC Mate 招聘</span>
        </button>
        <nav class="hidden items-center gap-8 text-sm font-semibold text-white/80 md:flex">
          <button @click="router.push('/')">首页</button>
          <button @click="router.push('/jobs/social')">社会招聘</button>
          <button @click="router.push('/jobs/campus')">校园招聘</button>
          <button @click="router.push('/about')">了解我们</button>
        </nav>
        <div class="flex items-center gap-3">
          <button class="rounded-full border border-white/15 px-4 py-2 text-sm font-semibold text-white/80 hover:bg-white/10" @click="router.push('/user/login')">登录</button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-[960px] px-4 py-10 sm:px-8">
      <div v-if="loading" class="rounded-2xl bg-white p-16 text-center text-[#667085]">正在加载...</div>
      <div v-else-if="error" class="rounded-2xl bg-white p-16 text-center">
        <i class="fa fa-exclamation-circle text-4xl text-red-300 mb-3 block"></i>
        <p class="text-red-500">{{ error }}</p>
        <button class="mt-4 font-bold text-[#4776ff]" @click="router.push('/jobs/social')">返回职位列表</button>
      </div>
      <article v-else class="overflow-hidden rounded-2xl bg-white shadow-[0_12px_40px_rgba(15,35,80,0.08)]">
        <!-- 头部 -->
        <section class="bg-gradient-to-br from-slate-800 via-slate-900 to-indigo-950 px-8 py-10 sm:px-12">
          <div class="flex flex-wrap items-start justify-between gap-6">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-3 mb-3">
                <span class="rounded-md bg-white/10 px-3 py-1 text-sm font-bold text-white/70">{{ job.recruitment_type || '社招' }}</span>
                <span class="rounded-md bg-emerald-500/20 px-3 py-1 text-sm font-bold text-emerald-300">热招中</span>
              </div>
              <h1 class="text-3xl font-black tracking-tight text-white sm:text-4xl">{{ job.name }}</h1>
              <div class="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm text-white/60">
                <span><i class="fa fa-map-marker mr-1.5"></i>{{ job.location || '地点待定' }}</span>
                <span><i class="fa fa-folder-o mr-1.5"></i>{{ job.category || '综合' }}</span>
                <span><i class="fa fa-clock-o mr-1.5"></i>{{ job.experience_required || '不限经验' }}</span>
                <span><i class="fa fa-calendar mr-1.5"></i>发布于 {{ String(job.updated_at || job.created_at || '').slice(0, 10) || '近期' }}</span>
              </div>
            </div>
            <button class="shrink-0 rounded-xl bg-[#11b89f] px-8 py-3.5 text-base font-black text-white hover:bg-[#0d9488] shadow-lg shadow-teal-500/20" @click="goLogin">立即投递</button>
          </div>
        </section>

        <!-- 正文 -->
        <div class="px-8 py-10 sm:px-12 space-y-10">
          <!-- 职位亮点 -->
          <div v-if="job.highlights" class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div v-for="h in job.highlights" :key="h" class="rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 p-4 text-center">
              <span class="text-sm font-bold text-amber-700">{{ h }}</span>
            </div>
          </div>

          <!-- 岗位职责 -->
          <div>
            <h2 class="mb-4 flex items-center gap-2.5 text-lg font-black text-slate-800">
              <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-50 text-sm text-blue-500"><i class="fa fa-list-ul"></i></span>岗位职责
            </h2>
            <div class="rounded-xl border border-slate-100 bg-[#fafbfd] p-6">
              <pre class="whitespace-pre-wrap font-sans text-sm leading-7 text-slate-600">{{ job.responsibilities || '暂无详细描述' }}</pre>
            </div>
          </div>

          <!-- 任职要求 -->
          <div>
            <h2 class="mb-4 flex items-center gap-2.5 text-lg font-black text-slate-800">
              <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-50 text-sm text-emerald-500"><i class="fa fa-check-circle"></i></span>任职要求
            </h2>
            <div class="rounded-xl border border-slate-100 bg-[#fafbfd] p-6">
              <pre class="whitespace-pre-wrap font-sans text-sm leading-7 text-slate-600">{{ job.requirements || '暂无详细要求' }}</pre>
            </div>
          </div>

          <!-- 其他信息 -->
          <div v-if="job.benefits || job.salary_range" class="rounded-xl border border-slate-100 bg-[#fafbfd] p-6">
            <h3 class="mb-4 text-base font-black text-slate-800">薪酬福利</h3>
            <div class="flex flex-wrap gap-3">
              <span v-if="job.salary_range" class="rounded-full bg-green-50 px-4 py-2 text-sm font-bold text-green-700">{{ job.salary_range }}</span>
              <span v-if="job.benefits" class="text-sm text-slate-600">{{ job.benefits }}</span>
              <span v-if="!job.salary_range && !job.benefits" class="text-sm text-slate-400">具体薪资福利以面试沟通为准</span>
            </div>
          </div>
        </div>

        <!-- 底部操作 -->
        <div class="sticky bottom-0 border-t border-slate-100 bg-white/95 backdrop-blur px-8 py-5 sm:px-12 flex items-center justify-between gap-4">
          <button class="text-sm font-semibold text-[#667085] hover:text-[#4776ff]" @click="goList"><i class="fa fa-arrow-left mr-1.5"></i>返回职位列表</button>
          <div class="flex gap-3">
            <button class="rounded-lg border border-[#dce5f2] px-5 py-2.5 text-sm font-bold text-[#475467] hover:bg-[#f5f7fa]"><i class="fa fa-share-alt mr-1.5"></i>分享</button>
            <button class="rounded-xl bg-[#11b89f] px-8 py-2.5 text-base font-black text-white hover:bg-[#0d9488]" @click="goLogin">立即投递</button>
          </div>
        </div>
      </article>
    </main>
  </div>
</template>
