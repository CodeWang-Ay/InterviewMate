# InterviewMate — AI 面试官系统

基于大语言模型的智能招聘面试平台，覆盖从 JD 管理、简历解析、面试计划编排到 AI 实时对话、语音交互、数字人面试官的全流程。

**两周从零搭建，约 19,000 行代码。**

---

## 功能概览

### 🤖 AI 面试对话
- 基于 LLM 的结构化面试，自动生成针对性问题
- 回答质量实时评估，支持最多 3 轮智能追问
- 问题来源标注（JD / 简历 / 行为面），可追溯
- 流式响应输出，打字机效果

### 📋 面试计划管理
- 多轮次工作流编排（技术一面 → 二面 → HR 面 → 终面）
- 可视化流程模板编辑器，拖拽调整面试环节
- 面试状态机：待进入 → 等待 → 进行中 → 已完成 / 已取消
- 自动创建候选人账号，一键复制登录信息

### 🎤 语音交互
- FunASR 实时流式语音识别（WebSocket + 双 pass 精校）
- 按住说话 / 空格键语音输入，松开自动发送
- Edge TTS 语音合成，面试官回复自动朗读
- 前端音频采集、线性重采样、WAV 编码全链路

### 👤 Live2D 数字人面试官
- PIXI.js + Cubism SDK 4 驱动
- Web Audio API 实时唇形同步
- 可拖拽位置，状态动画响应（聆听中 / 思考中 / 在线）

### 📄 简历管理
- PDF / DOCX 上传解析，LLM 提取结构化信息
- MD5 解析缓存，避免重复调用
- 简历评分、润色（对比 JD 输出改进建议）
- 智能关键词提取

### 📊 JD 管理
- 岗位 JD CRUD + 版本历史 + 回滚
- AI 智能生成 JD 草稿
- AI 优化已有 JD（修改前后对比）
- 分类筛选、批量操作

### 📈 面试报告
- 多维度评分（沟通表达 / 技术匹配 / 项目经验 / 问题解决）
- 面试官训练复盘报告（岗位覆盖 / 追问深度 / 案例挖掘 / 节奏 / 结构）
- 雷达图可视化
- 面试记录回放

### 🎯 面试官训练
- AI 扮演候选人，5 种风格（标准 / 紧张 / 强势 / 含糊 / 经验包装）
- 4 种训练模式（结构化面试 / 行为面试 / 技术面试 / 压力面试）
- 训练后生成复盘报告

### 🔐 用户体系
- 管理员 / 候选人双角色
- bcrypt 密码哈希
- Bearer Token 鉴权
- 路由守卫 + 全局 401 拦截

### 💬 AI 聊天助手
- 浮动助手小部件，可拖拽、全屏
- 流式对话，角色感知（自动区分管理员/候选人语境）
- Markdown 渲染，代码高亮

### 🏠 候选人门户
- 招聘职位浏览（社会招聘 / 校园招聘）
- 个人中心：投递记录、面试进度、简历查看
- 动画首页（流星、轨道、星空效果）

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI (Python) |
| **前端框架** | Vue 3 (Composition API) + Vue Router |
| **构建工具** | Vite 5 |
| **样式** | Tailwind CSS |
| **数据库** | SQLite |
| **AI / LLM** | OpenAI 兼容 API（千问 qwen-plus） |
| **语音识别** | FunASR (Paraformer + FSMN-VAD) |
| **语音合成** | Edge TTS |
| **数字人** | Live2D Cubism SDK 4 + PIXI.js |
| **密码哈希** | bcrypt |
| **Python 依赖管理** | uv |
| **其他依赖** | PyPDF, python-docx, json-repair, loguru |

---

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）

### 1. 克隆项目

```bash
git clone <repo-url>
cd InterviewMate
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入 API Key：

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 3. 安装后端依赖

```bash
uv sync
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

### 5. 启动开发服务

**后端**（端口 8000）：

```bash
uv run python main.py
```

**前端**（端口 5173）：

```bash
cd frontend
npm run dev
```

访问 http://localhost:5173

### 6. 默认管理员账号

```
用户名：admin
密码：admin123
```

### 7. 生产构建

```bash
cd frontend && npm run build
uv run python main.py   # 后端自动 serve 前端静态文件
```

访问 http://localhost:8000

---

## 项目结构

```
InterviewMate/
├── main.py                    # FastAPI 入口，路由注册，静态文件 serve
├── pyproject.toml             # Python 项目配置
├── backend/
│   ├── config.py              # 全局配置（路径、常量）
│   ├── controllers/           # 控制器层（路由处理）
│   │   ├── auth_controller.py         # 登录/注册/鉴权
│   │   ├── chat_controller.py         # 面试对话
│   │   ├── interview_controller.py    # 旧版面试 API
│   │   ├── plan_controller.py         # 面试计划管理
│   │   ├── jd_controller.py           # JD 管理
│   │   ├── resume_controller.py       # 简历管理
│   │   ├── report_controller.py       # 面试报告
│   │   ├── record_controller.py       # 面试记录
│   │   ├── archive_controller.py      # 面试档案
│   │   ├── voice_controller.py        # 语音 ASR/TTS/WebSocket
│   │   ├── assistant_controller.py    # AI 助手
│   │   ├── ai_tools_controller.py     # AI 工具（简历评分/润色）
│   │   ├── task_controller.py         # 异步任务
│   │   └── interviewer_training_controller.py  # 面试官训练
│   ├── services/              # 服务层（核心业务逻辑）
│   │   ├── chat_service.py            # 面试对话引擎（状态机/追问/评估）
│   │   ├── llm_service.py             # LLM 调用封装（简历解析）
│   │   ├── voice_service.py           # 语音识别/合成
│   │   ├── report_service.py          # 报告生成
│   │   ├── assistant_service.py       # AI 助手对话
│   │   ├── interviewer_training_service.py  # 面试官训练
│   │   ├── jd_copilot_service.py      # JD 智能生成/优化
│   │   ├── resume_copilot_service.py  # 简历评分/润色
│   │   ├── file_service.py            # 文件解析
│   │   └── task_service.py            # 异步任务
│   ├── repositories/          # 数据访问层（SQLite）
│   │   ├── admin_repo.py
│   │   ├── candidate_repo.py
│   │   ├── plan_repo.py
│   │   ├── jd_repo.py
│   │   ├── resume_repo.py
│   │   ├── interview_repo.py
│   │   ├── task_repo.py
│   │   └── ...
│   ├── models/
│   │   └── schemas.py         # Pydantic 数据模型
│   └── utils/
│       └── resume_normalizer.py  # 简历结构标准化
├── frontend/
│   ├── src/
│   │   ├── main.js            # Vue 入口，全局 fetch 拦截
│   │   ├── App.vue
│   │   ├── router/index.js    # 路由配置 + 守卫
│   │   ├── pages/             # 22 个页面组件
│   │   │   ├── Chat.vue               # 面试对话（含语音+Live2D）
│   │   │   ├── PlanManager.vue        # 面试计划管理
│   │   │   ├── ResumeManager.vue      # 简历管理
│   │   │   ├── JdManager.vue          # JD 管理
│   │   │   ├── UserInterview.vue      # 候选人个人中心
│   │   │   ├── RecruitmentHome.vue    # 招聘首页
│   │   │   ├── InterviewArchive.vue   # 面试档案
│   │   │   ├── Report.vue             # 面试报告（含雷达图）
│   │   │   └── ...
│   │   └── components/
│   │       ├── Sidebar.vue            # 侧边栏导航
│   │       └── AIAssistantWidget.vue  # AI 浮动助手
│   ├── images/                # 静态图片
│   └── static/                # favicon / PWA manifest / Live2D 模型
├── tests/                     # 测试脚本
├── prototype/                 # 早期 HTML 原型
└── data/                      # SQLite 数据库文件
```

---

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Vue 3)                      │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ 管理后台 │ │ 候选人门户│ │ Chat 面试对话      │  │
│  │ 22 pages │ │ 3 pages  │ │ + 语音 + Live2D    │  │
│  └──────────┘ └──────────┘ └────────────────────┘  │
└──────────────────┬──────────────────────────────────┘
                   │ REST API / WebSocket
┌──────────────────┴──────────────────────────────────┐
│                 后端 (FastAPI)                       │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ Controllers│  │  Services  │  │ Repositories │  │
│  │ (路由/鉴权) │──│ (业务逻辑) │──│ (SQLite CRUD)│  │
│  └────────────┘  └────────────┘  └──────────────┘  │
│                         │                           │
│  ┌──────────────────────┼──────────────────────┐   │
│  │ OpenAI API │ FunASR │ Edge TTS │ Live2D    │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

面试对话核心流程：

```
用户进入 → 加载面试计划 → 生成/加载题目
    ↓
READY_CHECK（确认准备） → 打招呼
    ↓
INTERVIEWING（面试中）
    ├── 用户回答 → LLM 评估质量
    │   ├── 不合格 → 追问（最多 3 次）
    │   └── 合格 → 下一题
    ↓
COMPLETED（结束） → 生成报告 → 保存记录
```

---

## 注意事项

- 本项目为个人学习项目，适合作为 AI 应用开发的技术参考
- 语音功能需要麦克风权限，推荐使用 Chrome / Edge
- FunASR 模型首次启动会自动下载（约 1-2 GB）
- Live2D 模型文件需放置在 `frontend/dist/hiyori_pro_zh/` 目录下
- 生产部署前建议：迁移至 PostgreSQL、添加 Redis 会话管理、引入 CI/CD

---

## License

MIT
