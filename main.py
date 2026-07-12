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

    # 面试结束时持久化记录
    if session["state"] == "COMPLETED":
        save_interview_record(body.session_id)

    return {"message": reply, "state": session["state"]}


# 生产模式
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str = ""):  # noqa: ARG001
    return FileResponse("frontend/dist/index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
