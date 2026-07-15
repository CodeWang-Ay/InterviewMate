import json
import re

from openai import OpenAI

from backend.services.llm_service import OPENAI_API_KEY, OPENAI_BASE_URL


def generate_jd_draft(
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
            return _llm_generate_jd(payload)
        except Exception:
            pass
    return _fallback_generate_jd(payload)


def _llm_generate_jd(payload: dict) -> dict:
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
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
3. experience_required 只输出简短经验描述，例如“1-3年”“3-5年”“应届生 / 实习经历优先”
4. 生成结果要和岗位名称、简单描述一致，不要泛泛而谈

岗位名称：{payload['name']}
岗位类别：{payload['category'] or '未指定'}
工作地点：{payload['location'] or '未指定'}
招聘类型：{payload['recruitment_type']}
简单描述：{payload['summary'] or '请按常见招聘场景生成一份完整 JD'}
"""
    response = client.chat.completions.create(
        model="qwen-plus",
        temperature=0.4,
        messages=[
            {"role": "system", "content": "你是一位专业招聘顾问，输出必须是纯 JSON。"},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    return {
        "name": data.get("name") or payload["name"],
        "category": data.get("category") or payload["category"],
        "location": data.get("location") or payload["location"],
        "recruitment_type": data.get("recruitment_type") or payload["recruitment_type"],
        "experience_required": data.get("experience_required") or "",
        "responsibilities": _normalize_numbered_lines(data.get("responsibilities") or ""),
        "requirements": _normalize_numbered_lines(data.get("requirements") or ""),
        "status": data.get("status") or "enable",
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
        "experience_required": exp,
        "responsibilities": responsibilities,
        "requirements": requirements,
        "status": "enable",
    }


def _infer_experience(recruitment_type: str, summary: str) -> str:
    text = f"{recruitment_type} {summary}".lower()
    if "实习" in recruitment_type or "应届" in summary:
        return "应届生 / 实习经历优先"
    if any(token in text for token in ["资深", "高级", "专家", "负责人", "lead"]):
        return "5年以上"
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
