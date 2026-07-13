import os
from datetime import datetime

from backend.config import UPLOAD_DIR
from backend.repositories.interview_repo import load_record, save_report


def generate_report(session_id: str) -> dict:
    record = load_record(session_id)
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
