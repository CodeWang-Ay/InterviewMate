import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import Interviewer from '../pages/Interviewer.vue'
import Interviewee from '../pages/Interviewee.vue'
import Chat from '../pages/Chat.vue'
import Report from '../pages/Report.vue'
import InterviewRecord from '../pages/InterviewRecord.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/interviewer', component: Interviewer },
  { path: '/interviewee', component: Interviewee },
  { path: '/chat', component: Chat },
  { path: '/report', component: Report },
  { path: '/interview-record', component: InterviewRecord },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
