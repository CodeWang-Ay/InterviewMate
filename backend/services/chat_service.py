import uuid
from datetime import datetime

from backend.config import chat_sessions
from backend.services.file_service import read_jd, extract_questions_from_jd
from backend.repositories import plan_repo


def start_session(jd_filename: str = "", resume_filename: str = "", plan_id: int | None = None) -> tuple[str, str, str]:
    plan = plan_repo.get_by_id(plan_id) if plan_id else None
    if plan:
        questions = _questions_for_plan(plan)
        jd_filename = plan.get("jd_filename", "")
        resume_filename = plan.get("resume_filename", "")
        plan_repo.update(plan["id"], {"status": "running"})
    else:
        jd_text = read_jd(jd_filename)
        questions = extract_questions_from_jd(jd_text)

    session_id = uuid.uuid4().hex[:12]
    chat_sessions[session_id] = {
        "jd_filename": jd_filename,
        "resume_filename": resume_filename,
        "plan_id": plan_id,
        "state": "READY_CHECK",
        "question_index": 0,
        "questions": questions,
        "history": [],
        "created_at": datetime.now().isoformat(),
    }

    if plan:
        opening = (
            f"你好！欢迎参加「{plan.get('interview_round') or '本轮'}」面试。"
            f"本轮岗位是「{plan.get('jd_name') or '目标岗位'}」。"
            "我是今天的面试官，接下来会根据本轮安排向你提几个问题。请问你准备好了吗？"
        )
    else:
        opening = "你好！感谢你来参加今天的面试。我是今天的面试官，将根据岗位要求向你提几个问题。请问你准备好了吗？"
    chat_sessions[session_id]["history"].append({"role": "interviewer", "content": opening})

    print(f"[会话 {session_id}] 面试开始，共 {len(questions)} 个问题")
    print(f"面试官: {opening}")

    return session_id, opening, "READY_CHECK"


def _questions_for_plan(plan: dict) -> list[str]:
    import json

    try:
        stored = json.loads(plan.get("questions") or "[]")
        if isinstance(stored, list) and stored:
            return [str(q) for q in stored if str(q).strip()]
    except Exception:
        pass

    round_name = plan.get("interview_round") or "面试"
    jd_name = plan.get("jd_name") or "目标岗位"
    count = max(3, min(int(plan.get("question_count") or 6), 12))
    base = [
        f"请先做一个简短的自我介绍，并重点说明你和「{jd_name}」岗位相关的经历。",
        f"你为什么对「{jd_name}」这个方向感兴趣？",
        f"请结合过往项目，讲一个你在「{round_name}」相关能力上最有代表性的案例。",
        "遇到复杂问题时，你通常如何拆解和推进？",
        "请讲一次你和团队协作中遇到分歧并解决的经历。",
        f"如果加入这个岗位，你觉得前 30 天最应该优先了解和完成什么？",
        "你目前最希望提升的一项能力是什么？为什么？",
        "你有什么想反问面试官的问题？",
    ]
    return base[:count]


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
            if session.get("plan_id"):
                plan_repo.update(session["plan_id"], {"status": "finish"})
            reply = (
                "好的，所有问题都已经问完了。感谢你今天的参与和真诚的回答！\n\n"
                "我们会综合评估你的表现，如有后续安排会及时联系你。祝你好运！🍀"
            )

    elif session["state"] == "COMPLETED":
        reply = "面试已经结束了，感谢你的参与！如有任何问题，可以联系我们的 HR 团队。"

    session["history"].append({"role": "interviewer", "content": reply})
    print(f"[会话 {session_id}] 面试官: {reply}")

    return reply, session["state"]
