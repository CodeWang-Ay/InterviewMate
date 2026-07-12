import json
import os
import re
import time
import uuid
from datetime import datetime

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="InterviewMate")

# 允许的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 上传目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
INTERVIEW_DIR = os.path.join(BASE_DIR, "interviews")
os.makedirs(os.path.join(UPLOAD_DIR, "jd"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "resume"), exist_ok=True)
os.makedirs(INTERVIEW_DIR, exist_ok=True)

# 面试会话存储
chat_sessions: dict[str, dict] = {}

# 默认面试问题
DEFAULT_QUESTIONS = [
    "请做一个简短的自我介绍，重点介绍与这个岗位相关的经历。",
    "根据 JD 中的核心技术要求，请分享一个你做过的相关项目，遇到了哪些挑战，如何解决的？",
    "对于这个岗位所需的技术栈，你的理解深度如何？有深入学习过哪些方面？",
    "请描述一次你在团队中解决冲突或推动协作的经历。",
    "你对这个岗位的期望是什么？未来 3 年的职业规划是怎样的？",
    "你有什么问题想问我们吗？",
]


def validate_file(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


async def save_file(file: UploadFile, subdir: str, ext: str) -> str:
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, subdir, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filename


def read_resume_file(filename: str) -> str:
    filepath = os.path.join(UPLOAD_DIR, "resume", filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".txt", ".md"):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    elif ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise HTTPException(status_code=400, detail=f"无法读取格式: {ext}")


def extract_questions_from_jd(jd_text: str) -> list[str]:
    """尝试从 JD 提取问题；失败则返回默认问题"""
    lines = jd_text.strip().split("\n")
    questions = []
    in_section = False
    for line in lines:
        line = line.strip()
        if "面试问题" in line or "建议问题" in line:
            in_section = True
            continue
        if in_section and re.match(r"^\d+[\.\、\)]", line):
            q = re.sub(r"^\d+[\.\、\)]\s*", "", line).strip()
            if q:
                questions.append(q)
    return questions if questions else DEFAULT_QUESTIONS


def save_interview_record(session_id: str):
    """将面试记录持久化到 JSON 文件"""
    session = chat_sessions.get(session_id)
    if not session:
        return
    record = {
        "session_id": session_id,
        "jd_filename": session.get("jd_filename"),
        "resume_filename": session.get("resume_filename"),
        "questions": session.get("questions", []),
        "state": session.get("state"),
        "question_index": session.get("question_index", 0),
        "history": session.get("history", []),
        "created_at": session.get("created_at"),
        "completed_at": datetime.now().isoformat(),
    }
    filepath = os.path.join(INTERVIEW_DIR, f"{session_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    print(f"[会话 {session_id}] 记录已保存到 {filepath}")


def analyze_interview(session_id: str) -> dict:
    """多维面试分析，返回报告"""
    record_path = os.path.join(INTERVIEW_DIR, f"{session_id}.json")
    if not os.path.exists(record_path):
        raise HTTPException(status_code=404, detail="面试记录不存在")

    with open(record_path, "r", encoding="utf-8") as f:
        record = json.load(f)

    history = record.get("history", [])
    questions = record.get("questions", [])

    # 提取候选人回答
    answers = [h for h in history if h["role"] == "candidate"]
    answer_texts = [a["content"] for a in answers]

    # 加载 JD 文本提取关键词
    jd_text = ""
    jd_path = os.path.join(UPLOAD_DIR, "jd", record.get("jd_filename", ""))
    if os.path.exists(jd_path):
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read()

    # JD 技术关键词提取
    tech_kw = ["Python", "Java", "Go", "Rust", "C++", "TypeScript", "React", "Vue",
               "Node", "Django", "Flask", "Spring", "Docker", "Kubernetes", "AWS",
               "MySQL", "Redis", "Kafka", "AI", "机器学习", "深度学习", "NLP",
               "微服务", "分布式", "高并发", "性能优化", "数据分析", "架构"]
    jd_keywords = set()
    for kw in tech_kw:
        if kw.lower() in jd_text.lower():
            jd_keywords.add(kw)

    # 项目经验关键词
    project_kw = ["项目", "负责", "主导", "开发", "设计", "实现", "优化", "重构",
                  "架构", "上线", "团队", "管理", "推动", "解决", "成果", "%", "QPS"]

    all_answers = " ".join(answer_texts).lower()
    total_chars = sum(len(a) for a in answer_texts)
    avg_len = total_chars / max(len(answer_texts), 1)

    # ---- 维度 1: 沟通表达 ----
    comm_score = min(100, int(avg_len / 5 * 10)) if avg_len > 0 else 40
    comm_score = max(30, min(95, comm_score))
    if avg_len < 30:
        comm_comment = "回答较为简短，建议在面试中更充分地展开回答，提供具体案例支撑观点。"
    elif avg_len < 100:
        comm_comment = "表达清晰，回答长度适中。可以适当增加细节和实例来增强说服力。"
    else:
        comm_comment = "表达能力强，回答详细且有条理，能够清晰地传达观点和经历。"

    # ---- 维度 2: 技术匹配 ----
    if jd_keywords:
        matches = sum(1 for kw in jd_keywords if kw.lower() in all_answers)
        tech_score = int(matches / len(jd_keywords) * 100)
        tech_score = max(20, min(95, tech_score))
    else:
        tech_score = 60
    if tech_score < 40:
        tech_comment = "对岗位所需技术的回答覆盖不足，建议更深入了解 JD 中的核心技术要求。"
    elif tech_score < 70:
        tech_comment = "对部分核心技术有所涉及，但可以更深入地展示技术理解和实战经验。"
    else:
        tech_comment = "对岗位所需核心技术有较全面的了解和实践经验，匹配度较高。"

    # ---- 维度 3: 项目经验 ----
    proj_hits = sum(1 for kw in project_kw if kw.lower() in all_answers)
    proj_score = min(95, max(25, proj_hits * 7 + 30))
    if proj_hits < 3:
        proj_comment = "回答中缺少具体的项目案例，建议多用实际项目经历来展示能力。"
    elif proj_hits < 7:
        proj_comment = "有一定的项目经验体现，建议增加量化成果和技术细节的描述。"
    else:
        proj_comment = "项目经验丰富，能够结合具体案例说明问题，展示了实战能力。"

    # ---- 维度 4: 问题解决 ----
    solve_kw = ["问题", "解决", "方案", "分析", "思路", "方法", "挑战", "优化", "改进", "策略"]
    solve_hits = sum(1 for kw in solve_kw if kw.lower() in all_answers)
    solve_score = min(95, max(25, solve_hits * 8 + 25))
    if solve_hits < 2:
        solve_comment = "回答中较少体现解决问题的思路和方法，建议展示分析过程和决策依据。"
    elif solve_hits < 5:
        solve_comment = "展示了一定的问题解决能力，可以更系统地描述分析过程和解决方案。"
    else:
        solve_comment = "分析思路清晰，能够系统性地描述问题并给出有效的解决方案。"

    # ---- 维度 5: 岗位匹配 ----
    overall_score = int((comm_score + tech_score + proj_score + solve_score) / 4)
    fit_comment = "综合各方面的表现，" if overall_score >= 70 else "整体表现有提升空间，"
    if overall_score >= 85:
        fit_comment += "候选人非常匹配该岗位要求，建议进入下一轮。"
    elif overall_score >= 65:
        fit_comment += "候选人基本符合岗位要求，可在关键领域进一步考察。"
    else:
        fit_comment += "建议候选人在技术深度和项目经验方面加强准备。"

    # ---- 改进建议 ----
    suggestions = []
    if avg_len < 50:
        suggestions.append("建议在回答中展开更多细节，用 STAR 法则（情境-任务-行动-结果）组织答案。")
    if tech_score < 60:
        suggestions.append("建议针对 JD 中的核心技术要求进行针对性准备，补充相关项目经验。")
    if proj_score < 55:
        suggestions.append("建议准备 2-3 个代表性的项目案例，包含具体的量化成果和技术实现细节。")
    if solve_hits < 4:
        suggestions.append("建议在回答中展示完整的分析过程，从发现问题到提出方案到落地结果。")
    if not suggestions:
        suggestions.append("整体表现不错，可以在表达的精炼度和技术深度上持续提升。")

    # ---- 时长 ----
    duration = "未知"
    if record.get("created_at") and record.get("completed_at"):
        try:
            start = datetime.fromisoformat(record["created_at"])
            end = datetime.fromisoformat(record["completed_at"])
            minutes = int((end - start).total_seconds() / 60)
            duration = f"{minutes} 分钟"
        except (ValueError, TypeError):
            pass

    report = {
        "session_id": session_id,
        "duration": duration,
        "total_questions": len(questions),
        "answered_questions": len(answers),
        "overall_score": overall_score,
        "created_at": record.get("created_at", ""),
        "dimensions": [
            {"name": "沟通表达", "score": comm_score, "comment": comm_comment},
            {"name": "技术匹配", "score": tech_score, "comment": tech_comment},
            {"name": "项目经验", "score": proj_score, "comment": proj_comment},
            {"name": "问题解决", "score": solve_score, "comment": solve_comment},
            {"name": "岗位匹配", "score": overall_score, "comment": fit_comment},
        ],
        "qa_pairs": [
            {
                "question": questions[i] if i < len(questions) else "",
                "answer": answers[i]["content"] if i < len(answers) else "",
            }
            for i in range(max(len(questions), len(answers)))
        ],
        "suggestions": suggestions,
    }

    # 保存报告
    report_path = os.path.join(INTERVIEW_DIR, f"{session_id}_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[会话 {session_id}] 面试报告已生成")

    return report


# ---------- Models ----------

class JDContent(BaseModel):
    content: str


class ResumeParse(BaseModel):
    resume_filename: str


class PlanGenerate(BaseModel):
    jd_filename: str
    resume_filename: str


class ChatStart(BaseModel):
    jd_filename: str
    resume_filename: str


class ChatMessage(BaseModel):
    session_id: str
    message: str


# ---------- API ----------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/save/jd")
async def save_jd(body: JDContent):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="JD 内容不能为空")
    filename = f"{uuid.uuid4().hex}.txt"
    filepath = os.path.join(UPLOAD_DIR, "jd", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(body.content)
    return {"filename": filename, "status": "ok"}


@app.post("/api/upload/resume")
async def upload_resume(file: UploadFile = File(...)):
    ext = validate_file(file)
    filename = await save_file(file, "resume", ext)
    return {"filename": filename, "original_name": file.filename, "status": "ok"}


@app.post("/api/parse/resume")
async def parse_resume(body: ResumeParse):
    resume_path = os.path.join(UPLOAD_DIR, "resume", body.resume_filename)
    if not os.path.exists(resume_path):
        raise HTTPException(status_code=404, detail="简历文件不存在")
    resume_text = read_resume_file(body.resume_filename)
    print("=" * 60)
    print("【简历解析结果】")
    print(resume_text)
    print("=" * 60)
    return {"resume": resume_text}


@app.post("/api/generate/plan")
async def generate_plan(body: PlanGenerate):
    jd_path = os.path.join(UPLOAD_DIR, "jd", body.jd_filename)
    if not os.path.exists(jd_path):
        raise HTTPException(status_code=404, detail="JD 文件不存在")
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()

    resume_path = os.path.join(UPLOAD_DIR, "resume", body.resume_filename)
    if not os.path.exists(resume_path):
        raise HTTPException(status_code=404, detail="简历文件不存在")
    resume_text = read_resume_file(body.resume_filename)

    questions = extract_questions_from_jd(jd_text)
    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    plan = (
        "【面试岗位】\n根据 JD 描述分析，本面试针对的岗位要求如下：\n"
        "（请根据下方 JD 内容确认岗位核心需求）\n\n"
        "【候选人背景摘要】\n根据简历内容，候选人的背景如下：\n"
        "（请根据下方简历内容确认候选人核心经历）\n\n"
        "【建议面试问题】\n" + questions_text + "\n\n"
        + "=" * 60 + "\n【岗位 JD】\n" + jd_text + "\n"
        + "=" * 60 + "\n【个人简历】\n" + resume_text + "\n"
        + "=" * 60 + "\n"
    )

    print("=" * 60)
    print("【面试计划】")
    print(plan)
    print("=" * 60)

    return {"plan": plan}


# ---------- 面试聊天 ----------

@app.post("/api/chat/start")
async def chat_start(body: ChatStart):
    # 读取 JD 和简历
    jd_path = os.path.join(UPLOAD_DIR, "jd", body.jd_filename)
    if not os.path.exists(jd_path):
        raise HTTPException(status_code=404, detail="JD 文件不存在")
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()

    questions = extract_questions_from_jd(jd_text)

    session_id = uuid.uuid4().hex[:12]
    chat_sessions[session_id] = {
        "jd_filename": body.jd_filename,
        "resume_filename": body.resume_filename,
        "state": "READY_CHECK",
        "question_index": 0,
        "questions": questions,
        "history": [],
        "created_at": datetime.now().isoformat(),
    }

    opening = "你好！感谢你来参加今天的面试。我是今天的面试官，将根据岗位要求向你提几个问题。请问你准备好了吗？"
    chat_sessions[session_id]["history"].append({"role": "interviewer", "content": opening})

    print(f"[会话 {session_id}] 面试开始，共 {len(questions)} 个问题")
    print(f"面试官: {opening}")

    return {"session_id": session_id, "message": opening, "state": "READY_CHECK"}


@app.post("/api/chat/message")
async def chat_message(body: ChatMessage):
    session = chat_sessions.get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    user_msg = body.message.strip()
    session["history"].append({"role": "candidate", "content": user_msg})
    print(f"[会话 {body.session_id}] 候选人: {user_msg}")

    reply = ""

    if session["state"] == "READY_CHECK":
        if any(kw in user_msg for kw in ["准备", "好了", "可以", "开始", "好", "是", "嗯", "ok", "yes", "ready"]):
            session["state"] = "INTERVIEWING"
            q = session["questions"][0]
            reply = f"好的，那我们正式开始。\n\n第 1 题：{q}"
        else:
            reply = "没关系，不用紧张。准备好了就告诉我，我们随时可以开始。"

    elif session["state"] == "INTERVIEWING":
        session["question_index"] += 1
        idx = session["question_index"]
        if idx < len(session["questions"]):
            reply = f"好的，谢谢你的回答。\n\n第 {idx + 1} 题：{session['questions'][idx]}"
        else:
            session["state"] = "COMPLETED"
            reply = (
                "好的，所有问题都已经问完了。感谢你今天的参与和真诚的回答！\n\n"
                "我们会综合评估你的表现，如有后续安排会及时联系你。祝你好运！🍀"
            )

    elif session["state"] == "COMPLETED":
        reply = "面试已经结束了，感谢你的参与！如有任何问题，可以联系我们的 HR 团队。"

    session["history"].append({"role": "interviewer", "content": reply})
    print(f"[会话 {body.session_id}] 面试官: {reply}")

    # 面试结束时持久化记录 + 生成报告
    if session["state"] == "COMPLETED":
        save_interview_record(body.session_id)
        analyze_interview(body.session_id)

    return {"message": reply, "state": session["state"]}


@app.get("/api/report/{session_id}")
async def get_report(session_id: str):
    """获取面试报告"""
    report_path = os.path.join(INTERVIEW_DIR, f"{session_id}_report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 如果报告不存在，尝试生成
    return analyze_interview(session_id)


# 生产模式
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str = ""):  # noqa: ARG001
    return FileResponse("frontend/dist/index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
