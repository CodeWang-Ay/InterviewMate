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
  { path: '/register', component: Register },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录跳转登录页
router.beforeEach((to) => {
  const publicPages = ['/login', '/register']
  const token = localStorage.getItem('token')
  if (!token && !publicPages.includes(to.path)) {
    return '/login'
  }
})

export default router
