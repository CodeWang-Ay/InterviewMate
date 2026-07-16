import json
import re

from openai import AsyncOpenAI

from backend.repositories.jd_repo import EXPERIENCE_OPTIONS, normalize_experience
from backend.services.llm_service import OPENAI_API_KEY, OPENAI_BASE_URL


async def generate_jd_draft(
    name: str,
    summary: str = "",
    category: str = "",
    location: str = "",
    recruitment_type: str = "社招",
) -> dict:
    payload = {
        "name": name.strip(),
        "category": category.strip(),
        "location": location.strip(),
        "recruitment_type": recruitment_type.strip() or "社招",
        "summary": summary.strip(),
    }

    if OPENAI_API_KEY:
        try:
            return await _llm_generate_jd(payload)
        except Exception:
            pass
    return _fallback_generate_jd(payload)


async def optimize_jd_draft(jd: dict) -> dict:
    payload = {
        "name": str(jd.get("name") or "").strip(),
        "category": str(jd.get("category") or "").strip(),
        "location": str(jd.get("location") or "").strip(),
        "recruitment_type": str(jd.get("recruitment_type") or "社招").strip() or "社招",
        "experience_required": normalize_experience(jd.get("experience_required")),
        "responsibilities": str(jd.get("responsibilities") or "").strip(),
        "requirements": str(jd.get("requirements") or "").strip(),
        "status": str(jd.get("status") or "enable").strip() or "enable",
    }

    if OPENAI_API_KEY:
        try:
            return await _llm_optimize_jd(payload)
        except Exception:
            pass
    return _fallback_optimize_jd(payload)


async def _llm_generate_jd(payload: dict) -> dict:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
    prompt = f"""你是一位资深招聘顾问，请根据岗位信息生成一份结构清晰、适合招聘后台直接保存的 JD，并严格输出 JSON。

输出 JSON 格式如下：
{{
  "name": "",
  "category": "",
  "location": "",
  "recruitment_type": "",
  "experience_required": "",
  "responsibilities": "",
  "requirements": "",
  "status": "enable"
}}

要求：
1. 只输出 JSON，不要额外解释
2. responsibilities 和 requirements 必须按点分条输出，使用“1. 2. 3.”这种格式，每一条单独换行
3. experience_required 必须且只能从以下枚举中选择一个：{"、".join(EXPERIENCE_OPTIONS)}
4. 生成结果要和岗位名称、简单描述一致，不要泛泛而谈

岗位名称：{payload['name']}
岗位类别：{payload['category'] or '未指定'}
工作地点：{payload['location'] or '未指定'}
招聘类型：{payload['recruitment_type']}
简单描述：{payload['summary'] or '请按常见招聘场景生成一份完整 JD'}
"""
    response = await client.chat.completions.create(
        model="qwen-plus",
        temperature=0.4,
        messages=[
            {"role": "system", "content": "你是一位专业招聘顾问，输出必须是纯 JSON。"},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )
    content = response.choices[0].message.content or "{}"
    data = _parse_json_content(content)
    return {
        "name": data.get("name") or payload["name"],
        "category": data.get("category") or payload["category"],
        "location": data.get("location") or payload["location"],
        "recruitment_type": data.get("recruitment_type") or payload["recruitment_type"],
        "experience_required": normalize_experience(data.get("experience_required")),
        "responsibilities": _normalize_numbered_lines(data.get("responsibilities") or ""),
        "requirements": _normalize_numbered_lines(data.get("requirements") or ""),
        "status": data.get("status") or "enable",
    }


async def _llm_optimize_jd(payload: dict) -> dict:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
    prompt = f"""你是一位资深招聘顾问，请在保留原岗位意图的基础上优化现有 JD，并严格输出 JSON。

输出 JSON 格式如下：
{{
  "name": "",
  "category": "",
  "location": "",
  "recruitment_type": "",
  "experience_required": "",
  "responsibilities": "",
  "requirements": "",
  "status": "enable",
  "summary": ""
}}

优化要求：
1. 只输出 JSON，不要额外解释
2. 不要改变岗位方向，不要虚构过强或无关要求
3. responsibilities 和 requirements 必须按点分条输出，使用“1. 2. 3.”格式，每一条单独换行
4. 用词更专业、更具体，去掉空泛表述，补足职责边界、协作对象、交付要求和能力要求
5. summary 用 2-4 条短句概括本次优化点
6. experience_required 必须且只能从以下枚举中选择一个：{"、".join(EXPERIENCE_OPTIONS)}

原岗位名称：{payload['name']}
岗位类别：{payload['category'] or '未指定'}
工作地点：{payload['location'] or '未指定'}
招聘类型：{payload['recruitment_type']}
经验要求：{payload['experience_required'] or '未填写'}
原岗位职责：
{payload['responsibilities'] or '未填写'}

原任职要求：
{payload['requirements'] or '未填写'}
"""
    response = await client.chat.completions.create(
        model="qwen-plus",
        temperature=0.35,
        messages=[
            {"role": "system", "content": "你是一位专业招聘顾问，输出必须是纯 JSON。"},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )
    content = response.choices[0].message.content or "{}"
    data = _parse_json_content(content)
    return {
        "name": data.get("name") or payload["name"],
        "category": data.get("category") or payload["category"],
        "location": data.get("location") or payload["location"],
        "recruitment_type": data.get("recruitment_type") or payload["recruitment_type"],
        "experience_required": normalize_experience(data.get("experience_required") or payload["experience_required"]),
        "responsibilities": _normalize_numbered_lines(data.get("responsibilities") or payload["responsibilities"]),
        "requirements": _normalize_numbered_lines(data.get("requirements") or payload["requirements"]),
        "status": data.get("status") or payload["status"],
        "summary": _normalize_summary(data.get("summary") or ""),
    }


def _fallback_generate_jd(payload: dict) -> dict:
    role = payload["name"] or "岗位"
    summary = payload["summary"] or f"围绕 {role} 的核心职责、协作方式和能力要求进行招聘。"
    exp = _infer_experience(payload["recruitment_type"], summary)
    responsibilities = "\n".join([
        f"1. 负责 {role} 相关工作的方案设计、执行落地与结果复盘，确保交付质量与进度；",
        f"2. 结合业务目标持续优化 {role} 对应流程、工具或系统，推动效率和体验提升；",
        "3. 与产品、研发、测试、运营等角色保持高效协作，推进跨团队事项闭环；",
        "4. 关注岗位领域的最佳实践，沉淀标准方法、文档规范与可复用经验；",
    ])
    requirements = "\n".join([
        f"1. 具备与 {role} 相关的专业基础，能够独立理解需求并拆解执行；",
        f"2. {exp}，有较好的沟通协作能力与问题分析能力；",
        f"3. 对 {summary[:40]} 有清晰理解，能够快速进入业务场景；",
        "4. 责任心强，具备结果意识、主动推进意识和持续学习能力；",
    ])
    return {
        "name": role,
        "category": payload["category"],
        "location": payload["location"],
        "recruitment_type": payload["recruitment_type"],
        "experience_required": normalize_experience(exp),
        "responsibilities": responsibilities,
        "requirements": requirements,
        "status": "enable",
    }


def _fallback_optimize_jd(payload: dict) -> dict:
    role = payload["name"] or "岗位"
    responsibilities = payload["responsibilities"] or "\n".join([
        f"1. 负责 {role} 相关工作的需求理解、方案制定与执行落地，确保交付质量；",
        "2. 与相关团队协同推进项目进度，及时识别并解决执行过程中的问题；",
        "3. 持续沉淀流程、文档和最佳实践，提升团队协作效率；",
    ])
    requirements = payload["requirements"] or "\n".join([
        f"1. 具备 {role} 相关专业基础，能够独立拆解任务并推进落地；",
        "2. 具备良好的沟通协作、问题分析和结果交付能力；",
        "3. 责任心强，学习能力好，能够适应业务快速变化；",
    ])
    return {
        **payload,
        "experience_required": normalize_experience(payload.get("experience_required")),
        "responsibilities": _normalize_numbered_lines(responsibilities),
        "requirements": _normalize_numbered_lines(requirements),
        "summary": "1. 统一职责和要求的分点格式\n2. 补足岗位交付、协作和能力描述\n3. 保留原岗位方向，便于直接对比采纳",
    }


def _infer_experience(recruitment_type: str, summary: str) -> str:
    text = f"{recruitment_type} {summary}".lower()
    if "实习" in recruitment_type or "应届" in summary:
        return "应届生"
    if any(token in text for token in ["资深", "高级", "专家", "负责人", "lead"]):
        return "5-10年"
    if any(token in text for token in ["中级", "独立负责", "核心模块"]):
        return "3-5年"
    return "1-3年"


def _normalize_numbered_lines(text: str) -> str:
    source = str(text or "").strip()
    if not source:
        return ""

    lines = [line.strip(" ;；") for line in source.splitlines() if line.strip()]
    if not lines:
        return ""

    normalized = []
    for index, line in enumerate(lines, start=1):
        clean = re.sub(r"^\d+[\.\、\)]\s*", "", line).strip()
        normalized.append(f"{index}. {clean}")
    return "\n".join(normalized)


def _parse_json_content(content: str) -> dict:
    source = str(content or "{}").strip()
    if source.startswith("```"):
        source = re.sub(r"^```(?:json)?\s*", "", source)
        source = re.sub(r"\s*```$", "", source).strip()
    if not source.startswith("{"):
        match = re.search(r"\{.*\}", source, re.S)
        source = match.group(0) if match else "{}"
    return json.loads(source)


def _normalize_summary(text: str) -> str:
    source = str(text or "").strip()
    if not source:
        return ""
    if "\n" in source:
        return _normalize_numbered_lines(source)
    parts = [part.strip(" ;；") for part in re.split(r"[。；;]\s*", source) if part.strip()]
    return "\n".join(f"{index}. {part}" for index, part in enumerate(parts[:4], start=1))
