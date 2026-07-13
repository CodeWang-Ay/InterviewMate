import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import Interviewer from '../pages/Interviewer.vue'
import InterviewerTrainChat from '../pages/InterviewerTrainChat.vue'
import Interviewee from '../pages/Interviewee.vue'
import Chat from '../pages/Chat.vue'
import Report from '../pages/Report.vue'
import InterviewRecord from '../pages/InterviewRecord.vue'
import JdManager from '../pages/JdManager.vue'
import ResumeManager from '../pages/ResumeManager.vue'
import PlanManager from '../pages/PlanManager.vue'
import InterviewArchive from '../pages/InterviewArchive.vue'
import RecordList from '../pages/RecordList.vue'
import ReportList from '../pages/ReportList.vue'
import Settings from '../pages/Settings.vue'
import Login from '../pages/Login.vue'
import Register from '../pages/Register.vue'
import UserCenter from '../pages/UserCenter.vue'
import UserInterview from '../pages/UserInterview.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/interviewer', component: Interviewer },
  { path: '/interviewer/chat', component: InterviewerTrainChat },
  { path: '/interviewee', component: Interviewee },
  { path: '/chat', component: Chat },
  { path: '/report', component: Report },
  { path: '/interview-record', component: InterviewRecord },
  { path: '/jd-manager', component: JdManager },
  { path: '/resume-manager', component: ResumeManager },
  { path: '/plan-manager', component: PlanManager },
  { path: '/interview-archive', component: InterviewArchive },
  { path: '/record-list', component: RecordList },
  { path: '/report-list', component: ReportList },
  { path: '/settings', component: Settings },
  { path: '/login', component: Login },
  { path: '/user/login', component: Login },
  { path: '/register', component: Register },
  { path: '/user-center', component: UserCenter },
  { path: '/user', component: UserInterview },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

let sessionCheckedToken = ''
let sessionCheckedRole = ''
let pendingSessionCheck = null

function clearLocalAuth() {
  try {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('nickname')
    localStorage.removeItem('avatar')
    localStorage.removeItem('role')
    localStorage.removeItem('email')
    localStorage.removeItem('phone')
    localStorage.removeItem('company')
    localStorage.removeItem('bio')
  } catch (_) {
    // ignore
  }
}

async function ensureSessionValid(token) {
  if (!token) return { ok: false }
  if (token === sessionCheckedToken) return { ok: true, role: sessionCheckedRole }
  if (pendingSessionCheck) return pendingSessionCheck

  pendingSessionCheck = fetch('/api/auth/session', {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(async (res) => {
      if (!res.ok) return { ok: false }
      const data = await res.json().catch(() => ({}))
      const role = data.role || ''
      sessionCheckedToken = token
      sessionCheckedRole = role
      try {
        if (role) localStorage.setItem('role', role)
        if (data.username) localStorage.setItem('username', data.username)
        if (data.nickname) localStorage.setItem('nickname', data.nickname)
      } catch (_) {
        // ignore
      }
      return { ok: true, role }
    })
    .finally(() => {
      pendingSessionCheck = null
    })

  return pendingSessionCheck
}

// 路由守卫：未登录跳转登录页
router.beforeEach(async (to, from) => {
  const publicPages = ['/login', '/user/login', '/register']
  let token = ''
  let role = ''
  try { token = localStorage.getItem('token') || '' } catch (_) {}
  try { role = localStorage.getItem('role') || '' } catch (_) {}
  if (!token && !publicPages.includes(to.path)) {
    const loginPath = to.path.startsWith('/user') ? '/user/login' : '/login'
    return { path: loginPath, query: { redirect: to.fullPath } }
  }
  if (token && !publicPages.includes(to.path)) {
    const session = await ensureSessionValid(token)
    if (!session.ok) {
      clearLocalAuth()
      sessionCheckedToken = ''
      sessionCheckedRole = ''
      const loginPath = to.path.startsWith('/user') ? '/user/login' : '/login'
      return { path: loginPath, query: { redirect: to.fullPath } }
    }
    role = session.role || role
  }
  const candidatePages = ['/user']
  if (candidatePages.includes(to.path) && role && role !== 'candidate') {
    return { path: '/' }
  }
  const adminPages = ['/interviewer', '/interviewer/chat', '/interviewee', '/jd-manager', '/resume-manager', '/plan-manager', '/report', '/interview-record', '/record-list', '/report-list', '/interview-archive', '/settings', '/user-center']
  if (adminPages.includes(to.path)) {
    if (role !== 'admin') {
      try { window.alert('仅管理员可查看面试记录和面试报告') } catch (_) {}
      return from.path ? false : { path: '/' }
    }
  }
})

export default router
