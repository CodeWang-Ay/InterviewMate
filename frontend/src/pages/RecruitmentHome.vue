<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import homePageImage from '../../images/home_page.png'
import CandidateNavbar from '../components/CandidateNavbar.vue'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const recruitmentType = ref('社招')
const showRecruitmentPicker = ref(false)
const selectedCategory = ref('')
const selectedLocation = ref('')
const jobs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const paginationItems = computed(() => {
  const last = totalPages.value
  const current = page.value
  if (last <= 7) return Array.from({ length: last }, (_, index) => index + 1)
  if (current <= 4) return [1, 2, 3, 4, 5, 'ellipsis', last]
  if (current >= last - 3) return [1, 'ellipsis', last - 4, last - 3, last - 2, last - 1, last]
  return [1, 'ellipsis', current - 1, current, current + 1, 'ellipsis-end', last]
})
const username = ref('')
const nickname = ref('')
const role = ref('')

const categories = ['技术', '产品', '政企', '销售', '综合']
const locations = ['北京', '上海', '深圳', '广州', '杭州', '成都']
const heroTags = ['大模型', 'AI 面试', 'RAG', '语音交互', '招聘流程', '候选人体验']

const displayedName = computed(() => nickname.value || username.value || '')
const isLoggedIn = computed(() => Boolean(username.value || localStorage.getItem('token')))
const centerPath = computed(() => role.value === 'candidate' ? '/user' : '/admin/user-center')
const recommendedJobs = computed(() => jobs.value.slice(0, 3))
const isHomePage = computed(() => route.path === '/')

onMounted(() => {
  readUser()
  syncRecruitmentTypeFromRoute()
  syncFiltersFromRoute()
  if (!isHomePage.value) loadJobs()
  loadFavorites()
})

watch(() => [route.path, route.query.page, route.query.search, route.query.category, route.query.location], () => {
  syncRecruitmentTypeFromRoute()
  syncFiltersFromRoute()
  if (!isHomePage.value) loadJobs()
})

function syncFiltersFromRoute() {
  keyword.value = String(route.query.search || '')
  selectedCategory.value = String(route.query.category || '')
  selectedLocation.value = String(route.query.location || '')
  page.value = Math.max(1, Number.parseInt(String(route.query.page || '1'), 10) || 1)
}

function currentQuery(nextPage = page.value) {
  const query = {}
  if (keyword.value.trim()) query.search = keyword.value.trim()
  if (selectedCategory.value) query.category = selectedCategory.value
  if (selectedLocation.value) query.location = selectedLocation.value
  if (nextPage > 1) query.page = String(nextPage)
  return query
}

function replaceListQuery(nextPage = 1) {
  page.value = nextPage
  router.replace({ path: route.path, query: currentQuery(nextPage) })
}

function readUser() {
  try {
    username.value = localStorage.getItem('username') || ''
    nickname.value = localStorage.getItem('nickname') || ''
    role.value = localStorage.getItem('role') || ''
  } catch (_) {
    username.value = ''
    nickname.value = ''
    role.value = ''
  }
}

async function loadJobs() {
  if (isHomePage.value) return
  loading.value = true
  error.value = ''
  try {
    const dbType = recruitmentType.value === '实习' ? '实习生' : recruitmentType.value
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize),
      recruitment_type: dbType,
    })
    if (keyword.value.trim()) params.set('search', keyword.value.trim())
    if (selectedCategory.value) params.set('category', selectedCategory.value)
    if (selectedLocation.value) params.set('location', selectedLocation.value)
    const res = await fetch(`/api/jds/public?${params.toString()}`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '职位加载失败')
    jobs.value = Array.isArray(data.items) ? data.items : []
    total.value = Number(data.total || jobs.value.length)
  } catch (err) {
    error.value = err.message || '职位加载失败'
    jobs.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function selectType(type) {
  recruitmentType.value = type
  showRecruitmentPicker.value = false
  if (type === '校招') router.push('/jobs/campus')
  else if (type === '实习') router.push('/jobs/intern')
  else router.push('/jobs/social')
}

const isCampusModule = computed(() => recruitmentType.value === '校招' || recruitmentType.value === '实习')

function chooseSearchType(type) {
  recruitmentType.value = type
  showRecruitmentPicker.value = false
}

function syncRecruitmentTypeFromRoute() {
  if (route.path === '/jobs/campus') recruitmentType.value = '校招'
  else if (route.path === '/jobs/intern') recruitmentType.value = '实习'
  else recruitmentType.value = '社招'
}

function searchJobs() {
  const path = recruitmentType.value === '校招' ? '/jobs/campus' : recruitmentType.value === '实习' ? '/jobs/intern' : '/jobs/social'
  page.value = 1
  router.push({ path, query: currentQuery(1) })
}

function toggleCategory(item) {
  selectedCategory.value = selectedCategory.value === item ? '' : item
  replaceListQuery(1)
}

function toggleLocation(item) {
  selectedLocation.value = selectedLocation.value === item ? '' : item
  replaceListQuery(1)
}

function resetFilters() {
  keyword.value = ''
  selectedCategory.value = ''
  selectedLocation.value = ''
  replaceListQuery(1)
}

function goPage(nextPage) {
  const target = Math.min(Math.max(1, nextPage), totalPages.value)
  if (target === page.value) return
  replaceListQuery(target)
  window.scrollTo({ top: 560, behavior: 'smooth' })
}

function goLogin(jobId) {
  if (isLoggedIn.value) {
    router.push(jobId ? `/user?apply_job=${jobId}` : '/user')
  } else {
    router.push('/user/login?redirect=/user')
  }
}

// ── 收藏（按候选人账号持久化） ───────────────────────────────

const favorites = ref(new Set())

async function loadFavorites() {
  favorites.value = new Set()
  try { localStorage.removeItem('favorite_jobs') } catch (_) {}
  if (role.value !== 'candidate' || !localStorage.getItem('token')) return
  try {
    const res = await fetch('/api/jds/favorites', { cache: 'no-store' })
    if (!res.ok) return
    const items = await res.json()
    favorites.value = new Set((Array.isArray(items) ? items : []).map(item => Number(item.id)))
  } catch (_) {}
}

async function toggleFavorite(job) {
  if (role.value !== 'candidate' || !localStorage.getItem('token')) {
    router.push({ path: '/user/login', query: { redirect: route.fullPath } })
    return
  }
  const jobId = Number(job.id)
  const wasFavorite = favorites.value.has(jobId)
  const next = new Set(favorites.value)
  if (wasFavorite) next.delete(jobId)
  else next.add(jobId)
  favorites.value = next
  try {
    const res = await fetch(`/api/jds/favorites/${jobId}`, {
      method: wasFavorite ? 'DELETE' : 'POST',
    })
    if (!res.ok) throw new Error('收藏更新失败')
  } catch (error) {
    const rollback = new Set(favorites.value)
    if (wasFavorite) rollback.add(jobId)
    else rollback.delete(jobId)
    favorites.value = rollback
    window.appNotify?.(error.message || '收藏更新失败', 'error')
  }
}
function isFavorite(jobId) {
  return favorites.value.has(Number(jobId))
}

// ── 分享 ──────────────────────────────────────────────────────

async function shareJob(job) {
  const url = `${window.location.origin}/jobs/${job.id}`
  const text = `【${job.name}】${job.location || ''} ｜ ${job.category || ''}\n${url}`
  try {
    if (navigator.share) {
      await navigator.share({ title: job.name, text, url })
    } else {
      await navigator.clipboard.writeText(text)
      alert('职位信息已复制到剪贴板')
    }
  } catch (_) {
    try { await navigator.clipboard.writeText(text); alert('链接已复制') } catch (__) {}
  }
}

function goCenter() {
  router.push(centerPath.value)
}

function jobSummary(job) {
  const text = `${job.responsibilities || ''}`.replace(/\s+/g, ' ').trim()
  return text || '参与核心业务建设，与团队一起探索 AI 招聘与面试体验的更多可能。'
}
</script>

<template>
  <div class="min-h-screen bg-[#f6f7fb] text-[#182033]">
    <CandidateNavbar
      position="fixed"
      :active="isHomePage ? 'home' : recruitmentType === '社招' ? 'social' : 'campus'"
    />

    <section :class="['recruitment-hero relative overflow-hidden bg-[#061819] pt-16 text-white', isHomePage ? 'min-h-screen' : 'min-h-[620px]']">
      <img :src="homePageImage" alt="" class="absolute inset-0 h-full w-full object-cover" />
      <div class="absolute inset-0 bg-[linear-gradient(180deg,rgba(5,15,22,0.54)_0%,rgba(6,24,25,0.34)_45%,rgba(6,24,25,0.64)_100%)]"></div>
      <div class="hero-aurora absolute inset-0"></div>
      <div class="orbit-ring orbit-ring-1 absolute left-1/2 top-[52%] h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/14">
        <span class="orbit-node node-green"></span>
      </div>
      <div class="orbit-ring orbit-ring-2 absolute left-1/2 top-[52%] h-[860px] w-[860px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-white/18">
        <span class="orbit-node node-blue"></span>
        <span class="orbit-label label-1">AI Infra</span>
        <span class="orbit-label label-2">智能面试</span>
      </div>
      <div class="orbit-ring orbit-ring-3 absolute left-1/2 top-[52%] h-[1180px] w-[1180px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dotted border-white/16">
        <span class="orbit-node node-gold"></span>
        <span class="orbit-label label-3">RAG 应用</span>
        <span class="orbit-label label-4">人才档案</span>
      </div>
      <div class="star-field absolute inset-0 opacity-80">
        <span
          v-for="i in 96"
          :key="i"
          class="star-point absolute rounded-full bg-white/70"
          :style="{
            left: `${(i * 37) % 100}%`,
            top: `${14 + ((i * 53) % 72)}%`,
            width: `${2 + ((i * 11) % 4)}px`,
            height: `${2 + ((i * 11) % 4)}px`,
            opacity: `${0.22 + ((i * 7) % 62) / 100}`,
            animationDelay: `${(i % 12) * -0.45}s`,
            animationDuration: `${5 + (i % 8)}s`
          }"
        ></span>
      </div>
      <div class="meteor-field absolute inset-0 overflow-hidden">
        <span v-for="i in 4" :key="`meteor-${i}`" class="meteor-line" :class="`meteor-${i}`"></span>
      </div>

      <div :class="['relative mx-auto flex max-w-[1380px] flex-col items-center justify-center px-6 text-center', isHomePage ? 'min-h-[calc(100vh-64px)]' : 'min-h-[560px]']">
        <div class="hero-kicker mb-8 rounded-full border border-white/16 bg-white/8 px-5 py-2 text-sm font-semibold tracking-[0.22em] text-white/82">
          AI RECRUITMENT CENTER
        </div>
        <h1 class="hero-title text-[52px] font-black leading-tight tracking-tight md:text-[84px]">众里寻你，一起发光</h1>
        <p class="mt-5 max-w-3xl text-xl leading-9 text-white/78">从岗位投递到 AI 面试，查看你的招聘进度，找到更适合的机会。</p>

        <div class="hero-search mt-12 flex w-full max-w-3xl overflow-visible rounded-none border border-white/60 bg-white/12 shadow-2xl shadow-blue-950/40">
          <div class="relative z-10 min-w-[128px] border-r border-white/40">
            <button
              class="flex h-full w-full items-center justify-center px-4 text-left text-white/90 transition hover:bg-white/10"
              @click.stop="showRecruitmentPicker = !showRecruitmentPicker"
            >
              {{ recruitmentType }} <i class="fa fa-angle-down ml-2 transition" :class="showRecruitmentPicker ? 'rotate-180' : ''"></i>
            </button>
            <div
              v-if="showRecruitmentPicker"
              class="absolute left-0 top-[calc(100%+10px)] w-full overflow-hidden rounded-xl border border-white/18 bg-[#082529]/95 py-1 text-sm text-white shadow-2xl backdrop-blur"
            >
              <template v-if="isCampusModule">
                <button class="block w-full px-4 py-3 text-left hover:bg-white/10" :class="recruitmentType === '校招' ? 'text-[#72f2d1]' : ''" @click="chooseSearchType('校招')">校园招聘</button>
                <button class="block w-full px-4 py-3 text-left hover:bg-white/10" :class="recruitmentType === '实习' ? 'text-[#72f2d1]' : ''" @click="chooseSearchType('实习')">实习生招聘</button>
              </template>
              <button v-else class="block w-full px-4 py-3 text-left text-[#72f2d1]" @click="chooseSearchType('社招')">社会招聘</button>
            </div>
          </div>
          <input
            v-model="keyword"
            class="min-w-0 flex-1 bg-white/10 px-5 py-4 text-base text-white placeholder:text-white/55 outline-none"
            placeholder="搜索岗位、技术方向或城市"
            @keyup.enter="searchJobs"
          >
          <button class="bg-white px-8 py-4 font-bold text-[#087f78] hover:bg-emerald-50" @click="searchJobs">搜索职位</button>
        </div>

        <div class="mt-6 flex flex-wrap justify-center gap-3 text-sm text-white/70">
          <button v-for="tag in heroTags" :key="tag" class="hero-tag rounded-full bg-white/8 px-4 py-2 hover:bg-white/14" @click="keyword = tag; searchJobs()">{{ tag }}</button>
        </div>
      </div>
    </section>

    <section v-if="!isHomePage" class="mx-auto grid max-w-[1440px] gap-8 px-6 py-16 xl:grid-cols-[240px_minmax(0,1fr)_320px]">
      <aside class="h-fit rounded-xl bg-white p-6 shadow-[0_12px_34px_rgba(15,35,80,0.10)]">
        <h3 class="text-lg font-bold">筛选</h3>
        <div class="mt-7">
          <div class="mb-4 font-bold">职位类别</div>
          <div class="space-y-3">
            <button v-for="item in categories" :key="item" class="flex w-full items-center gap-3 text-left text-[#4a5568]" @click="toggleCategory(item)">
              <span class="flex h-4 w-4 items-center justify-center border" :class="selectedCategory === item ? 'border-[#4b6cff] bg-[#4b6cff]' : 'border-[#d8dce8]'">
                <i v-if="selectedCategory === item" class="fa fa-check text-[10px] text-white"></i>
              </span>
              {{ item }}
            </button>
          </div>
        </div>
        <div class="mt-8">
          <div class="mb-4 font-bold">职位地点</div>
          <div class="space-y-3">
            <button v-for="item in locations" :key="item" class="flex w-full items-center gap-3 text-left text-[#4a5568]" @click="toggleLocation(item)">
              <span class="flex h-4 w-4 items-center justify-center border" :class="selectedLocation === item ? 'border-[#4b6cff] bg-[#4b6cff]' : 'border-[#d8dce8]'">
                <i v-if="selectedLocation === item" class="fa fa-check text-[10px] text-white"></i>
              </span>
              {{ item }}
            </button>
          </div>
        </div>
        <button class="mt-7 text-[#4b6cff]" @click="resetFilters">+ 重置筛选</button>
      </aside>

      <main class="min-w-0">
        <div class="mb-5 flex flex-wrap items-center justify-between gap-4">
          <div class="text-lg font-bold">{{ total }} 条职位信息</div>
          <div v-if="isCampusModule" class="flex overflow-hidden rounded-full bg-[#e9ecf5] p-1">
            <button class="rounded-full px-6 py-2" :class="recruitmentType === '校招' ? 'bg-[#11b89f] text-white' : 'text-[#667085]'" @click="selectType('校招')">校园招聘</button>
            <button class="rounded-full px-6 py-2" :class="recruitmentType === '实习' ? 'bg-[#11b89f] text-white' : 'text-[#667085]'" @click="selectType('实习')">实习生招聘</button>
          </div>
          <div v-else class="rounded-full bg-[#e9ecf5] px-6 py-2 text-sm font-medium text-[#11b89f]">社会招聘</div>
        </div>

        <div v-if="error" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-600">{{ error }}</div>
        <div v-if="loading" class="rounded-xl bg-white p-12 text-center text-[#667085] shadow-sm">正在加载职位...</div>

        <div v-else class="space-y-4">
          <article v-for="job in jobs" :key="job.id" class="cursor-pointer rounded-xl bg-white p-6 shadow-[0_12px_28px_rgba(15,35,80,0.08)] transition hover:-translate-y-0.5 hover:shadow-[0_18px_42px_rgba(15,35,80,0.12)]" @click="router.push(`/jobs/${job.id}`)">
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-3">
                  <span class="text-red-500"><i class="fa fa-fire"></i></span>
                  <h2 class="text-2xl font-bold text-[#202838]">{{ job.name }}</h2>
                  <span class="rounded-md bg-[#fff2e8] px-2 py-1 text-sm text-[#f26b3a]">{{ job.recruitment_type || recruitmentType }}</span>
                </div>
                <div class="mt-3 text-[#687286]">
                  {{ job.category || '综合' }} ｜ {{ job.location || '地点待定' }} ｜ {{ job.experience_required || '不限经验' }} ｜ {{ String(job.updated_at || job.created_at || '').slice(0, 10) || '近期发布' }}
                </div>
                <p class="mt-4 line-clamp-2 leading-7 text-[#3f4b5f]">{{ jobSummary(job) }}</p>
              </div>
              <div class="flex shrink-0 gap-3 text-[#9aa3b5]" @click.stop>
                <button :class="['h-9 w-9 rounded-full transition', isFavorite(job.id) ? 'text-amber-500 bg-amber-50' : 'hover:bg-[#f3f5fb]']" :title="isFavorite(job.id) ? '取消收藏' : '收藏'" @click="toggleFavorite(job)">
                  <i :class="['fa', isFavorite(job.id) ? 'fa-star' : 'fa-star-o']"></i>
                </button>
                <button class="h-9 w-9 rounded-full hover:bg-[#f3f5fb]" title="分享" @click="shareJob(job)"><i class="fa fa-share-alt"></i></button>
              </div>
            </div>
            <div class="mt-5 flex flex-wrap items-center justify-between gap-4">
              <div class="flex flex-wrap gap-2">
                <span v-for="tag in [job.category || '业务方向', job.location || '灵活地点', job.experience_required || '不限经验']" :key="tag" class="rounded-md bg-[#f3f7ff] px-3 py-1.5 text-sm text-[#4d63af]">{{ tag }}</span>
              </div>
              <div class="flex gap-3" @click.stop>
                <button class="rounded-lg border border-[#dce5f2] px-5 py-2.5 font-semibold text-[#475467] hover:bg-[#f5f7fa]" @click="router.push(`/jobs/${job.id}`)">查看详情</button>
                <button class="rounded-lg bg-[#11b89f] px-5 py-2.5 font-semibold text-white hover:bg-[#0d9488]" @click="goLogin(job.id)">立即投递</button>
              </div>
            </div>
          </article>

          <div v-if="!jobs.length" class="rounded-xl bg-white p-12 text-center text-[#667085] shadow-sm">
            暂无匹配职位，换个关键词试试。
          </div>

          <div v-if="total > pageSize" class="mt-7 flex items-center justify-center gap-1 rounded-xl bg-white px-5 py-4 shadow-sm">
            <button class="flex h-9 w-9 items-center justify-center rounded-md border border-[#d9dee8] text-[#98a2b3] transition hover:border-[#4b6cff] hover:text-[#4b6cff] disabled:cursor-not-allowed disabled:opacity-45" :disabled="page <= 1 || loading" aria-label="上一页" @click="goPage(page - 1)">
              <i class="fa fa-angle-left"></i>
            </button>
            <template v-for="(item, index) in paginationItems" :key="`${item}-${index}`">
              <span v-if="typeof item === 'string'" class="flex h-9 w-9 items-center justify-center text-sm text-[#98a2b3]">…</span>
              <button v-else :class="['h-9 min-w-9 rounded-md border px-2 text-sm transition', item === page ? 'border-[#4b6cff] bg-[#f4f6ff] text-[#4b6cff]' : 'border-[#d9dee8] text-[#344054] hover:border-[#4b6cff] hover:text-[#4b6cff]']" :disabled="loading" @click="goPage(item)">{{ item }}</button>
            </template>
            <button class="flex h-9 w-9 items-center justify-center rounded-md border border-[#d9dee8] text-[#344054] transition hover:border-[#4b6cff] hover:text-[#4b6cff] disabled:cursor-not-allowed disabled:opacity-45" :disabled="page >= totalPages || loading" aria-label="下一页" @click="goPage(page + 1)">
              <i class="fa fa-angle-right"></i>
            </button>
          </div>
        </div>
      </main>

      <aside class="space-y-6 xl:sticky xl:top-24 xl:h-fit">
        <div class="rounded-2xl bg-white p-6 shadow-[0_12px_34px_rgba(15,35,80,0.10)]">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold">智能职位推荐</h2>
            <button class="text-sm font-semibold text-[#0f9f8f]">全部职位 &gt;</button>
          </div>
          <p class="mt-2 text-sm leading-6 text-[#667085]">根据当前筛选条件，为你优先展示更匹配的机会。</p>
          <div class="mt-5 space-y-5">
            <div v-for="job in recommendedJobs" :key="job.id" class="cursor-pointer rounded-xl border border-[#e7eef7] bg-[#fbfdff] p-4 transition hover:-translate-y-0.5 hover:shadow-md" @click="router.push(`/jobs/${job.id}`)">
              <div class="font-bold">{{ job.name }}</div>
              <div class="mt-3 flex flex-wrap gap-2">
                <span class="rounded border border-[#11b89f] px-2 py-0.5 text-sm text-[#0f9f8f]">{{ job.category || '技术' }}</span>
                <span class="rounded border border-[#d8dce8] px-2 py-0.5 text-sm text-[#667085]">{{ job.location || '深圳' }}</span>
              </div>
              <div class="mt-3 grid grid-cols-3 gap-px overflow-hidden rounded bg-[#edf3f8] text-center text-sm text-[#4f5a6d]">
                <span class="bg-[#f8fbff] py-2">岗位匹配</span>
                <span class="bg-[#f8fbff] py-2">AI 面试</span>
                <span class="bg-[#f8fbff] py-2">可投递</span>
              </div>
            </div>
            <div v-if="!recommendedJobs.length" class="rounded-xl bg-[#f8fbff] p-6 text-center text-sm text-[#667085]">
              暂无推荐职位
            </div>
          </div>
        </div>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.recruitment-hero {
  isolation: isolate;
}

.hero-aurora {
  background:
    radial-gradient(circle at 50% 48%, rgba(255, 247, 205, 0.08) 0 4%, rgba(20, 184, 166, 0.1) 5% 18%, transparent 39%),
    radial-gradient(circle at 43% 56%, rgba(16, 185, 129, 0.08), transparent 34%),
    radial-gradient(circle at 62% 34%, rgba(245, 158, 11, 0.05), transparent 28%),
    radial-gradient(circle at 18% 18%, rgba(45, 212, 191, 0.06), transparent 34%);
  animation: aurora-breathe 9s ease-in-out infinite;
}

.orbit-ring {
  transform-origin: center;
  will-change: transform;
}

.orbit-ring-1 {
  animation: orbit-spin 38s linear infinite;
}

.orbit-ring-2 {
  animation: orbit-spin-reverse 58s linear infinite;
}

.orbit-ring-3 {
  animation: orbit-spin 82s linear infinite;
}

.orbit-node {
  position: absolute;
  left: 50%;
  top: -5px;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  box-shadow: 0 0 22px currentColor;
}

.node-green {
  color: #4ade80;
  background: #4ade80;
}

.node-blue {
  color: #2dd4bf;
  background: #2dd4bf;
}

.node-gold {
  color: #facc15;
  background: #facc15;
}

.orbit-label {
  position: absolute;
  color: rgba(255, 255, 255, 0.66);
  font-size: 12px;
  font-weight: 700;
  text-shadow: 0 0 18px rgba(255, 255, 255, 0.26);
  animation: label-float 4.8s ease-in-out infinite;
}

.label-1 {
  left: 62%;
  top: 12%;
}

.label-2 {
  left: 18%;
  top: 64%;
  animation-delay: -1.2s;
}

.label-3 {
  right: 14%;
  top: 35%;
  animation-delay: -2.4s;
}

.label-4 {
  left: 30%;
  bottom: 10%;
  animation-delay: -3.1s;
}

.star-point {
  filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.38));
  animation-name: star-drift;
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
}

.meteor-field {
  pointer-events: none;
}

.meteor-line {
  position: absolute;
  left: 78%;
  top: 18%;
  height: 1px;
  width: 140px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.9), rgba(114, 242, 209, 0.12));
  filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.46));
  opacity: 0;
  transform: rotate(-26deg) translate3d(0, 0, 0);
  animation: meteor-fall 8.5s linear infinite;
}

.meteor-1 {
  left: 72%;
  top: 18%;
  animation-delay: -1.2s;
}

.meteor-2 {
  left: 86%;
  top: 30%;
  width: 110px;
  animation-delay: -4.8s;
  animation-duration: 10.5s;
}

.meteor-3 {
  left: 55%;
  top: 12%;
  width: 92px;
  animation-delay: -7.3s;
  animation-duration: 12s;
}

.meteor-4 {
  left: 94%;
  top: 42%;
  width: 128px;
  animation-delay: -9.5s;
  animation-duration: 13.5s;
}

.hero-kicker,
.hero-title,
.hero-search,
.hero-tag {
  animation: hero-rise 0.75s cubic-bezier(0.2, 0.75, 0.25, 1) both;
}

.hero-title {
  text-shadow: 0 8px 42px rgba(45, 212, 191, 0.2), 0 0 18px rgba(255, 244, 201, 0.1);
  animation-delay: 0.08s;
}

.hero-search {
  backdrop-filter: blur(18px);
  animation-delay: 0.18s;
}

.hero-tag {
  transition: transform 0.2s ease, background-color 0.2s ease, color 0.2s ease;
  animation-delay: 0.26s;
}

.hero-tag:hover {
  transform: translateY(-2px);
  color: white;
}

@keyframes orbit-spin {
  from {
    transform: translate(-50%, -50%) rotate(0deg);
  }
  to {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

@keyframes orbit-spin-reverse {
  from {
    transform: translate(-50%, -50%) rotate(360deg);
  }
  to {
    transform: translate(-50%, -50%) rotate(0deg);
  }
}

@keyframes aurora-breathe {
  0%,
  100% {
    transform: scale(1);
    filter: saturate(1);
  }
  50% {
    transform: scale(1.035);
    filter: saturate(1.16);
  }
}

@keyframes star-drift {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(10px, -12px, 0) scale(1.35);
  }
}

@keyframes meteor-fall {
  0%,
  64% {
    opacity: 0;
    transform: rotate(-26deg) translate3d(0, 0, 0);
  }
  68% {
    opacity: 0.85;
  }
  78%,
  100% {
    opacity: 0;
    transform: rotate(-26deg) translate3d(-520px, 230px, 0);
  }
}

@keyframes label-float {
  0%,
  100% {
    transform: translateY(0);
    opacity: 0.58;
  }
  50% {
    transform: translateY(-8px);
    opacity: 0.9;
  }
}

@keyframes hero-rise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-aurora,
  .orbit-ring,
  .orbit-label,
  .star-point,
  .meteor-line,
  .hero-kicker,
  .hero-title,
  .hero-search,
  .hero-tag {
    animation: none;
  }
}
</style>
