<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const parsing = ref(false)
const resume = ref(null)

const form = ref({
  姓名: '', 性别: '', 出生年月: '', 手机号: '', 邮箱: '', 求职意向: '', 所在地: '', 自我评价: '',
  教育经历: [], 工作经历: [], 项目经历: [],
})

const genderOptions = ['', '男', '女']
const educationLevels = ['博士', '硕士', '本科', '大专', '高中/中专']

onMounted(loadResume)

async function loadResume() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    const filename = route.query.filename || ''
    const res = await fetch(`/api/plans/my-resume?filename=${encodeURIComponent(filename)}`, { headers })
    if (!res.ok) throw new Error('简历不存在')
    resume.value = await res.json()
    if (resume.value.structured_data) {
      try { prefill(JSON.parse(resume.value.structured_data)) } catch (_) {}
    }
  } catch (e) { /* 无简历时允许上传 */ } finally { loading.value = false }
}

function prefill(data) {
  const b = data['基础信息'] || {}
  form.value.姓名 = b['姓名'] || resume.value?.name || ''
  form.value.性别 = b['性别'] || ''
  form.value.手机号 = b['电话'] || ''
  form.value.邮箱 = b['邮箱'] || ''
  form.value.求职意向 = b['意向岗位'] || resume.value?.target_position || ''
  form.value.所在地 = b['地址'] || ''
  form.value.出生年月 = b['出生年月'] || ''
  form.value.自我评价 = data['自我评价'] || ''
  form.value.教育经历 = ensureList(data['教育经历'])
  form.value.工作经历 = ensureList(data['工作经历'])
  form.value.项目经历 = ensureList(data['项目经历'])
}

function ensureList(v) {
  if (Array.isArray(v)) return v
  return v && typeof v === 'object' ? [v] : []
}

async function handleUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  parsing.value = true
  try {
    const fd = new FormData(); fd.append('file', file)
    const headers = { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    const res = await fetch('/api/plans/my-resume/upload', { method: 'POST', headers, body: fd })
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || '上传失败')
    resume.value = await res.json()
    if (resume.value.structured_data) {
      try { prefill(JSON.parse(resume.value.structured_data)) } catch (_) {}
    }
  } catch (e) { alert(e.message) } finally { parsing.value = false; e.target.value = '' }
}

function addItem(section) {
  const t = section === '教育经历'
    ? { 学校: '', 专业: '', 学位: '', 学历: '', 开始时间: '', 结束时间: '' }
    : section === '工作经历'
      ? { 公司名称: '', 职位: '', 开始时间: '', 结束时间: '', 工作描述: '' }
      : { 项目名称: '', 角色: '', 开始时间: '', 结束时间: '', 项目描述: '' }
  form.value[section].push(t)
}

function removeItem(section, i) { form.value[section].splice(i, 1) }

async function handleSave() {
  saving.value = true
  try {
    const structured = {
      '基础信息': { '姓名': form.value.姓名, '性别': form.value.性别, '意向岗位': form.value.求职意向, '邮箱': form.value.邮箱, '电话': form.value.手机号, '地址': form.value.所在地, '出生年月': form.value.出生年月 },
      '自我评价': form.value.自我评价,
      '教育经历': form.value.教育经历,
      '工作经历': form.value.工作经历,
      '项目经历': form.value.项目经历,
    }
    const res = await fetch('/api/plans/my-resume', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
      body: JSON.stringify({
        name: form.value.姓名,
        target_position: form.value.求职意向,
        structured_data: JSON.stringify(structured),
      }),
    })
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || '保存失败')
    alert('保存成功')
  } catch (e) { alert(e.message) } finally { saving.value = false }
}
</script>

<template>
  <div class="min-h-screen bg-[#f3f5f8] text-[#202838]">
    <header class="sticky top-0 z-20 border-b border-[#e5eaf1] bg-white/95 backdrop-blur">
      <div class="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-6">
        <button class="font-semibold text-[#475467] hover:text-[#4776ff]" @click="router.back()"><i class="fa fa-arrow-left mr-2"></i>返回</button>
        <span class="text-sm font-bold truncate max-w-[420px]">{{ resume?.original_name || '编辑简历' }}</span>
        <button class="rounded-lg bg-[#4776ff] px-5 py-2 text-sm font-bold text-white hover:bg-[#3868e5] disabled:opacity-50" :disabled="saving" @click="handleSave">
          <i :class="['fa mr-1', saving ? 'fa-spinner fa-spin' : 'fa-check']"></i>{{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </header>

    <main class="mx-auto max-w-[1280px] px-4 py-8 sm:px-8">
      <div v-if="loading" class="rounded-2xl bg-white p-16 text-center text-[#667085]">正在加载...</div>
      <div v-else class="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
        <!-- 左栏 -->
        <div class="space-y-6">
          <!-- 上传入口 -->
          <div class="rounded-2xl bg-white p-6 shadow-sm">
            <h2 class="mb-4 text-lg font-black">简历文件</h2>
            <label class="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-[#dce5f2] p-6 text-center transition hover:border-[#4776ff] hover:bg-[#f8fbff]">
              <i :class="['fa text-2xl text-[#98a2b3]', parsing ? 'fa-spinner fa-spin' : 'fa-cloud-upload']"></i>
              <span class="text-sm font-semibold text-[#667085]">{{ parsing ? '解析中...' : resume ? '重新上传简历文件（PDF/DOCX）' : '上传简历文件（PDF/DOCX）' }}</span>
              <span class="text-xs text-[#98a2b3]">上传即自动解析，结果会回显到下方表单</span>
              <input type="file" accept=".pdf,.docx,.doc,.txt" class="hidden" :disabled="parsing" @change="handleUpload">
            </label>
          </div>

          <!-- 基本信息 -->
          <div class="rounded-2xl bg-white p-6 shadow-sm">
            <h2 class="mb-5 text-lg font-black">基本信息</h2>
            <div class="space-y-4">
              <div class="grid grid-cols-2 gap-4">
                <div><label class="mb-1 block text-xs font-bold text-[#667085]">姓名</label><input v-model="form.姓名" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff]"></div>
                <div><label class="mb-1 block text-xs font-bold text-[#667085]">性别</label><select v-model="form.性别" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff]"><option v-for="g in genderOptions" :key="g" :value="g">{{ g || '请选择' }}</option></select></div>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div><label class="mb-1 block text-xs font-bold text-[#667085]">出生年月</label><input v-model="form.出生年月" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff]" placeholder="如 1998-06"></div>
                <div><label class="mb-1 block text-xs font-bold text-[#667085]">手机号</label><input v-model="form.手机号" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff]"></div>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div><label class="mb-1 block text-xs font-bold text-[#667085]">邮箱</label><input v-model="form.邮箱" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff]"></div>
                <div><label class="mb-1 block text-xs font-bold text-[#667085]">求职意向</label><input v-model="form.求职意向" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff]"></div>
              </div>
              <div><label class="mb-1 block text-xs font-bold text-[#667085]">所在地</label><input v-model="form.所在地" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff]"></div>
            </div>
          </div>
        </div>

        <!-- 右栏 -->
        <div class="space-y-6">
          <template v-for="s in [
            { key: '教育经历', label: '教育经历', fields: ['学校', '专业', '学位', '学历', '开始时间', '结束时间'] },
            { key: '工作经历', label: '工作经历', fields: ['公司名称', '职位', '开始时间', '结束时间', '工作描述'] },
            { key: '项目经历', label: '项目经历', fields: ['项目名称', '角色', '开始时间', '结束时间', '项目描述'] },
          ]" :key="s.key">
            <div class="rounded-2xl bg-white p-6 shadow-sm">
              <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-black">{{ s.label }}</h2>
                <button class="rounded-lg px-3 py-1.5 text-sm font-bold text-[#4776ff] hover:bg-[#f0f4ff]" @click="addItem(s.key)"><i class="fa fa-plus mr-1"></i>添加</button>
              </div>
              <div v-if="!form[s.key].length" class="rounded-xl bg-[#f8fbff] py-8 text-center text-sm text-[#98a2b3]">暂无{{ s.label }}，点击"添加"录入</div>
              <div v-for="(item, idx) in form[s.key]" :key="idx" class="mb-4 rounded-xl border border-[#edf1f7] p-4">
                <div class="mb-3 flex items-center justify-between">
                  <span class="text-sm font-bold text-[#475467]">{{ s.label.slice(0, -2) }} {{ idx + 1 }}</span>
                  <button class="text-sm text-red-400 hover:text-red-600" @click="removeItem(s.key, idx)"><i class="fa fa-trash"></i></button>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <template v-for="f in s.fields" :key="f">
                    <div :class="f.endsWith('描述') ? 'col-span-2' : ''">
                      <label class="mb-1 block text-xs font-bold text-[#667085]">{{ f }}</label>
                      <input v-if="!f.endsWith('描述')" v-model="item[f]" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff]">
                      <textarea v-else v-model="item[f]" rows="3" class="w-full rounded-lg border border-[#dce5f2] px-3 py-2 text-sm outline-none focus:border-[#4776ff] resize-y"></textarea>
                    </div>
                  </template>
                </div>
                <div v-if="s.key === '教育经历'" class="mt-2 flex items-center gap-2">
                  <span class="text-xs font-bold text-[#667085]">学历：</span>
                  <button v-for="lv in educationLevels" :key="lv" :class="['rounded-full px-3 py-1 text-xs font-bold transition', item['学历'] === lv ? 'bg-[#4776ff] text-white' : 'bg-[#f0f4ff] text-[#667085] hover:bg-[#e0e8ff]']" @click="item['学历'] = item['学历'] === lv ? '' : lv">{{ lv }}</button>
                </div>
              </div>
            </div>
          </template>

          <div class="rounded-2xl bg-white p-6 shadow-sm">
            <h2 class="mb-4 text-lg font-black">自我评价</h2>
            <textarea v-model="form.自我评价" rows="5" class="w-full rounded-lg border border-[#dce5f2] px-3 py-3 text-sm outline-none focus:border-[#4776ff] resize-y" placeholder="请输入自我评价..."></textarea>
          </div>

          <button class="w-full rounded-xl bg-[#4776ff] py-3.5 text-base font-black text-white hover:bg-[#3868e5] disabled:opacity-50" :disabled="saving" @click="handleSave">
            <i :class="['fa mr-2', saving ? 'fa-spinner fa-spin' : 'fa-check']"></i>{{ saving ? '保存中...' : '保存简历' }}
          </button>
        </div>
      </div>
    </main>
  </div>
</template>
