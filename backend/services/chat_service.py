import json
import os
import re
import uuid
import asyncio
from datetime import datetime

import json_repair
from openai import AsyncOpenAI

from backend.config import chat_sessions
from backend.repositories.interview_repo import restore_session
from backend.services.file_service import read_jd, extract_questions_from_jd
from backend.repositories import plan_repo
from backend.repositories import resume_repo
from backend.services.llm_service import OPENAI_API_KEY, OPENAI_BASE_URL

MAX_QUESTION_ATTEMPTS = 3


def _now_iso() -> str:
    return datetime.now().isoformat()


def _history_message(role: str, content: str) -> dict:
    return {
        "role": role,
        "content": content,
        "timestamp": _now_iso(),
    }


async def start_session(jd_filename: str = "", resume_filename: str = "", plan_id: int | None = None) -> tuple[str, str, str, list[dict]]:
    plan = plan_repo.get_by_id(plan_id) if plan_id else None
    if plan and plan.get("active_session_id"):
        active_session_id = plan.get("active_session_id")
        restored = restore_session(active_session_id)
        if restored and restored.get("state") != "COMPLETED":
            history = restored.get("history", [])
            last_message = history[-1]["content"] if history else ""
            return active_session_id, last_message, restored.get("state", "READY_CHECK"), history

    if plan:
        questions, should_generate_async = _questions_for_plan_fast(plan)
        jd_filename = plan.get("jd_filename", "")
        resume_filename = plan.get("resume_filename", "")
        plan_repo.update(plan["id"], {"status": "running"})
    else:
        jd_text = read_jd(jd_filename)
        questions = [_normalize_question(q, index) for index, q in enumerate(extract_questions_from_jd(jd_text), start=1)]

    session_id = uuid.uuid4().hex[:12]
    chat_sessions[session_id] = {
        "jd_filename": jd_filename,
        "resume_filename": resume_filename,
        "plan_id": plan_id,
        "state": "READY_CHECK",
        "question_index": 0,
        "questions": questions,
        "question_attempts": {},
        "answer_evaluations": [],
        "resume_context": _load_resume_context(resume_filename),
        "jd_context": _load_jd_context(jd_filename, plan),
        "questions_ready": not should_generate_async,
        "history": [],
        "created_at": _now_iso(),
    }

    if plan:
        opening = (
            f"你好！欢迎参加「{plan.get('interview_round') or '本轮'}」面试。"
            f"本轮岗位是「{plan.get('jd_name') or '目标岗位'}」。"
            "我是今天的面试官，接下来会根据本轮安排向你提几个问题。请问你准备好了吗？"
        )
    else:
        opening = "你好！感谢你来参加今天的面试。我是今天的面试官，将根据岗位要求向你提几个问题。请问你准备好了吗？"
    chat_sessions[session_id]["history"].append(_history_message("interviewer", opening))

    print(f"[会话 {session_id}] 面试开始，共 {len(questions)} 个问题")
    print(f"面试官: {opening}")

    if plan:
        plan_repo.update(plan["id"], {"active_session_id": session_id})
        if should_generate_async:
            asyncio.create_task(_generate_questions_for_session(session_id, plan))

    return session_id, opening, "READY_CHECK", chat_sessions[session_id]["history"]


def _questions_for_plan_fast(plan: dict) -> tuple[list[dict], bool]:
    try:
        stored = json.loads(plan.get("questions") or "[]")
        if isinstance(stored, list) and stored:
            return [_normalize_question(q, index) for index, q in enumerate(stored, start=1) if _question_text(q)], False
    except Exception:
        pass
    return _fallback_questions_for_plan(plan), True


async def _generate_questions_for_session(session_id: str, plan: dict) -> None:
    generated = await _generate_smart_questions(plan)
    if not generated:
        session = chat_sessions.get(session_id)
        if session:
            session["questions_ready"] = True
        return

    questions_json = json.dumps(generated, ensure_ascii=False)
    plan_repo.update(plan["id"], {"questions": questions_json})
    session = chat_sessions.get(session_id)
    if not session or session.get("state") == "COMPLETED":
        return
    if int(session.get("question_index") or 0) == 0 and not session.get("question_attempts"):
        session["questions"] = generated
    session["questions_ready"] = True


async def _questions_for_plan(plan: dict) -> list[dict]:
    try:
        stored = json.loads(plan.get("questions") or "[]")
        if isinstance(stored, list) and stored:
            return [_normalize_question(q, index) for index, q in enumerate(stored, start=1) if _question_text(q)]
    except Exception:
        pass

    generated = await _generate_smart_questions(plan)
    if generated:
        questions_json = json.dumps(generated, ensure_ascii=False)
        plan_repo.update(plan["id"], {"questions": questions_json})
        return generated

    return _fallback_questions_for_plan(plan)


def _fallback_questions_for_plan(plan: dict) -> list[dict]:
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
    return [
        _normalize_question({
            "question": question,
            "expected_points": ["结合真实经历回答", "说明个人职责或行动", "补充结果或复盘"],
            "source": "fallback",
        }, index)
        for index, question in enumerate(base[:count], start=1)
    ]


async def _generate_smart_questions(plan: dict) -> list[dict]:
    jd_context = _load_jd_context(plan.get("jd_filename", ""), plan)
    resume_context = _load_resume_context(plan.get("resume_filename", ""))
    if not OPENAI_API_KEY or not (jd_context or resume_context):
        return []

    count = max(3, min(int(plan.get("question_count") or 6), 12))
    prompt = f"""你是一位资深技术面试官。请基于候选人的简历解析结果和岗位 JD，为当前面试轮次生成有针对性的结构化面试问题，并严格输出 JSON 数组。

每个问题对象格式：
{{
  "question": "面试官要问的问题",
  "expected_points": ["优秀回答应该覆盖的要点1", "要点2", "要点3"],
  "source": "resume|jd|resume_jd|behavior",
  "retry_prompt": "如果候选人回答过短、泛泛而谈或没有回答到点上，用于追问/重复的问题"
}}

要求：
1. 只输出 JSON 数组，不要解释
2. 共生成 {count} 个问题
3. 每个 question 只能包含一个明确问题，不要在同一句里连续问 2 个以上问题
4. 问题整体要覆盖：自我介绍/岗位动机、简历中的真实项目、JD 核心技能、问题解决、协作沟通、本轮结尾反问
5. 每题必须能通过候选人回答判断是否认真，expected_points 要具体
6. retry_prompt 也只能追问一个点，不要使用“1）2）3）”这种多问题格式

候选人：{plan.get('candidate_name') or '候选人'}
岗位：{plan.get('jd_name') or '目标岗位'}
面试轮次：{plan.get('interview_round') or '面试'}

简历解析结果：
{resume_context[:5000] or '暂无结构化简历'}

岗位 JD：
{jd_context[:3500] or plan.get('jd_name') or '暂无 JD'}
"""
    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
        response = await client.chat.completions.create(
            model="qwen-plus",
            temperature=0.35,
            messages=[
                {"role": "system", "content": "你是专业面试官，只输出可解析 JSON。"},
                {"role": "user", "content": prompt},
            ],
            extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
        )
        content = response.choices[0].message.content or "[]"
        data = _parse_json_array(content)
        return [_normalize_question(item, index) for index, item in enumerate(data[:count], start=1)]
    except Exception as exc:
        print(f"智能面试问题生成失败: {exc}")
        return []


def _normalize_question(item, index: int) -> dict:
    if isinstance(item, dict):
        question = str(item.get("question") or item.get("title") or item.get("content") or "").strip()
        expected_points = item.get("expected_points") or item.get("points") or []
        if isinstance(expected_points, str):
            expected_points = [line.strip() for line in re.split(r"[\n；;]", expected_points) if line.strip()]
        retry_prompt = str(item.get("retry_prompt") or "").strip()
        source = str(item.get("source") or "custom").strip()
    else:
        question = str(item or "").strip()
        expected_points = []
        retry_prompt = ""
        source = "legacy"

    return {
        "id": f"q{index}",
        "question": _clean_interviewer_text(question),
        "expected_points": [str(point).strip() for point in expected_points if str(point).strip()][:5],
        "source": source or "custom",
        "retry_prompt": _clean_interviewer_text(retry_prompt) or f"能不能结合一个具体经历，再展开说说你的实际做法？",
    }


def _question_text(item) -> str:
    if isinstance(item, dict):
        return str(item.get("question") or item.get("title") or item.get("content") or "").strip()
    return str(item or "").strip()


def _format_question(item, index: int) -> str:
    return _clean_interviewer_text(_question_text(item))


async def process_message(session_id: str, user_msg: str) -> tuple[str, str]:
    session = chat_sessions.get(session_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    session["history"].append(_history_message("candidate", user_msg))
    print(f"[会话 {session_id}] 候选人: {user_msg}")

    reply = ""

    if session["state"] == "READY_CHECK":
        if any(kw in user_msg for kw in ["准备", "好了", "可以", "开始", "好", "是", "嗯", "ok", "yes", "ready"]):
            session["state"] = "INTERVIEWING"
            q = session["questions"][0] if session.get("questions") else _normalize_question("请先做一个简短的自我介绍。", 1)
            reply = _compact_reply(f"好的，那我们正式开始。{_format_question(q, 0)}")
        else:
            reply = "没关系，不用紧张。准备好了就告诉我，我们随时可以开始。"

    elif session["state"] == "INTERVIEWING":
        reply = await _handle_interview_answer(session, user_msg)

    elif session["state"] == "COMPLETED":
        reply = "面试已经结束了，感谢你的参与！如有任何问题，可以联系我们的 HR 团队。"

    session["history"].append(_history_message("interviewer", reply))
    print(f"[会话 {session_id}] 面试官: {reply}")

    return reply, session["state"]


async def _handle_interview_answer(session: dict, user_msg: str) -> str:
    questions = session.get("questions") or []
    idx = int(session.get("question_index") or 0)
    if idx >= len(questions):
        return _complete_session(session)

    if not isinstance(questions[idx], dict):
        questions[idx] = _normalize_question(questions[idx], idx + 1)
    attempts = session.setdefault("question_attempts", {})
    current_attempt = int(attempts.get(str(idx), 0)) + 1
    attempts[str(idx)] = current_attempt
    question = questions[idx]
    evaluation = await _evaluate_answer(session, question, user_msg, current_attempt)
    session.setdefault("answer_evaluations", []).append({
        "question_index": idx,
        "question": _question_text(question),
        "answer": user_msg,
        "attempt": current_attempt,
        "evaluation": evaluation,
        "timestamp": _now_iso(),
    })

    if evaluation.get("need_retry") and current_attempt < MAX_QUESTION_ATTEMPTS:
        retry_prompt = evaluation.get("retry_question") or question.get("retry_prompt") or _question_text(question)
        return _clean_interviewer_text(retry_prompt) or "我想再追问一个点，能不能结合一个具体经历展开说说？"

    session["question_index"] = idx + 1
    next_idx = int(session["question_index"])
    if next_idx < len(questions):
        prefix = "好的，谢谢你的回答。"
        if evaluation.get("need_retry"):
            prefix = "好的，我们继续往下聊。"
        return _compact_reply(f"{prefix}{_format_question(questions[next_idx], next_idx)}")

    return _complete_session(session)


def _complete_session(session: dict) -> str:
    session["state"] = "COMPLETED"
    if session.get("plan_id"):
        plan_repo.mark_finished(session["plan_id"])
    return (
        "好的，所有问题都已经问完了。感谢你今天的参与和真诚的回答！"
        "我们会综合评估你的表现，如有后续安排会及时联系你。祝你好运！"
    )


async def _evaluate_answer(session: dict, question: dict, answer: str, attempt: int) -> dict:
    if OPENAI_API_KEY:
        try:
            return await _llm_evaluate_answer(session, question, answer, attempt)
        except Exception as exc:
            print(f"回答质量评估失败，使用兜底策略: {exc}")
    return _fallback_evaluate_answer(question, answer)


async def _llm_evaluate_answer(session: dict, question: dict, answer: str, attempt: int) -> dict:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
    prompt = f"""你是面试官助手，请判断候选人对当前问题是否认真回答，并严格输出 JSON。

输出格式：
{{
  "serious": true,
  "answered": true,
  "score": 0,
  "need_retry": false,
  "missing_points": ["缺失要点"],
  "retry_question": "需要追问时给候选人的自然追问，只能问一个问题",
  "summary": "一句话评估"
}}

判断规则：
1. 如果回答明显过短、敷衍、与问题无关、只说不知道/没有/嗯/好，need_retry=true
2. 如果没有覆盖 expected_points 中的关键要点，need_retry=true
3. 第 {MAX_QUESTION_ATTEMPTS} 次回答后即使不足也不再无限纠缠，但本次仍要真实评价 need_retry
4. retry_question 要自然具体，但一次只能追问一个点，不要给候选人展示缺失要点、评分依据或“可以重点补充”
5. retry_question 不要使用编号列表，不要包含“1）2）”“第一/第二/第三”等连续追问

岗位：{session.get('jd_name') or '目标岗位'}
面试轮次：{session.get('interview_round') or '面试'}
第 {int(session.get('question_index') or 0) + 1} 题：{_question_text(question)}
优秀回答要点：{json.dumps(question.get('expected_points') or [], ensure_ascii=False)}
候选人第 {attempt} 次回答：{answer}
"""
    response = await client.chat.completions.create(
        model="qwen-plus",
        temperature=0.15,
        messages=[
            {"role": "system", "content": "你是严格但友好的面试质量评估助手，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )
    data = _parse_json_object(response.choices[0].message.content or "{}")
    return _normalize_evaluation(data)


def _fallback_evaluate_answer(question: dict, answer: str) -> dict:
    text = str(answer or "").strip()
    compact = re.sub(r"\s+", "", text.lower())
    weak_tokens = ["不知道", "不会", "没有", "不清楚", "随便", "不了解", "没想过", "好", "嗯", "可以", "ok"]
    too_short = len(compact) < 12
    weak_only = compact in weak_tokens or any(compact == token.lower() for token in weak_tokens)
    expected = question.get("expected_points") or []
    hit_count = 0
    for point in expected:
        tokens = [token for token in re.split(r"[，,、；;\s]+", str(point)) if len(token) >= 2]
        if any(token.lower() in compact for token in tokens[:4]):
            hit_count += 1
    missing = [point for point in expected if point][:3]
    need_retry = weak_only or too_short or (expected and len(text) < 40 and hit_count == 0)
    return {
        "serious": not (weak_only or too_short),
        "answered": not weak_only,
        "score": 35 if need_retry else 70,
        "need_retry": need_retry,
        "missing_points": missing if need_retry else [],
        "retry_question": question.get("retry_prompt") or "能不能结合一个具体经历，再展开说说你的实际做法？",
        "summary": "回答偏短或要点不足，建议追问。" if need_retry else "回答基本有效，可以进入下一题。",
    }


def _normalize_evaluation(data: dict) -> dict:
    missing = data.get("missing_points") or []
    if isinstance(missing, str):
        missing = [line.strip() for line in re.split(r"[\n；;、]", missing) if line.strip()]
    try:
        score = int(float(data.get("score", 0)))
    except (TypeError, ValueError):
        score = 0
    serious = _as_bool(data.get("serious"))
    answered = _as_bool(data.get("answered"))
    need_retry = _as_bool(data.get("need_retry"))
    return {
        "serious": serious,
        "answered": answered,
        "score": max(0, min(score, 100)),
        "need_retry": need_retry,
        "missing_points": [str(item).strip() for item in missing if str(item).strip()][:4],
        "retry_question": _clean_interviewer_text(data.get("retry_question") or ""),
        "summary": str(data.get("summary") or "").strip(),
    }


def _clean_interviewer_text(text: str) -> str:
    source = str(text or "").strip()
    if not source:
        return ""

    source = re.sub(r"\n+\s*可以重点补充[:：].*", "", source, flags=re.S)
    source = re.sub(r"可以重点补充[:：].*", "", source, flags=re.S).strip()
    source = re.sub(r"^(第\s*\d+\s*题[:：]\s*)", "", source).strip()

    multi_markers = [
        r"\s*[（(]?\s*2\s*[）)、.．]\s*",
        r"\s*第二[，,、：:]\s*",
        r"\s*另外[，,、：:]\s*",
        r"\s*同时[，,、：:]\s*",
    ]
    for marker in multi_markers:
        parts = re.split(marker, source, maxsplit=1)
        if len(parts) > 1 and len(parts[0].strip()) >= 8:
            source = parts[0].strip()
            break

    numbered_first = re.search(r"[（(]?\s*1\s*[）)、.．]\s*", source)
    if numbered_first:
        prefix = source[:numbered_first.start()].strip()
        first = source[numbered_first.end():].strip()
        first = re.split(r"\s*[（(]?\s*2\s*[）)、.．]\s*", first, maxsplit=1)[0].strip()
        source = f"{prefix}{first}".strip()

    sentences = [item.strip() for item in re.split(r"(?<=[。！？?])", source) if item.strip()]
    question_sentences = [item for item in sentences if item.endswith(("？", "?"))]
    if len(question_sentences) > 1:
        first_question = question_sentences[0]
        lead = ""
        for item in sentences:
            if item == first_question:
                break
            if not item.endswith(("？", "?")):
                lead += item
        source = f"{lead}{first_question}".strip()

    return _compact_reply(source)


def _compact_reply(text: str) -> str:
    source = str(text or "").strip()
    source = re.sub(r"\s*\n+\s*", " ", source)
    source = re.sub(r"\s{2,}", " ", source)
    source = re.sub(r"([。！？?])(?=[\u4e00-\u9fa5A-Za-z0-9])", r"\1 ", source)
    return source.strip()


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"true", "1", "yes", "y", "是", "需要", "认真", "已回答"}


def _load_resume_context(resume_filename: str = "") -> str:
    if not resume_filename:
        return ""
    filename = os.path.basename(resume_filename)
    matched = None
    for resume in resume_repo.list_all():
        if filename in {resume.get("file_path"), resume.get("original_name"), os.path.basename(resume.get("file_path") or "")}:
            matched = resume
            break
    if not matched:
        return ""
    chunks = [
        f"姓名：{matched.get('name') or '未提取'}",
        f"意向岗位：{matched.get('target_position') or '未填写'}",
        f"学历：{matched.get('education') or '未填写'}",
        f"经验：{matched.get('experience_years') or '未填写'}",
        f"技能：{matched.get('skills') or '未提取'}",
    ]
    structured_raw = matched.get("structured_data") or "{}"
    try:
        structured = json.loads(structured_raw)
        chunks.append("结构化简历：")
        chunks.append(json.dumps(structured, ensure_ascii=False)[:4500])
    except Exception:
        if structured_raw and structured_raw != "{}":
            chunks.append(structured_raw[:3000])
    return "\n".join(chunks)


def _load_jd_context(jd_filename: str = "", plan: dict | None = None) -> str:
    pieces = []
    if plan:
        for key, label in [("jd_name", "岗位名称"), ("interview_round", "面试轮次")]:
            if plan.get(key):
                pieces.append(f"{label}：{plan.get(key)}")
    if jd_filename:
        try:
            pieces.append(read_jd(jd_filename))
        except Exception:
            pass
    return "\n".join(pieces).strip()


def _parse_json_array(content: str) -> list:
    source = str(content or "[]").strip()
    if source.startswith("```"):
        source = re.sub(r"^```(?:json)?\s*", "", source)
        source = re.sub(r"\s*```$", "", source).strip()
    try:
        data = json_repair.loads(source)
    except Exception:
        match = re.search(r"\[.*\]", source, re.S)
        data = json_repair.loads(match.group(0)) if match else []
    return data if isinstance(data, list) else []


def _parse_json_object(content: str) -> dict:
    source = str(content or "{}").strip()
    if source.startswith("```"):
        source = re.sub(r"^```(?:json)?\s*", "", source)
        source = re.sub(r"\s*```$", "", source).strip()
    try:
        data = json_repair.loads(source)
    except Exception:
        match = re.search(r"\{.*\}", source, re.S)
        data = json_repair.loads(match.group(0)) if match else {}
    return data if isinstance(data, dict) else {}
