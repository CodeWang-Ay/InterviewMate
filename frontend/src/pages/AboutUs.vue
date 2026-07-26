<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import aboutAgentImage from '../../images/about_agent.png'
import aboutLlmImage from '../../images/about_llm.png'
import aboutMultiAgentImage from '../../images/about_multi_agent.png'
import aboutTopImage from '../../images/about_top.png'

const router = useRouter()
const username = ref('')
const nickname = ref('')
const role = ref('')

try {
  username.value = localStorage.getItem('username') || ''
  nickname.value = localStorage.getItem('nickname') || ''
  role.value = localStorage.getItem('role') || ''
} catch (_) {
  username.value = ''
  nickname.value = ''
  role.value = ''
}

const displayedName = computed(() => nickname.value || username.value || '')
const isLoggedIn = computed(() => Boolean(username.value || localStorage.getItem('token')))
const centerPath = computed(() => role.value === 'candidate' ? '/user' : '/admin/user-center')

const capabilities = [
  { title: 'LLM 操作核心', desc: '把研究、判断、写作、代码和评估交给大模型协作完成，让一个人拥有更高密度的认知杠杆。', label: 'LLM Core', image: aboutLlmImage },
  { title: 'Agent 工作流', desc: '用 Agent 承接检索、规划、执行、验证和复盘，把想法拆成可以连续推进的任务链路。', label: 'Agent Workflow', image: aboutAgentImage },
  { title: 'Multi-Agent 协作网络', desc: '让多个智能体像一支小型团队一样分工协作，覆盖产品、工程、内容、运营和增长。', label: 'Multi-Agent', image: aboutMultiAgentImage },
]

const news = [
  { date: '2026.07', title: 'OPC Mate 启动 AI-native 一人公司实验室', tag: 'Company Lab' },
  { date: '2026.06', title: 'Multi-Agent 研发、内容与运营工作流进入内测', tag: 'Agent System' },
  { date: '2026.05', title: 'LLM 记忆、任务状态和工具调用链路完成整合', tag: 'Model Ops' },
  { date: '2026.04', title: '第一个由 Agent 协作完成的产品原型上线', tag: 'Prototype' },
]

const cultureCards = [
  { title: '一人公司', desc: '用模型和工具把个人判断扩展成可持续运行的小型组织。' },
  { title: '智能团队', desc: '让 Agent 分担重复、复杂和跨领域协作，把人留在关键决策上。' },
  { title: '快速试错', desc: '以产品原型验证想法，让每一次实验都沉淀成下一次能力。' },
  { title: '持续复利', desc: '把提示词、流程、数据和工具链积累成长期可复用资产。' },
]

const operatingLayers = [
  { title: 'Context & Memory', desc: '用 RAG、长期记忆和项目知识库保留上下文，让每次协作都站在已有资产上。', tags: ['RAG', 'Memory', 'Knowledge Base'] },
  { title: 'Tool Calling', desc: '让模型调用代码、搜索、文档、数据库和自动化工具，把回答变成可执行动作。', tags: ['Function Calling', 'API', 'Automation'] },
  { title: 'Workflow Orchestration', desc: '把模糊目标拆成任务流，串联计划、执行、检查、发布和复盘。', tags: ['Planning', 'Task Graph', 'Ops'] },
  { title: 'Evaluation Loop', desc: '通过评测、日志、人工审阅和版本记录，让 Agent 的输出可观察、可纠偏、可复用。', tags: ['Eval', 'Observability', 'HITL'] },
]

const focusItems = [
  'AI 原生产品原型与可自托管工具',
  'LLM 应用、RAG 知识库与智能文档系统',
  'Agent 工作流、自动化脚本与轻量 B 端系统',
  '把个人经验沉淀为可复制的软件资产',
]

const avoidItems = [
  '堆人数解决问题的重运营模式',
  '一次性交付后无法复用的零散外包',
  '只有概念没有可运行产品的展示项目',
  '脱离用户真实场景的纯技术炫技',
]

function goLogin() {
  router.push('/user/login?redirect=/user')
}

function goCenter() {
  router.push(centerPath.value)
}
</script>

<template>
  <div class="min-h-screen bg-[#f6f7fb] text-[#182033]">
    <header class="fixed left-0 right-0 top-0 z-30 border-b border-white/10 bg-[#071c22]/88 text-white backdrop-blur-xl">
      <div class="mx-auto flex h-16 max-w-[1680px] items-center justify-between px-5 lg:px-8">
        <button class="flex items-center gap-3" @click="router.push('/')">
          <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-black text-[#0f9f8f]">AI</span>
          <span class="text-lg font-bold">OPC Mate 招聘</span>
        </button>
        <nav class="hidden items-center gap-8 text-sm font-semibold text-white/82 md:flex">
          <button @click="router.push('/')">首页</button>
          <button @click="router.push('/jobs/social')">社会招聘</button>
          <button @click="router.push('/jobs/campus')">校园招聘</button>
          <button class="text-[#72f2d1]">了解我们</button>
          <button v-if="isLoggedIn" @click="goCenter">个人中心</button>
        </nav>
        <div class="flex items-center gap-3 text-sm font-semibold">
          <button v-if="isLoggedIn" class="rounded-full px-3 py-2 text-white/90 hover:bg-white/10" @click="goCenter">
            你好，{{ displayedName || '用户' }} <i class="fa fa-angle-down ml-1"></i>
          </button>
          <button v-else class="rounded-full px-3 py-2 text-white/90 hover:bg-white/10" @click="goLogin">登录/注册</button>
        </div>
      </div>
    </header>

    <section class="about-hero relative min-h-[760px] overflow-hidden pt-16 text-white">
      <img :src="aboutTopImage" alt="" class="absolute inset-0 h-full w-full object-cover" />
      <div class="absolute inset-0 bg-[linear-gradient(120deg,rgba(6,24,25,0.66)_0%,rgba(8,47,50,0.62)_46%,rgba(8,25,31,0.78)_100%)]"></div>
      <div class="hero-glow absolute inset-0"></div>
      <div class="about-orbit orbit-a"></div>
      <div class="about-orbit orbit-b"></div>
      <div class="about-orbit orbit-c"></div>
      <div class="absolute inset-0 opacity-70">
        <span class="absolute rounded-full bg-white/70" style="left: 41%; top: 69%; width: 3px; height: 3px; opacity: 0.31;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 82%; top: 50%; width: 4px; height: 4px; opacity: 0.4;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 23%; top: 31%; width: 5px; height: 5px; opacity: 0.49;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 64%; top: 12%; width: 2px; height: 2px; opacity: 0.58;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 5%; top: 71%; width: 3px; height: 3px; opacity: 0.67;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 46%; top: 52%; width: 4px; height: 4px; opacity: 0.76;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 87%; top: 33%; width: 5px; height: 5px; opacity: 0.25;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 28%; top: 14%; width: 2px; height: 2px; opacity: 0.34;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 69%; top: 73%; width: 3px; height: 3px; opacity: 0.43;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 10%; top: 54%; width: 4px; height: 4px; opacity: 0.52;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 51%; top: 35%; width: 5px; height: 5px; opacity: 0.61;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 92%; top: 16%; width: 2px; height: 2px; opacity: 0.7;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 33%; top: 75%; width: 3px; height: 3px; opacity: 0.79;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 74%; top: 56%; width: 4px; height: 4px; opacity: 0.28;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 15%; top: 37%; width: 5px; height: 5px; opacity: 0.37;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 56%; top: 18%; width: 2px; height: 2px; opacity: 0.46;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 97%; top: 77%; width: 3px; height: 3px; opacity: 0.55;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 38%; top: 58%; width: 4px; height: 4px; opacity: 0.64;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 79%; top: 39%; width: 5px; height: 5px; opacity: 0.73;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 20%; top: 20%; width: 2px; height: 2px; opacity: 0.22;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 61%; top: 79%; width: 3px; height: 3px; opacity: 0.31;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 2%; top: 60%; width: 4px; height: 4px; opacity: 0.4;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 43%; top: 41%; width: 5px; height: 5px; opacity: 0.49;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 84%; top: 22%; width: 2px; height: 2px; opacity: 0.58;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 25%; top: 81%; width: 3px; height: 3px; opacity: 0.67;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 66%; top: 62%; width: 4px; height: 4px; opacity: 0.76;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 7%; top: 43%; width: 5px; height: 5px; opacity: 0.25;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 48%; top: 24%; width: 2px; height: 2px; opacity: 0.34;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 89%; top: 83%; width: 3px; height: 3px; opacity: 0.43;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 30%; top: 64%; width: 4px; height: 4px; opacity: 0.52;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 71%; top: 45%; width: 5px; height: 5px; opacity: 0.61;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 12%; top: 26%; width: 2px; height: 2px; opacity: 0.7;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 53%; top: 85%; width: 3px; height: 3px; opacity: 0.79;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 94%; top: 66%; width: 4px; height: 4px; opacity: 0.28;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 35%; top: 47%; width: 5px; height: 5px; opacity: 0.37;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 76%; top: 28%; width: 2px; height: 2px; opacity: 0.46;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 17%; top: 87%; width: 3px; height: 3px; opacity: 0.55;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 58%; top: 68%; width: 4px; height: 4px; opacity: 0.64;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 99%; top: 49%; width: 5px; height: 5px; opacity: 0.73;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 40%; top: 30%; width: 2px; height: 2px; opacity: 0.22;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 81%; top: 11%; width: 3px; height: 3px; opacity: 0.31;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 22%; top: 70%; width: 4px; height: 4px; opacity: 0.4;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 63%; top: 51%; width: 5px; height: 5px; opacity: 0.49;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 4%; top: 32%; width: 2px; height: 2px; opacity: 0.58;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 45%; top: 13%; width: 3px; height: 3px; opacity: 0.67;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 86%; top: 72%; width: 4px; height: 4px; opacity: 0.76;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 27%; top: 53%; width: 5px; height: 5px; opacity: 0.25;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 68%; top: 34%; width: 2px; height: 2px; opacity: 0.34;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 9%; top: 15%; width: 3px; height: 3px; opacity: 0.43;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 50%; top: 74%; width: 4px; height: 4px; opacity: 0.52;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 91%; top: 55%; width: 5px; height: 5px; opacity: 0.61;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 32%; top: 36%; width: 2px; height: 2px; opacity: 0.7;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 73%; top: 17%; width: 3px; height: 3px; opacity: 0.79;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 14%; top: 76%; width: 4px; height: 4px; opacity: 0.28;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 55%; top: 57%; width: 5px; height: 5px; opacity: 0.37;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 96%; top: 38%; width: 2px; height: 2px; opacity: 0.46;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 37%; top: 19%; width: 3px; height: 3px; opacity: 0.55;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 78%; top: 78%; width: 4px; height: 4px; opacity: 0.64;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 19%; top: 59%; width: 5px; height: 5px; opacity: 0.73;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 60%; top: 40%; width: 2px; height: 2px; opacity: 0.22;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 1%; top: 21%; width: 3px; height: 3px; opacity: 0.31;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 42%; top: 80%; width: 4px; height: 4px; opacity: 0.4;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 83%; top: 61%; width: 5px; height: 5px; opacity: 0.49;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 24%; top: 42%; width: 2px; height: 2px; opacity: 0.58;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 65%; top: 23%; width: 3px; height: 3px; opacity: 0.67;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 6%; top: 82%; width: 4px; height: 4px; opacity: 0.76;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 47%; top: 63%; width: 5px; height: 5px; opacity: 0.25;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 88%; top: 44%; width: 2px; height: 2px; opacity: 0.34;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 29%; top: 25%; width: 3px; height: 3px; opacity: 0.43;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 70%; top: 84%; width: 4px; height: 4px; opacity: 0.52;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 11%; top: 65%; width: 5px; height: 5px; opacity: 0.61;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 52%; top: 46%; width: 2px; height: 2px; opacity: 0.7;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 93%; top: 27%; width: 3px; height: 3px; opacity: 0.79;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 34%; top: 86%; width: 4px; height: 4px; opacity: 0.28;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 75%; top: 67%; width: 5px; height: 5px; opacity: 0.37;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 16%; top: 48%; width: 2px; height: 2px; opacity: 0.46;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 57%; top: 29%; width: 3px; height: 3px; opacity: 0.55;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 98%; top: 10%; width: 4px; height: 4px; opacity: 0.64;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 39%; top: 69%; width: 5px; height: 5px; opacity: 0.73;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 80%; top: 50%; width: 2px; height: 2px; opacity: 0.22;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 21%; top: 31%; width: 3px; height: 3px; opacity: 0.31;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 62%; top: 12%; width: 4px; height: 4px; opacity: 0.4;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 3%; top: 71%; width: 5px; height: 5px; opacity: 0.49;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 44%; top: 52%; width: 2px; height: 2px; opacity: 0.58;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 85%; top: 33%; width: 3px; height: 3px; opacity: 0.67;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 26%; top: 14%; width: 4px; height: 4px; opacity: 0.76;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 67%; top: 73%; width: 5px; height: 5px; opacity: 0.25;"></span>
        <span class="absolute rounded-full bg-white/70" style="left: 8%; top: 54%; width: 2px; height: 2px; opacity: 0.34;"></span>
      </div>

      <div class="relative mx-auto flex min-h-[700px] max-w-[1280px] flex-col items-center justify-center px-6 text-center">
        <div class="rounded-full border border-white/14 bg-white/8 px-5 py-2 text-sm font-semibold tracking-[0.24em] text-white/78">
          ABOUT OPC MATE
        </div>
        <h1 class="mt-8 text-[64px] font-black leading-none tracking-tight md:text-[118px]">OPC Mate</h1>
        <p class="mt-7 max-w-3xl text-xl leading-9 text-white/76">
          OPC Mate 是一家 AI-native 一人公司实验室。我们用 LLM、Agent 与 Multi-Agent 工作流，把一个人的想法、产品、内容和自动化系统，扩展成一支可协作的智能团队。
        </p>
        <div class="mt-11 grid w-full max-w-4xl gap-4 md:grid-cols-3">
          <div v-for="item in capabilities" :key="item.title" class="rounded-2xl border border-white/14 bg-white/10 p-5 text-left backdrop-blur">
            <div class="text-xs font-bold tracking-[0.16em] text-[#72f2d1]">{{ item.label }}</div>
            <div class="mt-3 text-xl font-bold">{{ item.title }}</div>
            <p class="mt-3 text-sm leading-6 text-white/68">{{ item.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="bg-white py-20">
      <div class="mx-auto grid max-w-[1180px] gap-10 px-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
        <div>
          <div class="text-sm font-bold tracking-[0.22em] text-[#0f9f8f]">ONE PERSON COMPANY</div>
          <h2 class="mt-3 text-4xl font-black leading-tight text-[#182033]">不是自由职业，也不是缩小版公司</h2>
          <p class="mt-6 leading-8 text-[#607272]">
            OPC Mate 的核心不是“一个人做所有事”，而是由一个人负责方向、判断和审美，用模型、工具链和 Agent 网络承接重复执行、跨领域协作与持续交付。
          </p>
          <div class="mt-7 rounded-2xl border-l-4 border-[#0f9f8f] bg-[#eefaf6] p-5 text-[#254241]">
            一人公司出售的不是时间，而是长期可复用的产品、流程、数据和自动化系统。
          </div>
        </div>
        <div class="overflow-hidden rounded-3xl border border-[#dfeaea] bg-[#fbfdfc] shadow-[0_20px_60px_rgba(15,45,45,0.08)]">
          <div class="grid grid-cols-[0.8fr_1.2fr] border-b border-[#e4eeee] bg-[#f2f7f5] px-6 py-4 text-sm font-bold text-[#4f6665]">
            <span>模式</span>
            <span>核心差异</span>
          </div>
          <div class="grid grid-cols-[0.8fr_1.2fr] border-b border-[#eaf0f0] px-6 py-5">
            <div class="font-bold">自由职业</div>
            <div class="text-[#667777]">主要出售个人时间，项目结束后资产沉淀有限。</div>
          </div>
          <div class="grid grid-cols-[0.8fr_1.2fr] border-b border-[#eaf0f0] bg-[#f4fffb] px-6 py-5">
            <div class="font-black text-[#0f9f8f]">OPC Mate</div>
            <div class="text-[#375655]">自研产品和系统资产，用 AI 工作流提高单人交付上限。</div>
          </div>
          <div class="grid grid-cols-[0.8fr_1.2fr] px-6 py-5">
            <div class="font-bold">传统组织</div>
            <div class="text-[#667777]">依赖层级和人员规模，管理成本更高，迭代路径更重。</div>
          </div>
        </div>
      </div>
    </section>

    <section class="mx-auto max-w-[1180px] px-6 py-20">
      <div class="mb-9 text-center">
        <div class="text-sm font-bold tracking-[0.22em] text-[#0f9f8f]">AI-NATIVE COMPANY</div>
        <h2 class="mt-3 text-3xl font-black text-[#182033]">一人公司背后的智能协作系统</h2>
      </div>
      <div class="grid gap-5 md:grid-cols-3">
        <article v-for="item in capabilities" :key="item.label" class="group overflow-hidden rounded-3xl bg-white shadow-[0_18px_50px_rgba(15,45,45,0.08)]">
          <div class="cap-image-wrap h-44 overflow-hidden bg-[#102a2d]">
            <img :src="item.image" :alt="item.title" class="h-full w-full object-cover transition duration-500 group-hover:scale-[1.04]" />
          </div>
          <div class="p-7">
            <div class="text-sm font-bold text-[#0f9f8f]">{{ item.label }}</div>
            <h3 class="mt-2 text-2xl font-black">{{ item.title }}</h3>
            <p class="mt-3 leading-7 text-[#5a6a6a]">{{ item.desc }}</p>
          </div>
        </article>
      </div>
    </section>

    <section class="bg-[#f6f7fb] py-20">
      <div class="mx-auto max-w-[1180px] px-6">
        <div class="mb-10 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <div class="text-sm font-bold tracking-[0.22em] text-[#0f9f8f]">OPERATING SYSTEM</div>
            <h2 class="mt-3 text-3xl font-black text-[#182033]">不只 LLM，而是一套 AI 公司操作系统</h2>
          </div>
          <p class="max-w-xl leading-7 text-[#607272]">
            大模型是发动机，Agent 是执行单元，但真正决定效率的是上下文、工具、流程和评估闭环。
          </p>
        </div>
        <div class="grid gap-5 md:grid-cols-2">
          <article v-for="item in operatingLayers" :key="item.title" class="rounded-3xl border border-white bg-white/86 p-7 shadow-[0_18px_50px_rgba(15,45,45,0.06)]">
            <div class="flex items-start justify-between gap-5">
              <div>
                <div class="text-sm font-black tracking-[0.18em] text-[#0f9f8f]">{{ item.title }}</div>
                <p class="mt-4 leading-7 text-[#516565]">{{ item.desc }}</p>
              </div>
              <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#071c22] text-white">
                <i class="fa fa-sitemap"></i>
              </div>
            </div>
            <div class="mt-6 flex flex-wrap gap-2">
              <span v-for="tag in item.tags" :key="tag" class="rounded-full bg-[#eef6ff] px-3 py-1 text-xs font-bold text-[#3275d8]">{{ tag }}</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="bg-white py-20">
      <div class="mx-auto grid max-w-[1180px] gap-12 px-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <div class="text-sm font-bold tracking-[0.22em] text-[#0f9f8f]">MATE LOG</div>
          <h2 class="mt-3 text-3xl font-black">OPC Mate 动态</h2>
          <p class="mt-5 max-w-md leading-8 text-[#607272]">
            OPC Mate 不追求庞大组织，而是探索一个人如何借助模型、工具和 Agent 网络完成研究、设计、开发、运营与增长。每一次迭代，都是把个人能力产品化的一次尝试。
          </p>
        </div>
        <div class="space-y-4">
          <div v-for="item in news" :key="item.title" class="flex gap-5 rounded-2xl border border-[#e4eeee] bg-[#fbfdfc] p-5">
            <div class="w-24 shrink-0 text-sm font-bold text-[#0f9f8f]">{{ item.date }}</div>
            <div class="min-w-0">
              <div class="text-xs font-bold tracking-[0.14em] text-[#9aa8a8]">{{ item.tag }}</div>
              <div class="mt-1 text-lg font-bold text-[#182033]">{{ item.title }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="mx-auto max-w-[1180px] px-6 py-20">
      <div class="grid gap-6 lg:grid-cols-2">
        <div class="rounded-3xl bg-[#071c22] p-8 text-white shadow-[0_22px_60px_rgba(7,28,34,0.16)]">
          <div class="flex items-center gap-3 text-xl font-black">
            <i class="fa fa-check-circle text-[#72f2d1]"></i>
            我们专注
          </div>
          <ul class="mt-7 space-y-4 text-white/76">
            <li v-for="item in focusItems" :key="item" class="flex gap-3">
              <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#72f2d1]"></span>
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
        <div class="rounded-3xl border border-[#dfeaea] bg-white p-8 shadow-[0_18px_50px_rgba(15,45,45,0.06)]">
          <div class="flex items-center gap-3 text-xl font-black text-[#182033]">
            <i class="fa fa-times-circle text-[#ff7a8a]"></i>
            我们不做
          </div>
          <ul class="mt-7 space-y-4 text-[#607272]">
            <li v-for="item in avoidItems" :key="item" class="flex gap-3">
              <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#ff7a8a]"></span>
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mx-auto max-w-[1180px] px-6 py-20">
      <div class="grid gap-5 md:grid-cols-4">
        <div v-for="item in cultureCards" :key="item.title" class="rounded-3xl border border-[#dfeaea] bg-white p-7 shadow-[0_16px_45px_rgba(15,45,45,0.06)]">
          <div class="text-3xl font-black text-[#0f9f8f]">{{ item.title }}</div>
          <p class="mt-4 leading-7 text-[#607272]">{{ item.desc }}</p>
        </div>
      </div>
    </section>

    <footer class="border-t border-[#e1eaea] bg-white">
      <div class="mx-auto flex max-w-[1180px] flex-col gap-4 px-6 py-10 text-sm text-[#667777] md:flex-row md:items-center md:justify-between">
        <div class="font-bold text-[#182033]">OPC Mate</div>
        <div class="flex flex-wrap gap-6">
          <span>关于我们</span>
          <span>一人公司</span>
          <span>LLM 工作流</span>
          <span>Agent 产品</span>
          <span>Multi-Agent 实验</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.hero-glow {
  background:
    radial-gradient(circle at 48% 44%, rgba(255, 245, 190, 0.2), rgba(45, 212, 191, 0.18) 16%, transparent 38%),
    radial-gradient(circle at 72% 22%, rgba(134, 239, 172, 0.12), transparent 28%),
    radial-gradient(circle at 24% 70%, rgba(14, 165, 233, 0.14), transparent 26%);
  animation: glow-breathe 8s ease-in-out infinite;
}

.about-orbit {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  transform: translate(-50%, -50%);
}

.orbit-a {
  width: 520px;
  height: 520px;
  animation: spin 42s linear infinite;
}

.orbit-b {
  width: 860px;
  height: 860px;
  border-style: dashed;
  animation: spin-reverse 64s linear infinite;
}

.orbit-c {
  width: 1180px;
  height: 1180px;
  border-style: dotted;
  animation: spin 92s linear infinite;
}

@keyframes spin {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes spin-reverse {
  from { transform: translate(-50%, -50%) rotate(360deg); }
  to { transform: translate(-50%, -50%) rotate(0deg); }
}

@keyframes glow-breathe {
  0%, 100% { opacity: 0.86; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.04); }
}

</style>
