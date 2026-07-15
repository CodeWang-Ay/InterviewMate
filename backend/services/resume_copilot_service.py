import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.repositories import jd_repo, resume_repo
from backend.repositories.upload_repo import read_text

load_dotenv(".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")


async def score_resume(resume_id: int, jd_id: int | None = None) -> dict:
    resume = resume_repo.get_by_id(resume_id)
    if not resume:
        raise ValueError("简历不存在")

    jd = _resolve_jd(resume, jd_id)
    resume_text = _resume_text(resume)
    structured = _structured_resume(resume)

    if OPENAI_API_KEY:
        try:
            return await _llm_score_resume(resume, jd, resume_text, structured)
        except Exception:
            pass
    return _fallback_score_resume(resume, jd, resume_text, structured)


async def polish_resume(resume_id: int, jd_id: int | None = None, mode: str = "jd") -> dict:
    resume = resume_repo.get_by_id(resume_id)
    if not resume:
        raise ValueError("简历不存在")

    jd = _resolve_jd(resume, jd_id)
    resume_text = _resume_text(resume)
    structured = _structured_resume(resume)

    if OPENAI_API_KEY:
        try:
            return await _llm_polish_resume(resume, jd, resume_text, structured, mode)
        except Exception:
            pass
    return _fallback_polish_resume(resume, jd, structured, mode)


async def score_resume_text(
    filename: str,
    resume_text: str,
    structured: dict,
    jd_id: int | None = None,
) -> dict:
    jd = jd_repo.get_by_id(int(jd_id)) if jd_id else None
    resume = {
        "name": os.path.splitext(filename or "候选人简历")[0],
        "target_position": (structured.get("基础信息") or {}).get("意向岗位", ""),
        "education": "",
        "skills": "",
        "jd_name": jd.get("name") if jd else "",
    }
    if OPENAI_API_KEY:
        try:
            return await _llm_score_resume(resume, jd, resume_text, structured)
        except Exception:
            pass
    return _fallback_score_resume(resume, jd, resume_text, structured)


async def polish_resume_text(
    filename: str,
    resume_text: str,
    structured: dict,
    jd_id: int | None = None,
    mode: str = "jd",
) -> dict:
    jd = jd_repo.get_by_id(int(jd_id)) if jd_id else None
    resume = {
        "name": os.path.splitext(filename or "候选人简历")[0],
        "target_position": (structured.get("基础信息") or {}).get("意向岗位", ""),
        "education": "",
        "skills": "",
        "jd_name": jd.get("name") if jd else "",
    }
    if OPENAI_API_KEY:
        try:
            return await _llm_polish_resume(resume, jd, resume_text, structured, mode)
        except Exception:
            pass
    return _fallback_polish_resume(resume, jd, structured, mode)


def _resolve_jd(resume: dict, jd_id: int | None) -> dict | None:
    target_id = jd_id if jd_id is not None else resume.get("jd_id")
    if target_id:
        return jd_repo.get_by_id(int(target_id))
    return None


def _resume_text(resume: dict) -> str:
    if resume.get("file_path"):
        try:
            return read_text("resume", resume["file_path"])
        except Exception:
            pass
    return _resume_summary(resume, _structured_resume(resume))


def _structured_resume(resume: dict) -> dict:
    try:
        return json.loads(resume.get("structured_data") or "{}")
    except Exception:
        return {}


def _resume_summary(resume: dict, structured: dict) -> str:
    base = structured.get("基础信息", {})
    education = structured.get("教育经历", [])
    work = structured.get("工作经历", [])
    projects = structured.get("项目经历", [])
    lines = [
        f"姓名：{base.get('姓名') or resume.get('name') or '未知'}",
        f"意向岗位：{base.get('意向岗位') or resume.get('target_position') or '未填写'}",
        f"学历：{resume.get('education') or '未填写'}",
        f"技能：{resume.get('skills') or '未填写'}",
        f"自我评价：{structured.get('自我评价') or '未填写'}",
    ]
    if education:
        lines.append("教育经历：" + "；".join(
            f"{item.get('学校', '')} {item.get('专业', '')} {item.get('学位', '')}".strip()
            for item in education[:2]
        ))
    if work:
        lines.append("工作经历：" + "；".join(
            f"{item.get('公司名称', '')} {item.get('职位', '')} {item.get('工作描述', '')[:80]}".strip()
            for item in work[:2]
        ))
    if projects:
        lines.append("项目经历：" + "；".join(
            f"{item.get('项目名称', '')} {item.get('项目描述', '')[:100]}".strip()
            for item in projects[:2]
        ))
    return "\n".join(lines)


def _jd_text(jd: dict | None) -> str:
    if not jd:
        return "暂无绑定 JD，请按通用简历标准进行评估和润色。"
    return "\n".join([
        f"岗位名称：{jd.get('name', '')}",
        f"岗位类别：{jd.get('category', '')}",
        f"工作地点：{jd.get('location', '')}",
        f"岗位职责：{jd.get('responsibilities', '')}",
        f"任职要求：{jd.get('requirements', '')}",
    ])


async def _llm_score_resume(resume: dict, jd: dict | None, resume_text: str, structured: dict) -> dict:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
    prompt = f"""你是一位招聘顾问，请对下面的简历做结构化评估，并严格输出 JSON。

输出格式：
{{
  "summary": "",
  "total_score": 0,
  "dimensions": [
    {{"name": "岗位匹配度", "score": 0, "comment": ""}},
    {{"name": "技能覆盖度", "score": 0, "comment": ""}},
    {{"name": "项目说服力", "score": 0, "comment": ""}},
    {{"name": "经历完整度", "score": 0, "comment": ""}},
    {{"name": "表达专业度", "score": 0, "comment": ""}}
  ],
  "strengths": ["", "", ""],
  "risks": ["", "", ""],
  "suggestions": ["", "", ""]
}}

要求：
1. 分数范围 0-100
2. comment 要具体，不要空泛
3. suggestions 要可执行
4. 如果没有 JD，就按通用专业简历标准评估

JD：
{_jd_text(jd)}

简历结构化信息：
{json.dumps(structured, ensure_ascii=False)}

简历原文：
{resume_text[:8000]}
"""
    response = await client.chat.completions.create(
        model="qwen-plus",
        temperature=0.3,
        messages=[
            {"role": "system", "content": "你是一位专业招聘顾问，输出必须是 JSON。"},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    data["matched_jd_name"] = jd.get("name") if jd else (resume.get("jd_name") or "通用标准")
    return data


def _fallback_score_resume(resume: dict, jd: dict | None, resume_text: str, structured: dict) -> dict:
    skills_text = (resume.get("skills") or "").lower()
    jd_text = _jd_text(jd).lower()
    skill_hits = sum(1 for token in ["python", "java", "vue", "react", "mysql", "redis", "docker", "llm", "nlp"] if token in skills_text and token in jd_text)
    project_count = len(structured.get("项目经历", []) or [])
    work_count = len(structured.get("工作经历", []) or [])
    base_score = 55
    total_score = min(92, base_score + skill_hits * 5 + project_count * 4 + work_count * 3)
    dimensions = [
        {"name": "岗位匹配度", "score": min(95, 58 + skill_hits * 7), "comment": "简历与岗位方向存在一定对应关系，建议继续强化和 JD 直接相关的经历表述。"},
        {"name": "技能覆盖度", "score": min(95, 55 + skill_hits * 8), "comment": "技能标签基础具备，但可以把核心工具和技术栈拆得更清晰。"},
        {"name": "项目说服力", "score": min(95, 50 + project_count * 10), "comment": "项目经历数量尚可，建议把结果、指标和个人贡献写得更具体。"},
        {"name": "经历完整度", "score": min(95, 52 + work_count * 10), "comment": "教育、工作、项目主线基本完整，但仍建议补齐时间线和职责边界。"},
        {"name": "表达专业度", "score": min(95, 56 + (1 if len(resume_text) > 600 else 0) * 10), "comment": "表述具备基础专业度，不过可以再压缩口语化描述，提升招聘阅读效率。"},
    ]
    return {
        "summary": f"这份简历整体处于可进入初筛或一面准备的水平，当前更需要补强的是和「{jd.get('name') if jd else resume.get('target_position') or '目标岗位'}」直接相关的案例表达。",
        "total_score": total_score,
        "matched_jd_name": jd.get("name") if jd else (resume.get("jd_name") or "通用标准"),
        "dimensions": dimensions,
        "strengths": [
            "基础信息和岗位方向已经形成基本对应。",
            "已有项目或工作经历可作为后续深挖素材。",
            "技能栏具备可继续展开的技术关键词。",
        ],
        "risks": [
            "项目描述中量化结果不够明确。",
            "和目标岗位最强关联的经历没有被放大。",
            "表达颗粒度略粗，招聘方需要自己二次提炼。",
        ],
        "suggestions": [
            "把最相关的 1-2 个项目放到前面，并补齐个人职责、难点和结果。",
            "针对 JD 里的关键词重写技能栏和项目标题，让匹配关系更直观。",
            "尽量加入量化结果，例如效率提升、成本下降、准确率提升等指标。",
        ],
    }


async def _llm_polish_resume(resume: dict, jd: dict | None, resume_text: str, structured: dict, mode: str) -> dict:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
    prompt = f"""你是一位简历优化顾问，请对下面的简历进行润色，并严格输出 JSON。

输出格式：
{{
  "summary": "",
  "sections": [
    {{"title": "职业概述", "original": "", "polished": "", "reason": ""}},
    {{"title": "项目经历优化", "original": "", "polished": "", "reason": ""}},
    {{"title": "技能亮点优化", "original": "", "polished": "", "reason": ""}}
  ],
  "polished_version": ""
}}

要求：
1. 保持事实边界，不要编造不存在的经历
2. 如果 mode=jd，则优先向目标岗位靠拢
3. polished_version 输出一版可直接放进简历的优化稿
4. reason 说明为什么这么改

mode={mode}
JD：
{_jd_text(jd)}

简历结构化信息：
{json.dumps(structured, ensure_ascii=False)}

简历原文：
{resume_text[:8000]}
"""
    response = await client.chat.completions.create(
        model="qwen-plus",
        temperature=0.45,
        messages=[
            {"role": "system", "content": "你是一位专业简历优化顾问，输出必须是 JSON。"},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    data["matched_jd_name"] = jd.get("name") if jd else (resume.get("jd_name") or "通用标准")
    return data


def _fallback_polish_resume(resume: dict, jd: dict | None, structured: dict, mode: str) -> dict:
    base = structured.get("基础信息", {})
    self_intro = structured.get("自我评价") or "具备较好的学习能力、执行力和协作意识，能够围绕业务目标推进任务落地。"
    project = (structured.get("项目经历") or [{}])[0]
    skill_text = resume.get("skills") or "请补充与岗位强相关的技术关键词"
    target_name = jd.get("name") if jd else (resume.get("target_position") or "目标岗位")

    polished_intro = (
        f"聚焦{target_name}方向，具备与岗位相关的项目实践与持续学习能力。"
        f"能够结合业务目标推进方案设计、开发落地与效果优化，具备较强的协作意识与执行稳定性。"
    )
    project_original = project.get("项目描述") or project.get("工作描述") or "项目描述偏笼统，缺少个人贡献和结果。"
    project_polished = (
        f"围绕{project.get('项目名称') or target_name}相关场景，负责核心模块的方案设计与落地实施，"
        "在推进过程中重点处理需求拆解、关键问题定位与效果优化，并最终形成可量化的业务或技术成果。"
    )
    polished_version = "\n".join([
        f"姓名：{base.get('姓名') or resume.get('name') or '候选人'}",
        f"意向岗位：{base.get('意向岗位') or target_name}",
        "",
        "自我评价",
        polished_intro if mode == "jd" else self_intro,
        "",
        "核心技能",
        skill_text,
        "",
        "项目经历优化示例",
        project_polished,
    ])
    return {
        "summary": f"已根据{('目标 JD' if mode == 'jd' else '通用专业表达')}完成一版润色建议，重点增强岗位贴合度、项目说服力和专业表达。",
        "matched_jd_name": jd.get("name") if jd else (resume.get("jd_name") or "通用标准"),
        "sections": [
            {"title": "职业概述", "original": self_intro, "polished": polished_intro, "reason": "让开场表述更偏岗位价值，而不是泛泛自我评价。"},
            {"title": "项目经历优化", "original": project_original, "polished": project_polished, "reason": "把项目描述改成职责、动作、结果更清晰的招聘语言。"},
            {"title": "技能亮点优化", "original": skill_text, "polished": f"{skill_text}；建议把最贴近{target_name}的技术栈放在前面，并补充掌握深度。", "reason": "技能栏需要从“罗列”变成“贴近岗位的优先排序”。"},
        ],
        "polished_version": polished_version,
    }
