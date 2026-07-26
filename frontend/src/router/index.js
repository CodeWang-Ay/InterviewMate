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
import AITools from '../pages/AITools.vue'
import PlanManager from '../pages/PlanManager.vue'
import InterviewArchive from '../pages/InterviewArchive.vue'
import RecordList from '../pages/RecordList.vue'
import ReportList from '../pages/ReportList.vue'
import Settings from '../pages/Settings.vue'
import Login from '../pages/Login.vue'
import Register from '../pages/Register.vue'
import UserCenter from '../pages/UserCenter.vue'
import UserInterview from '../pages/UserInterview.vue'
import TaskCenter from '../pages/TaskCenter.vue'
import RecruitmentHome from '../pages/RecruitmentHome.vue'
import AboutUs from '../pages/AboutUs.vue'

const redirectWithQuery = (path) => (to) => ({ path, query: to.query })

const routes = [
  { path: '/', component: RecruitmentHome },
  { path: '/jobs', redirect: redirectWithQuery('/jobs/social') },
  { path: '/jobs/social', component: RecruitmentHome },
  { path: '/jobs/campus', component: RecruitmentHome },
  { path: '/about', component: AboutUs },
  { path: '/admin', component: Home },
  { path: '/admin/interviewer', component: Interviewer },
  { path: '/admin/interviewer/chat', component: InterviewerTrainChat },
  { path: '/admin/interviewee', component: Interviewee },
  { path: '/chat', component: Chat },
  { path: '/admin/report', component: Report },
  { path: '/admin/interview-record', component: InterviewRecord },
  { path: '/admin/jd-manager', component: JdManager },
  { path: '/admin/resume-manager', component: ResumeManager },
  { path: '/admin/ai-tools', component: AITools },
  { path: '/admin/plan-manager', component: PlanManager },
  { path: '/admin/interview-archive', component: InterviewArchive },
  { path: '/admin/record-list', component: RecordList },
  { path: '/admin/report-list', component: ReportList },
  { path: '/admin/settings', component: Settings },
  { path: '/admin/tasks', component: TaskCenter },
  { path: '/interviewer', redirect: redirectWithQuery('/admin/interviewer') },
  { path: '/interviewer/chat', redirect: redirectWithQuery('/admin/interviewer/chat') },
  { path: '/interviewee', redirect: redirectWithQuery('/admin/interviewee') },
  { path: '/report', redirect: redirectWithQuery('/admin/report') },
  { path: '/interview-record', redirect: redirectWithQuery('/admin/interview-record') },
  { path: '/jd-manager', redirect: redirectWithQuery('/admin/jd-manager') },
  { path: '/resume-manager', redirect: redirectWithQuery('/admin/resume-manager') },
  { path: '/ai-tools', redirect: redirectWithQuery('/admin/ai-tools') },
  { path: '/plan-manager', redirect: redirectWithQuery('/admin/plan-manager') },
  { path: '/interview-archive', redirect: redirectWithQuery('/admin/interview-archive') },
  { path: '/record-list', redirect: redirectWithQuery('/admin/record-list') },
  { path: '/report-list', redirect: redirectWithQuery('/admin/report-list') },
  { path: '/settings', redirect: redirectWithQuery('/admin/settings') },
  { path: '/tasks', redirect: redirectWithQuery('/admin/tasks') },
  { path: '/user-center', redirect: redirectWithQuery('/admin/user-center') },
  { path: '/login', redirect: redirectWithQuery('/admin/login') },
  { path: '/admin/login', component: Login },
  { path: '/user/login', component: Login },
  { path: '/register', component: Register },
  { path: '/admin/user-center', component: UserCenter },
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
  const publicPages = ['/', '/jobs', '/jobs/social', '/jobs/campus', '/about', '/login', '/admin/login', '/user/login', '/register']
  let token = ''
  let role = ''
  try { token = localStorage.getItem('token') || '' } catch (_) {}
  try { role = localStorage.getItem('role') || '' } catch (_) {}
  if (!token && !publicPages.includes(to.path)) {
    const loginPath = to.path.startsWith('/user') ? '/user/login' : '/admin/login'
    return { path: loginPath, query: { redirect: to.fullPath } }
  }
  if (token && !publicPages.includes(to.path)) {
    const session = await ensureSessionValid(token)
    if (!session.ok) {
      clearLocalAuth()
      sessionCheckedToken = ''
      sessionCheckedRole = ''
      const loginPath = to.path.startsWith('/user') ? '/user/login' : '/admin/login'
      return { path: loginPath, query: { redirect: to.fullPath } }
    }
    role = session.role || role
  }
  const candidatePages = ['/user']
  if (candidatePages.includes(to.path) && role && role !== 'candidate') {
    return { path: '/admin' }
  }
  const adminPages = ['/admin', '/admin/interviewer', '/admin/interviewer/chat', '/admin/interviewee', '/admin/jd-manager', '/admin/resume-manager', '/admin/ai-tools', '/admin/plan-manager', '/admin/report', '/admin/interview-record', '/admin/record-list', '/admin/report-list', '/admin/interview-archive', '/admin/settings', '/admin/tasks', '/admin/user-center']
  if (adminPages.includes(to.path)) {
    if (role !== 'admin') {
      try { window.alert('仅管理员可查看面试记录和面试报告') } catch (_) {}
      return from.path ? false : { path: '/admin/login' }
    }
  }
})

export default router
