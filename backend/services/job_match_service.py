import json
import re

from backend.repositories import jd_repo, resume_repo


TECH_KEYWORDS = [
    "python", "java", "javascript", "typescript", "vue", "vue3", "react", "node.js",
    "spring", "springboot", "mysql", "postgresql", "redis", "mongodb", "docker",
    "kubernetes", "k8s", "linux", "git", "pytorch", "tensorflow", "langchain",
    "rag", "llm", "nlp", "transformer", "prompt", "微服务", "大模型", "机器学习",
    "深度学习", "自然语言处理", "向量数据库", "数据分析", "产品设计", "项目管理",
]

EDUCATION_RANKS = {"不限": 0, "大专": 1, "本科": 2, "硕士": 3, "博士": 4}
EXPERIENCE_RANKS = {"不限经验": 0, "应届生": 0, "1-3年": 1, "3-5年": 3, "5-10年": 5, "10年以上": 10}


def calculate_resume_jd_match(resume: dict, jd: dict) -> dict:
    """按固定权重计算一份简历与一个 JD 的可解释匹配分数。"""
    structured = _structured_resume(resume)
    resume_text = _resume_search_text(resume, structured)
    jd_text = _jd_search_text(jd)

    required_skills = _extract_keywords(jd_text)
    resume_skills = _extract_keywords(resume_text)
    matched_skills = sorted(required_skills & resume_skills)
    missing_skills = sorted(required_skills - resume_skills)
    skill_score = round(100 * len(matched_skills) / len(required_skills)) if required_skills else 60

    resume_direction = " ".join([
        str(resume.get("target_position") or ""),
        str((structured.get("基础信息") or {}).get("意向岗位") or ""),
    ])
    jd_direction = " ".join([str(jd.get("name") or ""), str(jd.get("category") or "")])
    direction_score, direction_hits = _direction_score(resume_direction, jd_direction, resume_text)

    resume_years = _resume_years(resume, structured)
    required_years = EXPERIENCE_RANKS.get(str(jd.get("experience_required") or "不限经验"), 0)
    experience_score = _requirement_score(resume_years, required_years)

    resume_education = _resume_education_rank(resume, structured)
    required_education = _required_education_rank(jd_text)
    education_score = _requirement_score(resume_education, required_education)

    projects = structured.get("项目经历") or []
    work = structured.get("工作经历") or []
    evidence_points = min(50, len(projects) * 20) + min(35, len(work) * 18)
    if len(resume_text) >= 800:
        evidence_points += 15
    elif len(resume_text) >= 400:
        evidence_points += 8
    evidence_score = min(100, evidence_points)

    dimensions = [
        _dimension("技能覆盖", skill_score, 45, matched_skills, missing_skills),
        {
            "name": "岗位方向",
            "score": direction_score,
            "weight": 20,
            "weighted_score": round(direction_score * 0.20, 1),
            "evidence": direction_hits,
            "gaps": [] if direction_hits else ["简历意向岗位或经历中未体现目标岗位方向"],
        },
        {
            "name": "经验要求",
            "score": experience_score,
            "weight": 15,
            "weighted_score": round(experience_score * 0.15, 1),
            "evidence": [f"简历经验约 {resume_years} 年", f"岗位要求 {jd.get('experience_required') or '不限经验'}"],
            "gaps": [] if experience_score >= 100 else ["经验年限暂未达到岗位要求"],
        },
        {
            "name": "学历要求",
            "score": education_score,
            "weight": 10,
            "weighted_score": round(education_score * 0.10, 1),
            "evidence": [
                f"简历学历：{_education_name(resume_education)}",
                f"岗位要求：{_education_name(required_education)}",
            ],
            "gaps": [] if education_score >= 100 else ["学历暂未达到 JD 明确要求"],
        },
        {
            "name": "经历证据",
            "score": evidence_score,
            "weight": 10,
            "weighted_score": round(evidence_score * 0.10, 1),
            "evidence": [f"{len(projects)} 段项目经历", f"{len(work)} 段工作经历"],
            "gaps": [] if evidence_score >= 70 else ["项目或工作成果描述不够完整"],
        },
    ]
    total_score = round(sum(item["weighted_score"] for item in dimensions))
    return {
        "total_score": min(max(total_score, 0), 100),
        "resume_id": resume.get("id"),
        "jd_id": jd.get("id"),
        "matched_jd_name": jd.get("name", ""),
        "dimensions": dimensions,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "algorithm": "weighted-v1",
    }


def evaluate_resume_match(resume_id: int, jd_id: int) -> dict:
    resume = resume_repo.get_by_id(resume_id)
    if not resume:
        raise ValueError("简历不存在")
    jd = jd_repo.get_by_id(jd_id)
    if not jd:
        raise ValueError("岗位不存在")
    return calculate_resume_jd_match(resume, jd)


def _dimension(name: str, score: int, weight: int, evidence: list[str], gaps: list[str]) -> dict:
    return {
        "name": name,
        "score": score,
        "weight": weight,
        "weighted_score": round(score * weight / 100, 1),
        "evidence": evidence,
        "gaps": gaps,
    }


def _structured_resume(resume: dict) -> dict:
    try:
        return json.loads(resume.get("structured_data") or "{}")
    except (TypeError, ValueError):
        return {}


def _resume_search_text(resume: dict, structured: dict) -> str:
    return json.dumps({
        "name": resume.get("name", ""),
        "target_position": resume.get("target_position", ""),
        "education": resume.get("education", ""),
        "experience_years": resume.get("experience_years", ""),
        "skills": resume.get("skills", ""),
        "structured": structured,
    }, ensure_ascii=False).lower()


def _jd_search_text(jd: dict) -> str:
    return " ".join(str(jd.get(field) or "") for field in (
        "name", "category", "responsibilities", "requirements", "experience_required"
    )).lower()


def _extract_keywords(text: str) -> set[str]:
    normalized = str(text or "").lower()
    found = set()
    for keyword in TECH_KEYWORDS:
        pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])" if keyword[0].isascii() else re.escape(keyword)
        if re.search(pattern, normalized, re.IGNORECASE):
            found.add(keyword)
    return found


def _direction_score(resume_direction: str, jd_direction: str, resume_text: str) -> tuple[int, list[str]]:
    jd_tokens = _direction_tokens(jd_direction)
    if not jd_tokens:
        return 60, []
    direction_text = f"{resume_direction} {resume_text}".lower()
    hits = sorted(token for token in jd_tokens if token.lower() in direction_text)
    score = round(100 * len(hits) / len(jd_tokens))
    return max(20, score), hits


def _direction_tokens(text: str) -> set[str]:
    stopwords = {"工程师", "开发", "岗位", "高级", "初级", "专员", "方向", "技术"}
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", str(text or ""))
    ascii_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", str(text or "").lower())
    tokens = {token for token in chinese + ascii_tokens if token not in stopwords}
    return tokens or {str(text or "").strip()} - {""}


def _resume_years(resume: dict, structured: dict) -> int:
    text = str(resume.get("experience_years") or "")
    numbers = [int(item) for item in re.findall(r"\d+", text)]
    if numbers:
        return max(numbers)
    work = structured.get("工作经历") or []
    return max(0, len(work))


def _resume_education_rank(resume: dict, structured: dict) -> int:
    text = f"{resume.get('education') or ''} {json.dumps(structured.get('教育经历') or [], ensure_ascii=False)}"
    return _education_rank_from_text(text)


def _required_education_rank(jd_text: str) -> int:
    if "学历不限" in jd_text or "不限学历" in jd_text:
        return 0
    return _education_rank_from_text(jd_text)


def _education_rank_from_text(text: str) -> int:
    for name in ("博士", "硕士", "本科", "大专"):
        if name in str(text or ""):
            return EDUCATION_RANKS[name]
    return 0


def _requirement_score(actual: int, required: int) -> int:
    if required <= 0:
        return 100
    if actual >= required:
        return 100
    ratio = actual / required
    return max(20, round(ratio * 100))


def _education_name(rank: int) -> str:
    return next((name for name, value in EDUCATION_RANKS.items() if value == rank), "未识别")
