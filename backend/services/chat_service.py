import uuid
from datetime import datetime

from backend.config import chat_sessions
from backend.services.file_service import read_jd, extract_questions_from_jd


def start_session(jd_filename: str, resume_filename: str) -> tuple[str, str, str]:
    jd_text = read_jd(jd_filename)
    questions = extract_questions_from_jd(jd_text)

    session_id = uuid.uuid4().hex[:12]
    chat_sessions[session_id] = {
        "jd_filename": jd_filename,
        "resume_filename": resume_filename,
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

    return session_id, opening, "READY_CHECK"


def process_message(session_id: str, user_msg: str) -> tuple[str, str]:
    session = chat_sessions.get(session_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    session["history"].append({"role": "candidate", "content": user_msg})
    print(f"[会话 {session_id}] 候选人: {user_msg}")

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
    print(f"[会话 {session_id}] 面试官: {reply}")

    return reply, session["state"]
