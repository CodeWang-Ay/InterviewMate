import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import Interviewer from '../pages/Interviewer.vue'
import Interviewee from '../pages/Interviewee.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/interviewer', component: Interviewer },
  { path: '/interviewee', component: Interviewee },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
