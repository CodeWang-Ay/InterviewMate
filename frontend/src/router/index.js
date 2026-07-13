import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import Interviewer from '../pages/Interviewer.vue'
import Interviewee from '../pages/Interviewee.vue'
import Chat from '../pages/Chat.vue'
import Report from '../pages/Report.vue'
import InterviewRecord from '../pages/InterviewRecord.vue'
import JdManager from '../pages/JdManager.vue'
import ResumeManager from '../pages/ResumeManager.vue'
import PlanManager from '../pages/PlanManager.vue'
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
  { path: '/interviewee', component: Interviewee },
  { path: '/chat', component: Chat },
  { path: '/report', component: Report },
  { path: '/interview-record', component: InterviewRecord },
  { path: '/jd-manager', component: JdManager },
  { path: '/resume-manager', component: ResumeManager },
  { path: '/plan-manager', component: PlanManager },
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

// 路由守卫：未登录跳转登录页
router.beforeEach((to, from) => {
  const publicPages = ['/login', '/user/login', '/register']
  let token = ''
  try { token = localStorage.getItem('token') || '' } catch (_) {}
  if (!token && !publicPages.includes(to.path)) {
    const loginPath = to.path.startsWith('/user') ? '/user/login' : '/login'
    return { path: loginPath, query: { redirect: to.fullPath } }
  }
  // 仅管理员可访问面试报告和面试记录
  const adminPages = ['/report', '/interview-record', '/record-list', '/report-list']
  if (adminPages.includes(to.path)) {
    let role = ''
    try { role = localStorage.getItem('role') || 'user' } catch (_) {}
    if (role !== 'admin') {
      return from.path || '/'
    }
  }
})

export default router
