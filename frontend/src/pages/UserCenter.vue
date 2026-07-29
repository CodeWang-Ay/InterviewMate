<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()

function getStore(key, fallback = '') {
  try { return localStorage.getItem(key) || fallback } catch (_) { return fallback }
}

const username = ref(getStore('username'))
const nickname = ref(getStore('nickname', '用户'))
const avatar = ref(getStore('avatar', `https://ui-avatars.com/api/?name=User&background=1677ff&color=fff&size=120`))
const email = ref(getStore('email'))
const phone = ref(getStore('phone'))
const company = ref(getStore('company'))
const bio = ref(getStore('bio'))
const createdAt = ref(getStore('created_at', '近期'))
const role = ref(getStore('role', 'user'))

// 头像
const uploading = ref(false)
const avatarFile = ref(null)
const previewUrl = ref('')

// 编辑资料弹窗
const showProfile = ref(false)
const editForm = ref({ nickname: '', email: '', phone: '', company: '', bio: '' })
const profileLoading = ref(false)

// 修改密码弹窗
const showPassword = ref(false)
const oldPwd = ref('')
const newPwd = ref('')
const newPwd2 = ref('')
const pwdLoading = ref(false)
const pwdError = ref('')

// 统计数据
const stats = ref({ interviews: 0, avgScore: 0, resumes: 0, reports: 0 })

onMounted(async () => {
  try {
    const res = await fetch(role.value === 'admin' ? '/api/records' : '/api/plans/my')
    if (res.ok) {
      const data = await res.json()
      if (role.value === 'admin') {
        stats.value.interviews = data.length
        const scores = data.filter((r) => r.score !== null).map((r) => r.score)
        stats.value.avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
        stats.value.reports = data.filter((r) => r.score !== null).length
      } else {
        stats.value.interviews = Array.isArray(data) ? data.length : 0
        stats.value.reports = Array.isArray(data) ? data.filter((plan) => plan.status === 'finish').length : 0
      }
    }
  } catch (_) { /* ignore */ }
})

function onAvatarSelected(e) {
  const file = e.target?.files?.[0]
  if (!file) return
  avatarFile.value = file
  previewUrl.value = URL.createObjectURL(file)
}

async function saveAvatar() {
  if (!avatarFile.value) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', avatarFile.value)
    const res = await fetch('/api/auth/avatar', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      body: fd,
    })
    if (!res.ok) throw new Error('上传失败')
    const data = await res.json()
    avatar.value = data.avatar_url
    localStorage.setItem('avatar', data.avatar_url)
    avatarFile.value = null
    previewUrl.value = ''
  } catch (e) {
    alert('上传失败')
  }
  uploading.value = false
}

function openProfile() {
  editForm.value = { nickname: nickname.value, email: email.value, phone: phone.value, company: company.value, bio: bio.value }
  showProfile.value = true
}

async function saveProfile() {
  if (!editForm.value.nickname.trim()) return
  profileLoading.value = true
  try {
    const res = await fetch('/api/auth/profile', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(editForm.value),
    })
    if (!res.ok) throw new Error('保存失败')
    nickname.value = editForm.value.nickname.trim()
    email.value = editForm.value.email.trim()
    phone.value = editForm.value.phone.trim()
    company.value = editForm.value.company.trim()
    bio.value = editForm.value.bio.trim()
    ;['nickname', 'email', 'phone', 'company', 'bio'].forEach((k) => localStorage.setItem(k, editForm.value[k]?.trim() || ''))
    showProfile.value = false
  } catch (e) {
    alert('保存失败')
  }
  profileLoading.value = false
}

function openPassword() {
  oldPwd.value = ''
  newPwd.value = ''
  newPwd2.value = ''
  pwdError.value = ''
  showPassword.value = true
}

async function changePassword() {
  pwdError.value = ''
  if (!oldPwd.value || !newPwd.value) { pwdError.value = '请填写完整'; return }
  if (newPwd.value.length < 6) { pwdError.value = '新密码至少6位'; return }
  if (newPwd.value !== newPwd2.value) { pwdError.value = '两次新密码不一致'; return }
  pwdLoading.value = true
  try {
    const res = await fetch('/api/auth/password', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({ old_password: oldPwd.value, new_password: newPwd.value }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '修改失败')
    }
    showPassword.value = false
    alert('密码修改成功，请重新登录')
    doLogout()
  } catch (e) {
    pwdError.value = e.message
  }
  pwdLoading.value = false
}

async function doLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' })
  } catch (_) {}
  localStorage.clear()
  router.push('/admin/login')
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <h2 class="text-2xl font-bold text-gray-900 mb-6">用户中心</h2>

      <!-- 个人信息卡片 -->
      <div class="bg-white rounded-2xl shadow-sm p-8 mb-6">
        <div class="flex flex-col md:flex-row items-start gap-8">
          <!-- 头像区 -->
          <div class="flex flex-col items-center gap-3">
            <img :src="previewUrl || avatar" alt="avatar" class="w-24 h-24 rounded-full object-cover">
            <div v-if="avatarFile" class="flex gap-2">
              <button class="px-3 py-1 bg-[#1677ff] text-white rounded text-xs hover:bg-blue-600 disabled:opacity-50" :disabled="uploading" @click="saveAvatar">
                {{ uploading ? '保存中...' : '保存头像' }}
              </button>
              <button class="px-3 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200" :disabled="uploading" @click="avatarFile = null; previewUrl = ''">取消</button>
            </div>
            <label class="px-4 py-2 bg-[#1677ff] text-white rounded-lg text-sm hover:bg-blue-600 cursor-pointer inline-flex items-center gap-1">
              <i class="fa fa-camera"></i>更换头像
              <input type="file" accept="image/*" class="hidden" @change="onAvatarSelected">
            </label>
          </div>

          <!-- 信息区 -->
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="text-2xl font-bold text-gray-900">{{ nickname }}</h3>
              <span class="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded-full">专业版</span>
            </div>
            <p class="text-gray-500 text-sm mb-4">@{{ username }}</p>

            <div class="grid grid-cols-2 gap-x-8 gap-y-2">
              <div class="flex items-center gap-2 text-sm text-gray-600">
                <i class="fa fa-envelope-o text-gray-400 w-5"></i>
                <span>{{ email || '未填写邮箱' }}</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-gray-600">
                <i class="fa fa-phone text-gray-400 w-5"></i>
                <span>{{ phone || '未填写手机号' }}</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-gray-600">
                <i class="fa fa-building-o text-gray-400 w-5"></i>
                <span>{{ company || '未填写公司' }}</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-gray-600">
                <i class="fa fa-calendar text-gray-400 w-5"></i>
                <span>注册于 {{ createdAt }}</span>
              </div>
            </div>

            <p v-if="bio" class="text-sm text-gray-500 mt-3 italic">"{{ bio }}"</p>
          </div>

          <!-- 编辑入口 -->
          <button class="flex-shrink-0 border border-[#1677ff] text-[#1677ff] px-4 py-2 rounded-lg text-sm hover:bg-blue-50" @click="openProfile">
            <i class="fa fa-pencil mr-1"></i>编辑资料
          </button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-xl p-5 shadow-sm text-center hover:shadow-md transition">
          <div class="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center mx-auto mb-3">
            <i class="fa fa-comments text-[#1677ff]"></i>
          </div>
          <p class="text-2xl font-bold text-gray-900">{{ stats.interviews }}</p>
          <p class="text-xs text-gray-500 mt-1">面试次数</p>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm text-center hover:shadow-md transition">
          <div class="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center mx-auto mb-3">
            <i class="fa fa-star text-[#22c55e]"></i>
          </div>
          <p class="text-2xl font-bold text-gray-900">{{ stats.avgScore }}</p>
          <p class="text-xs text-gray-500 mt-1">平均分</p>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm text-center hover:shadow-md transition">
          <div class="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center mx-auto mb-3">
            <i class="fa fa-file-text text-purple-500"></i>
          </div>
          <p class="text-2xl font-bold text-gray-900">{{ stats.resumes || 0 }}</p>
          <p class="text-xs text-gray-500 mt-1">上传简历</p>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm text-center hover:shadow-md transition">
          <div class="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center mx-auto mb-3">
            <i class="fa fa-bar-chart text-orange-500"></i>
          </div>
          <p class="text-2xl font-bold text-gray-900">{{ stats.reports }}</p>
          <p class="text-xs text-gray-500 mt-1">生成报告</p>
        </div>
      </div>

      <!-- 操作列表 -->
      <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="bg-white rounded-2xl shadow-sm p-6 space-y-4">
          <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">账号安全</h3>
          <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-gray-50 flex items-center gap-3" @click="openPassword">
            <i class="fa fa-lock text-yellow-500 text-lg w-6 text-center"></i>
            <span class="text-sm">修改密码</span>
            <i class="fa fa-chevron-right text-gray-300 ml-auto"></i>
          </button>
          <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-gray-50 flex items-center gap-3">
            <i class="fa fa-shield text-blue-400 text-lg w-6 text-center"></i>
            <span class="text-sm">安全设置</span>
            <i class="fa fa-chevron-right text-gray-300 ml-auto"></i>
          </button>
        </div>
        <div class="bg-white rounded-2xl shadow-sm p-6 space-y-4">
          <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">数据管理</h3>
          <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-gray-50 flex items-center gap-3">
            <i class="fa fa-download text-green-500 text-lg w-6 text-center"></i>
            <span class="text-sm">导出面试记录</span>
            <i class="fa fa-chevron-right text-gray-300 ml-auto"></i>
          </button>
          <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-gray-50 flex items-center gap-3">
            <i class="fa fa-history text-gray-400 text-lg w-6 text-center"></i>
            <span class="text-sm">操作日志</span>
            <i class="fa fa-chevron-right text-gray-300 ml-auto"></i>
          </button>
        </div>
      </div>

      <!-- 关于 -->
      <div class="bg-white rounded-2xl shadow-sm p-6">
        <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">关于</h3>
        <p class="text-gray-600 text-sm">OPC Mate V1.0.0</p>
        <div class="flex gap-4 mt-3">
          <span class="text-[#1677ff] hover:underline cursor-pointer text-sm">帮助文档</span>
          <span class="text-[#1677ff] hover:underline cursor-pointer text-sm">联系客服</span>
        </div>
        <hr class="my-4">
        <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-red-50 flex items-center gap-3" @click="doLogout">
          <i class="fa fa-sign-out text-red-500 text-lg w-6 text-center"></i>
          <span class="text-sm text-red-500">退出登录</span>
        </button>
      </div>
    </main>

    <!-- 编辑资料弹窗 -->
    <div v-if="showProfile" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showProfile = false">
      <div class="bg-white rounded-2xl w-[520px] max-h-[80vh] overflow-auto p-6 shadow-xl">
        <h3 class="text-lg font-bold mb-5">编辑个人资料</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input :value="username" class="w-full border rounded-lg px-3 py-2 bg-gray-50 text-gray-500" disabled>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">昵称 <span class="text-red-500">*</span></label>
              <input v-model="editForm.nickname" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">手机号</label>
              <input v-model="editForm.phone" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input v-model="editForm.email" type="email" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">公司</label>
            <input v-model="editForm.company" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">个人简介</label>
            <textarea v-model="editForm.bio" rows="3" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]" placeholder="一句话介绍自己..."></textarea>
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="showProfile = false">取消</button>
          <button class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600 text-sm disabled:opacity-50" :disabled="profileLoading" @click="saveProfile">
            {{ profileLoading ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <div v-if="showPassword" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showPassword = false">
      <div class="bg-white rounded-2xl w-[420px] p-6 shadow-xl">
        <h3 class="text-lg font-bold mb-5">修改密码</h3>
        <div v-if="pwdError" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg">{{ pwdError }}</div>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
            <input v-model="oldPwd" type="password" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">新密码</label>
            <input v-model="newPwd" type="password" placeholder="至少6位" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
            <input v-model="newPwd2" type="password" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button class="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm" @click="showPassword = false">取消</button>
          <button class="px-4 py-2 bg-[#1677ff] text-white rounded-lg hover:bg-blue-600 text-sm disabled:opacity-50" :disabled="pwdLoading" @click="changePassword">
            {{ pwdLoading ? '修改中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
