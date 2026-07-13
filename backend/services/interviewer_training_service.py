import json
import uuid
from datetime import datetime

from openai import OpenAI

from backend.config import chat_sessions, UPLOAD_DIR
from backend.repositories import jd_repo, resume_repo
from backend.repositories.interview_repo import restore_session
from backend.services.llm_service import OPENAI_API_KEY, OPENAI_BASE_URL
from backend.services.file_service import read_jd


def start_training_session(jd_id: int, resume_id: int, training_mode: str, candidate_style: str) -> dict:
    jd = jd_repo.get_by_id(jd_id)
    resume = resume_repo.get_by_id(resume_id)
    if not jd or not resume:
        raise ValueError("JD 或简历不存在")

    session_id = uuid.uuid4().hex[:12]
    candidate_name = resume.get("name") or "候选人"
    jd_name = jd.get("name") or "目标岗位"
    jd_text = _load_jd_text(jd)
    resume_summary = _resume_summary(resume)
    opening = (
        f"您好，我是候选人 {candidate_name}。我准备好了，可以开始「{jd_name}」岗位的{training_mode}。"
        f"当前回答风格为「{candidate_style}」，您可以直接开始提问。"
    )

    chat_sessions[session_id] = {
        "mode": "interviewer_training",
        "state": "INTERVIEWING",
        "jd_id": jd_id,
        "resume_id": resume_id,
        "jd_name": jd_name,
        "resume_name": candidate_name,
        "jd_filename": "",
        "resume_filename": resume.get("file_path", ""),
        "questions": [],
        "question_index": 0,
        "training_mode": training_mode,
        "candidate_style": candidate_style,
        "candidate_name": candidate_name,
        "history": [{
            "role": "candidate",
            "content": opening,
            "timestamp": datetime.now().isoformat(),
        }],
        "created_at": datetime.now().isoformat(),
        "persona": {
            "jd_text": jd_text,
            "resume_summary": resume_summary,
            "structured_data": resume.get("structured_data", "{}"),
        },
    }
    return {
        "session_id": session_id,
        "state": "INTERVIEWING",
        "history": chat_sessions[session_id]["history"],
        "candidate_name": candidate_name,
        "jd_name": jd_name,
        "training_mode": training_mode,
        "candidate_style": candidate_style,
        "resume_summary": resume_summary,
    }


def get_training_session(session_id: str) -> dict | None:
    session = chat_sessions.get(session_id) or restore_session(session_id)
    if not session or session.get("mode") != "interviewer_training":
        return None
    return {
        "session_id": session_id,
        "state": session.get("state", "INTERVIEWING"),
        "history": session.get("history", []),
        "candidate_name": session.get("candidate_name") or session.get("resume_name") or "候选人",
        "jd_name": session.get("jd_name", "目标岗位"),
        "training_mode": session.get("training_mode", "结构化面试"),
        "candidate_style": session.get("candidate_style", "标准型"),
        "resume_summary": session.get("persona", {}).get("resume_summary", ""),
    }


def process_training_message(session_id: str, interviewer_question: str) -> tuple[str, str]:
    session = chat_sessions.get(session_id)
    if not session or session.get("mode") != "interviewer_training":
        raise ValueError("训练会话不存在")

    session["history"].append({
        "role": "interviewer",
        "content": interviewer_question,
        "timestamp": datetime.now().isoformat(),
    })

    answer = _generate_candidate_reply(session, interviewer_question)
    session["history"].append({
        "role": "candidate",
        "content": answer,
        "timestamp": datetime.now().isoformat(),
    })
    return answer, session.get("state", "INTERVIEWING")


def finish_training_session(session_id: str) -> dict | None:
    session = chat_sessions.get(session_id) or restore_session(session_id)
    if not session or session.get("mode") != "interviewer_training":
        return None
    if session.get("state") != "COMPLETED":
        session["state"] = "COMPLETED"
        session["history"].append({
            "role": "system",
            "content": "本次面试官训练已结束，系统正在生成训练报告。",
            "timestamp": datetime.now().isoformat(),
        })
    return session


def _resume_summary(resume: dict) -> str:
    chunks = [
        f"候选人：{resume.get('name', '未知')}",
        f"意向岗位：{resume.get('target_position') or '未填写'}",
        f"教育背景：{resume.get('education') or '未填写'}",
        f"经验年限：{resume.get('experience_years') or '未填写'}",
        f"技能关键词：{resume.get('skills') or '未提取'}",
    ]
    structured_raw = resume.get("structured_data") or "{}"
    try:
        structured = json.loads(structured_raw)
        project_list = structured.get("项目经历", [])
        if project_list:
            first_project = project_list[0]
            chunks.append(f"代表项目：{first_project.get('项目名称') or '未命名项目'}")
    except Exception:
        pass
    return "\n".join(chunks)


def _load_jd_text(jd: dict) -> str:
    jd_filename = jd.get("file_path") or ""
    if jd_filename:
        try:
            return read_jd(jd_filename)
        except Exception:
            pass
    pieces = [
        jd.get("name", ""),
        jd.get("responsibilities", ""),
        jd.get("requirements", ""),
    ]
    return "\n".join([piece for piece in pieces if piece]).strip()


def _generate_candidate_reply(session: dict, interviewer_question: str) -> str:
    if OPENAI_API_KEY:
        try:
            return _llm_candidate_reply(session, interviewer_question)
        except Exception:
            pass
    return _fallback_candidate_reply(session, interviewer_question)


def _llm_candidate_reply(session: dict, interviewer_question: str) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
    persona = session.get("persona", {})
    history = session.get("history", [])[-8:]
    history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history)
    prompt = f"""你正在扮演一位候选人，参与面试官训练。

候选人姓名：{session.get('candidate_name', '候选人')}
岗位名称：{session.get('jd_name', '目标岗位')}
训练模式：{session.get('training_mode', '结构化面试')}
候选人风格：{session.get('candidate_style', '标准型')}

候选人简历摘要：
{persona.get('resume_summary', '')}

岗位 JD 摘要：
{persona.get('jd_text', '')[:2000]}

最近对话：
{history_text}

要求：
1. 你只能以候选人的身份回答，不要代替面试官。
2. 回答应与简历背景一致，允许适度口语化。
3. 回答长度控制在 80-180 字，必要时给出项目案例。
4. 候选人风格会影响表达：
   - 标准型：正常、完整、稳妥
   - 紧张型：略有犹豫，但仍努力回答
   - 强表达型：表达欲强，回答更主动
   - 模糊回答型：会泛泛而谈，需要面试官继续追问
   - 经验包装型：会适度包装经历，但不要离谱

面试官提问：
{interviewer_question}
"""
    response = client.chat.completions.create(
        model="qwen-plus",
        temperature=0.7,
        messages=[
            {"role": "system", "content": "你是一位真实候选人，正在参加面试官训练。"},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )
    return (response.choices[0].message.content or "").strip()


def _fallback_candidate_reply(session: dict, interviewer_question: str) -> str:
    style = session.get("candidate_style", "标准型")
    summary = session.get("persona", {}).get("resume_summary", "")
    lower_q = interviewer_question.lower()

    if "自我介绍" in interviewer_question:
        base = f"您好，我是{session.get('candidate_name', '候选人')}。{summary.replace(chr(10), '，')}。"
    elif any(kw in lower_q for kw in ["项目", "project", "经历"]):
        base = f"我之前做过和「{session.get('jd_name', '目标岗位')}」比较相关的项目，主要负责方案设计、开发落地和效果优化。推进过程中我更关注业务目标、实现细节以及最终结果。"
    elif any(kw in interviewer_question for kw in ["为什么", "动机", "兴趣"]):
        base = f"我对这个岗位感兴趣，主要是因为它和我过去积累的能力比较匹配，而且我希望继续在{session.get('jd_name', '这个方向')}上做得更深入。"
    elif any(kw in interviewer_question for kw in ["优点", "优势"]):
        base = "我觉得自己的优势在于理解需求比较快，执行比较稳，也愿意把复杂问题拆开一步步推进。"
    elif any(kw in interviewer_question for kw in ["缺点", "不足"]):
        base = "如果说不足的话，我有时会在前期把细节想得比较多，现在会更注意在推进速度和方案完整性之间做平衡。"
    else:
        base = f"这个问题我会结合过往经历来回答。就我的理解，关键还是要先看岗位目标，再结合具体项目经验去说明自己为什么能胜任。"

    if style == "紧张型":
        return f"嗯，这个问题我想一下。{base}如果您需要的话，我也可以再补充一个更具体的例子。"
    if style == "强表达型":
        return f"{base}另外我通常会主动补充背景、决策思路和最终结果，因为我觉得这些更能说明一个人的实际能力。"
    if style == "模糊回答型":
        return f"{base}整体上差不多就是这样。"
    if style == "经验包装型":
        return f"{base}从结果上看，我在相关方向的实践还是比较完整的，也有过比较不错的落地成果。"
    return base
