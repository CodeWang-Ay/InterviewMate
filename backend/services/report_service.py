import os
from datetime import datetime

from backend.config import UPLOAD_DIR
from backend.repositories.interview_repo import load_record, save_report


def generate_report(session_id: str) -> dict:
    record = load_record(session_id)
    if record.get("mode") == "interviewer_training":
        report = _generate_interviewer_training_report(session_id, record)
        save_report(session_id, report)
        return report

    history = record.get("history", [])
    questions = record.get("questions", [])

    answers = [h for h in history if h["role"] == "candidate"]
    answer_texts = [a["content"] for a in answers]

    # 加载 JD 文本
    jd_text = ""
    jd_path = os.path.join(UPLOAD_DIR, "jd", record.get("jd_filename", ""))
    if os.path.isfile(jd_path):
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read()

    # JD 技术关键词
    tech_kw = ["Python", "Java", "Go", "Rust", "C++", "TypeScript", "React", "Vue",
               "Node", "Django", "Flask", "Spring", "Docker", "Kubernetes", "AWS",
               "MySQL", "Redis", "Kafka", "AI", "机器学习", "深度学习", "NLP",
               "微服务", "分布式", "高并发", "性能优化", "数据分析", "架构"]
    jd_keywords = {kw for kw in tech_kw if kw.lower() in jd_text.lower()}

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
        tech_score = max(20, min(95, int(matches / len(jd_keywords) * 100)))
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
            duration = f"{int((end - start).total_seconds() / 60)} 分钟"
        except (ValueError, TypeError):
            pass

    report = {
        "session_id": session_id,
        "candidate_name": record.get("candidate_name") or record.get("resume_name") or "",
        "jd_name": record.get("jd_name") or "",
        "interview_round": record.get("interview_round") or "",
        "workflow_name": record.get("workflow_name") or "",
        "workflow_id": record.get("workflow_id") or "",
        "candidate_username": record.get("candidate_username") or "",
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
        "history": history,
        "suggestions": suggestions,
    }

    save_report(session_id, report)
    return report


def _generate_interviewer_training_report(session_id: str, record: dict) -> dict:
    history = record.get("history", [])
    interviewer_msgs = [item for item in history if item.get("role") == "interviewer"]
    candidate_msgs = [item for item in history if item.get("role") == "candidate"]
    jd_text = (record.get("persona", {}) or {}).get("jd_text", "")
    training_mode = record.get("training_mode", "结构化面试")
    candidate_name = record.get("candidate_name") or record.get("resume_name") or "候选人"
    jd_name = record.get("jd_name", "目标岗位")

    interviewer_texts = [item.get("content", "") for item in interviewer_msgs]
    joined = " ".join(interviewer_texts).lower()
    avg_len = sum(len(text) for text in interviewer_texts) / max(len(interviewer_texts), 1)

    jd_keywords = []
    for token in ["项目", "架构", "性能", "协作", "业务", "优化", "系统", "AI", "大模型", "Python", "Java", "Vue", "React", "SQL"]:
        if token.lower() in jd_text.lower():
            jd_keywords.append(token)
    if not jd_keywords:
        jd_keywords = ["项目", "技术", "业务", "协作"]

    matched_keywords = sum(1 for token in jd_keywords if token.lower() in joined)
    keyword_coverage = matched_keywords / max(len(jd_keywords), 1)
    coverage_score = max(35, min(95, int(keyword_coverage * 100)))
    if coverage_score >= 80:
        coverage_comment = "提问已经覆盖了岗位中的关键能力点，训练聚焦度比较高。"
    elif coverage_score >= 60:
        coverage_comment = "已经触及部分核心要求，但还可以更有意识地围绕 JD 关键词展开。"
    else:
        coverage_comment = "提问与岗位要求的绑定还不够紧，建议先提炼 JD 里的关键考察项再发问。"

    followup_hits = sum(
        1 for text in interviewer_texts
        if any(keyword in text for keyword in ["为什么", "具体", "展开", "细说", "举例", "怎么做", "怎么解决", "如果再来一次"])
    )
    followup_ratio = followup_hits / max(len(interviewer_texts), 1)
    depth_score = max(30, min(95, int(45 + followup_ratio * 45)))
    if depth_score >= 80:
        depth_comment = "追问意识比较强，能够把候选人的回答继续往细节和证据上推进。"
    elif depth_score >= 60:
        depth_comment = "有一定追问动作，但还可以更稳定地把泛回答拉回到真实案例。"
    else:
        depth_comment = "当前更像是顺序发问，追问深度偏弱，建议多追到动作、决策和结果层。"

    scenario_hits = sum(
        1 for text in interviewer_texts
        if any(keyword in text for keyword in ["项目", "案例", "冲突", "挑战", "结果", "指标", "数据", "上线", "复盘"])
    )
    scenario_score = max(30, min(95, int(35 + scenario_hits * 8)))
    if scenario_score >= 80:
        scenario_comment = "你比较关注真实场景和量化结果，这很像成熟面试官的发问方式。"
    elif scenario_score >= 60:
        scenario_comment = "已经开始引导候选人讲案例，下一步可以继续追问背景、行动和结果。"
    else:
        scenario_comment = "场景化提问偏少，建议多让候选人用项目、冲突、指标和结果来证明自己。"

    rhythm_base = min(len(interviewer_msgs), len(candidate_msgs))
    rhythm_score = max(40, min(95, int(50 + min(rhythm_base, 8) * 5 + min(avg_len, 80) / 10)))
    if rhythm_score >= 80:
        rhythm_comment = "整体节奏自然，既没有太散，也没有过早切题结束。"
    elif rhythm_score >= 60:
        rhythm_comment = "节奏基本稳定，但可以在开场、主问题、追问、收束这几个段落上再更清晰。"
    else:
        rhythm_comment = "对话节奏略显生硬，建议先搭框架，再逐步推进到重点考察项。"

    openness_hits = sum(
        1 for text in interviewer_texts
        if any(keyword in text for keyword in ["请介绍", "请分享", "能不能", "你是怎么", "当时", "后来"])
    )
    precision_hits = sum(
        1 for text in interviewer_texts
        if any(keyword in text for keyword in ["具体", "数据", "指标", "多久", "多少", "谁来", "负责哪部分"])
    )
    structure_score = max(35, min(95, int(40 + openness_hits * 5 + precision_hits * 5)))
    if structure_score >= 80:
        structure_comment = "提问既开放又有收口，比较像一场有结构的正式面谈。"
    elif structure_score >= 60:
        structure_comment = "问题结构基本成型，但还可以更明确地区分开场题、能力题和压力追问题。"
    else:
        structure_comment = "问题结构还比较散，建议先按考察维度列一个提问路径再进入训练。"

    overall_score = int((coverage_score + depth_score + scenario_score + rhythm_score + structure_score) / 5)

    suggestions = []
    if coverage_score < 75:
        suggestions.append("先从 JD 中摘出 4 到 6 个核心能力点，把每个能力点对应到至少 1 个问题。")
    if depth_score < 75:
        suggestions.append("对每个关键回答至少补 1 个追问，优先追“为什么这么做”和“结果怎么证明”。")
    if scenario_score < 75:
        suggestions.append("多让候选人讲真实项目，尽量追到背景、任务、行动、结果四个层次。")
    if structure_score < 75:
        suggestions.append("把整场训练拆成开场暖场、核心能力、项目深挖、收尾反问四段，会更稳。")
    if not suggestions:
        suggestions.append("这轮训练已经比较成熟了，下一步可以尝试更高压或更模糊回答型候选人。")

    duration = "未知"
    if record.get("created_at") and record.get("completed_at"):
        try:
            start = datetime.fromisoformat(record["created_at"])
            end = datetime.fromisoformat(record["completed_at"])
            duration = f"{max(1, int((end - start).total_seconds() / 60))} 分钟"
        except (ValueError, TypeError):
            pass

    return {
        "session_id": session_id,
        "report_type": "interviewer_training",
        "report_title": "面试官训练复盘",
        "candidate_name": candidate_name,
        "jd_name": jd_name,
        "training_mode": training_mode,
        "duration": duration,
        "total_questions": len(interviewer_msgs),
        "answered_questions": len(candidate_msgs),
        "overall_score": overall_score,
        "created_at": record.get("created_at", ""),
        "dimensions": [
            {"name": "岗位覆盖", "score": coverage_score, "comment": coverage_comment},
            {"name": "追问深度", "score": depth_score, "comment": depth_comment},
            {"name": "案例挖掘", "score": scenario_score, "comment": scenario_comment},
            {"name": "面试节奏", "score": rhythm_score, "comment": rhythm_comment},
            {"name": "提问结构", "score": structure_score, "comment": structure_comment},
        ],
        "history": history,
        "suggestions": suggestions,
    }
