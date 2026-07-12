<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '')
const nickname = ref(localStorage.getItem('nickname') || '用户')
const avatar = ref(localStorage.getItem('avatar') || `https://ui-avatars.com/api/?name=${encodeURIComponent(nickname.value)}&background=1677ff&color=fff&size=120`)
const uploading = ref(false)

// 编辑资料弹窗
const showProfile = ref(false)
const editNickname = ref('')
const profileLoading = ref(false)

// 修改密码弹窗
const showPassword = ref(false)
const oldPwd = ref('')
const newPwd = ref('')
const newPwd2 = ref('')
const pwdLoading = ref(false)
const pwdError = ref('')

async function onAvatarChange(e) {
  const file = e.target?.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/auth/avatar', { method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: fd })
    if (!res.ok) throw new Error('上传失败')
    const data = await res.json()
    avatar.value = data.avatar_url
    localStorage.setItem('avatar', data.avatar_url)
  } catch (_) { /* ignore */ }
  uploading.value = false
}

function openProfile() {
  editNickname.value = nickname.value
  showProfile.value = true
}

async function saveProfile() {
  if (!editNickname.value.trim()) return
  profileLoading.value = true
  try {
    const res = await fetch('/api/auth/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      body: JSON.stringify({ nickname: editNickname.value.trim() }),
    })
    if (!res.ok) throw new Error('保存失败')
    nickname.value = editNickname.value.trim()
    localStorage.setItem('nickname', nickname.value)
    showProfile.value = false
  } catch (_) { /* ignore */ }
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
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      body: JSON.stringify({ old_password: oldPwd.value, new_password: newPwd.value }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '修改失败')
    }
    showPassword.value = false
    alert('密码修改成功')
  } catch (e) {
    pwdError.value = e.message
  }
  pwdLoading.value = false
}

function doLogout() {
  localStorage.clear()
  router.push('/login')
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <Sidebar />

    <main class="flex-1 overflow-auto p-6">
      <h2 class="text-2xl font-bold text-gray-900 mb-6">用户中心</h2>

      <div class="bg-white rounded-2xl shadow-sm p-8 mb-6">
        <div class="flex items-center gap-6">
          <label class="relative cursor-pointer group">
            <img :src="avatar" alt="avatar" class="w-24 h-24 rounded-full object-cover">
            <div class="absolute inset-0 rounded-full bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
              <i v-if="uploading" class="fa fa-spinner fa-spin text-white text-xl"></i>
              <i v-else class="fa fa-camera text-white text-xl"></i>
            </div>
            <input type="file" accept="image/*" class="hidden" @change="onAvatarChange">
          </label>
          <div>
            <h3 class="text-xl font-bold text-gray-900">{{ nickname }}</h3>
            <p class="text-gray-500">@{{ username }}</p>
            <span class="inline-block mt-2 px-3 py-1 bg-blue-100 text-blue-600 text-xs rounded-full">专业版</span>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-xl p-5 shadow-sm text-center">
          <p class="text-3xl font-bold text-[#1677ff]">0</p>
          <p class="text-sm text-gray-500 mt-1">面试次数</p>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm text-center">
          <p class="text-3xl font-bold text-[#22c55e]">0</p>
          <p class="text-sm text-gray-500 mt-1">平均分</p>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm text-center">
          <p class="text-3xl font-bold text-purple-500">0</p>
          <p class="text-sm text-gray-500 mt-1">上传简历</p>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm text-center">
          <p class="text-3xl font-bold text-orange-500">0</p>
          <p class="text-sm text-gray-500 mt-1">生成报告</p>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm p-6 space-y-4">
        <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-gray-50 flex items-center gap-3" @click="openProfile">
          <i class="fa fa-user-circle text-[#1677ff] text-lg w-6 text-center"></i>
          <span class="text-sm">编辑个人资料</span>
          <i class="fa fa-chevron-right text-gray-300 ml-auto"></i>
        </button>
        <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-gray-50 flex items-center gap-3" @click="openPassword">
          <i class="fa fa-lock text-yellow-500 text-lg w-6 text-center"></i>
          <span class="text-sm">修改密码</span>
          <i class="fa fa-chevron-right text-gray-300 ml-auto"></i>
        </button>
        <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-gray-50 flex items-center gap-3">
          <i class="fa fa-history text-gray-400 text-lg w-6 text-center"></i>
          <span class="text-sm">操作日志</span>
          <i class="fa fa-chevron-right text-gray-300 ml-auto"></i>
        </button>
        <hr class="my-2">
        <button class="w-full text-left px-4 py-3 rounded-xl hover:bg-red-50 flex items-center gap-3" @click="doLogout">
          <i class="fa fa-sign-out text-red-500 text-lg w-6 text-center"></i>
          <span class="text-sm text-red-500">退出登录</span>
        </button>
      </div>
    </main>

    <!-- 编辑资料弹窗 -->
    <div v-if="showProfile" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showProfile = false">
      <div class="bg-white rounded-2xl w-[420px] p-6 shadow-xl">
        <h3 class="text-lg font-bold mb-5">编辑个人资料</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input :value="username" class="w-full border rounded-lg px-3 py-2 bg-gray-50 text-gray-500" disabled>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">昵称</label>
            <input v-model="editNickname" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:border-[#1677ff]">
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
