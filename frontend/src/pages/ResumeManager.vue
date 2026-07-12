<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const resumeList = ref([])
const loading = ref(true)
const uploading = ref(false)
const searchText = ref('')
const filterStatus = ref('')
const filterYears = ref('')
const showJdPicker = ref(false)
const pendingFile = ref(null)
const selectedJdId = ref(0)
const jdOptions = ref([])

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchText.value) params.set('search', searchText.value)
    if (filterStatus.value) params.set('parse_status', filterStatus.value)
    if (filterYears.value) params.set('experience_years', filterYears.value)
    const qs = params.toString()
    const res = await fetch(`/api/resumes${qs ? '?' + qs : ''}`)
    if (res.ok) resumeList.value = await res.json()
  } catch (_) {}
  loading.value = false
}

onMounted(fetchList)

function onFileChange(e) {
  const file = e.target?.files?.[0]
  if (file) openJdPicker(file)
}

async function openJdPicker(file) {
  pendingFile.value = file
  selectedJdId.value = 0
  try {
    const res = await fetch('/api/jds?page_size=999')
    if (res.ok) {
      const data = await res.json()
      jdOptions.value = data.items.filter(j => j.status === 'enable')
    }
  } catch (_) {}
  showJdPicker.value = true
}

async function confirmUpload() {
  if (!pendingFile.value) return
  uploading.value = true
  showJdPicker.value = false
  try {
    const fd = new FormData()
    fd.append('file', pendingFile.value)
    if (selectedJdId.value > 0) fd.append('jd_id', selectedJdId.value)
    const uploadRes = await fetch('/api/resumes/upload', { method: 'POST', body: fd })
    if (!uploadRes.ok) return
    const resume = await uploadRes.json()
    pendingFile.value = null
    // 上传后自动解析
    await fetch(`/api/resumes/${resume.id}/parse`, { method: 'POST' }).catch(() => {})
    await fetchList()
  } catch (_) {}
  uploading.value = false
}

async function parseResume(rid) {
  try {
    const res = await fetch(`/api/resumes/${rid}/parse`, { method: 'POST' })
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || '解析失败')
      return
    }
    await fetchList()
  } catch (e) {
    alert('解析失败: ' + e.message)
  }
}

async function removeResume(rid, name) {
  if (!confirm(`确认删除「${name}」？`)) return
  await fetch(`/api/resumes/${rid}`, { method: 'DELETE' })
  await fetchList()
}

const viewingResume = ref(null)
async function viewResume(r) {
  viewingResume.value = null
  try {
    const res = await fetch(`/api/resumes/${r.id}`)
    if (res.ok) viewingResume.value = await res.json()
  } catch (_) {}
}

function createInterview(resume) {
  localStorage.setItem('interviewmate_selected_resume', resume.file_path || '')
  router.push('/interviewee')
}

const statusBadge = (s) => ({ success: 'bg-green-100 text-green-600', wait: 'bg-orange-100 text-orange-600', fail: 'bg-red-100 text-red-600' }[s] || 'bg-gray-100 text-gray-500')
const statusLabel = (s) => ({ success: '解析成功', wait: '待解析', fail: '解析失败' }[s] || s)

function resetFilters() { searchText.value = ''; filterStatus.value = ''; filterYears.value = ''; fetchList() }
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">简历管理</h2>
        <label class="bg-[#1677ff] text-white px-5 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 transition cursor-pointer text-sm">
          <i class="fa fa-plus"></i> 上传简历
          <input type="file" accept=".pdf,.docx,.doc,.txt,.md" class="hidden" @change="onFileChange" />
        </label>
      </div>

      <!-- 搜索筛选 -->
      <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <div class="w-64 relative">
            <input v-model="searchText" type="text" placeholder="搜索候选人姓名、技能、期望岗位" class="w-full pl-9 pr-3 py-2 border rounded-lg focus:outline-none focus:border-[#1677ff]" @input="fetchList">
            <i class="fa fa-search absolute left-3 top-3 text-gray-400"></i>
          </div>
          <select v-model="filterStatus" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="fetchList">
            <option value="">全部解析状态</option>
            <option value="wait">待解析</option>
            <option value="success">解析成功</option>
            <option value="fail">解析失败</option>
          </select>
          <select v-model="filterYears" class="border rounded-lg px-3 py-2 min-w-[150px]" @change="fetchList">
            <option value="">全部工作年限</option>
            <option value="应届生">应届生</option>
            <option value="1-3年">1-3年</option>
            <option value="3-5年">3-5年</option>
            <option value="5年以上">5年以上</option>
          </select>
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="resetFilters">重置筛选</button>
        </div>
      </div>

      <!-- 简历表格 -->
      <div class="bg-white rounded-xl shadow-sm overflow-hidden">
        <div v-if="loading" class="text-center py-12 text-gray-400"><i class="fa fa-spinner fa-spin text-2xl mb-2 block"></i>加载中...</div>
        <table v-else class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm w-8">#</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">候选人</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">期望岗位</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">学历</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">经验</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">关联 JD</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">文件</th>
              <th class="text-left px-4 py-3 text-gray-600 font-medium text-sm">解析状态</th>
              <th class="text-center px-4 py-3 text-gray-600 font-medium text-sm w-36">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(r, i) in resumeList" :key="r.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm text-gray-500">{{ i + 1 }}</td>
              <td class="px-4 py-3 font-medium text-sm">{{ r.name || '未命名' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.target_position || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.education || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.experience_years || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ r.jd_name || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">{{ r.skills || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-400 max-w-[140px] truncate">{{ r.original_name || r.file_path || '-' }}</td>
              <td class="px-4 py-3"><span :class="['px-2 py-1 text-xs rounded', statusBadge(r.parse_status)]">{{ statusLabel(r.parse_status) }}</span></td>
              <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center gap-1">
                  <button class="w-8 h-8 rounded-lg text-[#1677ff] hover:bg-blue-50 transition flex items-center justify-center" title="查看" @click="viewResume(r)"><i class="fa fa-eye"></i></button>
                  <button v-if="r.parse_status !== 'success' && r.file_path" class="w-8 h-8 rounded-lg text-orange-500 hover:bg-orange-50 transition flex items-center justify-center" :title="r.parse_status === 'fail' ? '重新解析' : '解析'" @click="parseResume(r.id)"><i class="fa fa-refresh"></i></button>
                  <button
                    v-if="r.parse_status === 'success'"
                    class="w-8 h-8 rounded-lg text-[#22c55e] hover:bg-green-50 transition flex items-center justify-center" title="创建面试"
                    @click="createInterview(r)"
                  ><i class="fa fa-play"></i></button>
                  <button class="w-8 h-8 rounded-lg text-red-400 hover:bg-red-50 transition flex items-center justify-center" title="删除" @click="removeResume(r.id, r.name)"><i class="fa fa-trash-o"></i></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !resumeList.length" class="text-center py-12 text-gray-400">
          <i class="fa fa-inbox text-3xl mb-2 block"></i>暂无简历，请上传
        </div>
      </div>

      <p class="text-sm text-gray-500 mt-4">共 {{ resumeList.length }} 条</p>
    </main>

    <!-- 查看简历弹窗 - 左右分栏 -->
    <div v-if="viewingResume" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @click.self="viewingResume = null">
      <div class="bg-white rounded-2xl w-[1100px] max-w-[95vw] h-[88vh] flex flex-col shadow-xl overflow-hidden">
        <!-- Header -->
        <div class="flex-shrink-0 px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold">{{ viewingResume.name || '简历详情' }}</h3>
            <p class="text-xs text-gray-500">{{ viewingResume.target_position || '' }} · {{ viewingResume.education || '' }}</p>
          </div>
          <div class="flex items-center gap-3">
            <span :class="['px-2 py-1 text-xs rounded', statusBadge(viewingResume.parse_status)]">{{ statusLabel(viewingResume.parse_status) }}</span>
            <button class="text-gray-400 hover:text-gray-600" @click="viewingResume = null"><i class="fa fa-times text-lg"></i></button>
          </div>
        </div>

        <!-- Body - 左右分栏 -->
        <div class="flex-1 flex overflow-hidden">
          <!-- 左侧：PDF 原文 -->
          <div class="w-1/2 border-r overflow-hidden bg-gray-100 flex flex-col">
            <h4 class="flex-shrink-0 text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 py-3 bg-gray-50 border-b">{{ viewingResume.original_name || viewingResume.file_path || '简历原文' }}</h4>
            <div class="flex-1">
              <embed
                v-if="viewingResume.file_path"
                :src="'/uploads/resume/' + viewingResume.file_path"
                type="application/pdf"
                class="w-full h-full"
              />
              <div v-else class="flex items-center justify-center h-full text-gray-400">
                <p class="text-sm">无文件</p>
              </div>
            </div>
          </div>

          <!-- 右侧：解析数据 -->
          <div class="w-1/2 overflow-auto p-4">
            <div v-if="viewingResume.parse_status === 'success' && viewingResume.structured_data">
              <template v-for="(section, key) in JSON.parse(viewingResume.structured_data || '{}')" :key="key">
                <!-- 基础信息 -->
                <div v-if="key === '基础信息' && section" class="mb-4">
                  <h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">基础信息</h4>
                  <table class="w-full text-sm border-collapse">
                    <tbody>
                      <tr v-for="(val, k) in section" :key="k" v-show="val" class="border-b border-gray-100">
                        <td class="py-2 pr-3 text-gray-400 w-20 text-xs">{{ k }}</td>
                        <td class="py-2 text-gray-800 font-medium">{{ val }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <!-- 自我评价 -->
                <div v-if="key === '自我评价' && section" class="mb-4">
                  <h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">自我评价</h4>
                  <p class="text-sm text-gray-700 leading-relaxed bg-blue-50 rounded-lg p-3">{{ section }}</p>
                </div>
                <!-- 教育经历 -->
                <div v-if="key === '教育经历' && section?.length" class="mb-4">
                  <h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">教育经历</h4>
                  <table class="w-full text-sm border-collapse">
                    <thead><tr class="bg-gray-50"><th class="text-left py-2 px-2 text-xs text-gray-500">学校</th><th class="text-left py-2 px-2 text-xs text-gray-500">专业</th><th class="text-left py-2 px-2 text-xs text-gray-500">学位</th><th class="text-left py-2 px-2 text-xs text-gray-500">时间</th></tr></thead>
                    <tbody>
                      <tr v-for="(edu, i) in section" :key="i" class="border-b border-gray-100">
                        <td class="py-2 px-2 text-gray-800">{{ edu.学校 }}</td>
                        <td class="py-2 px-2 text-gray-600">{{ edu.专业 }}</td>
                        <td class="py-2 px-2"><span class="text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded">{{ edu.学位 }}</span></td>
                        <td class="py-2 px-2 text-gray-500 text-xs">{{ edu.开始时间 }} ~ {{ edu.结束时间 }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <!-- 工作经历 -->
                <div v-if="key === '工作经历' && section?.length" class="mb-4">
                  <h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">工作经历</h4>
                  <div v-for="(job, i) in section" :key="i" class="mb-3 border border-gray-200 rounded-lg p-3">
                    <div class="flex items-center justify-between mb-1">
                      <span class="font-medium text-sm text-gray-800">{{ job.公司名称 }}</span>
                      <span class="text-xs text-gray-400">{{ job.开始时间 }} ~ {{ job.结束时间 }}</span>
                    </div>
                    <span class="inline-block text-xs bg-green-100 text-green-600 px-1.5 py-0.5 rounded mb-2">{{ job.职位 }}</span>
                    <p class="text-xs text-gray-600 leading-relaxed">{{ job.工作描述 }}</p>
                  </div>
                </div>
                <!-- 项目经历 -->
                <div v-if="key === '项目经历' && section?.length" class="mb-4">
                  <h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">项目经历</h4>
                  <div v-for="(proj, i) in section" :key="i" class="mb-3 border border-gray-200 rounded-lg p-3">
                    <div class="flex items-center justify-between mb-1">
                      <span class="font-medium text-sm text-gray-800">{{ proj.项目名称 }}</span>
                      <span class="text-xs text-gray-400">{{ proj.开始时间 }} ~ {{ proj.结束时间 }}</span>
                    </div>
                    <span class="inline-block text-xs bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded mb-2">{{ proj.角色 }}</span>
                    <p class="text-xs text-gray-600 leading-relaxed">{{ proj.项目描述 }}</p>
                  </div>
                </div>
              </template>
            </div>
            <div v-else class="text-center py-12 text-gray-400">
              <i class="fa fa-file-text-o text-3xl mb-2 block"></i>
              <p class="text-sm">尚未解析，请先上传文件并点击解析按钮</p>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex-shrink-0 px-6 py-3 border-t bg-gray-50 flex justify-end items-center">
          <button class="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 text-sm" @click="viewingResume = null">关闭</button>
        </div>
      </div>
    </div>

    <!-- JD 选择弹窗 -->
    <div v-if="showJdPicker" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showJdPicker = false">
      <div class="bg-white rounded-2xl w-[480px] p-6 shadow-xl">
        <h3 class="text-lg font-bold mb-2">选择关联岗位 JD</h3>
        <p class="text-sm text-gray-500 mb-4">文件：{{ pendingFile?.name }}</p>
        <div class="space-y-2 max-h-64 overflow-auto">
          <label
            v-for="jd in jdOptions"
            :key="jd.id"
            :class="['flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition', selectedJdId === jd.id ? 'border-[#1677ff] bg-blue-50' : 'border-gray-200 hover:bg-gray-50']"
          >
            <input v-model="selectedJdId" type="radio" :value="jd.id" class="hidden">
            <div class="flex-1">
              <div class="font-medium text-sm">{{ jd.name }}</div>
              <div class="text-xs text-gray-500">{{ jd.category }} · {{ jd.location }} · {{ jd.recruitment_type }}</div>
            </div>
          </label>
          <label
            :class="['flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition', selectedJdId === 0 ? 'border-gray-400 bg-gray-100' : 'border-gray-200 hover:bg-gray-50']"
          >
            <input v-model="selectedJdId" type="radio" :value="0" class="hidden">
            <div class="flex-1 text-sm text-gray-500">暂不关联（稍后设置）</div>
          </label>
        </div>
        <div class="flex justify-end gap-3 mt-5">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="showJdPicker = false; pendingFile = null">取消</button>
          <button class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600 text-sm" @click="confirmUpload">确认上传</button>
        </div>
      </div>
    </div>
  </div>
</template>
