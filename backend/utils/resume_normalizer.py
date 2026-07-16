def normalize_education_level(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    compact = text.replace(" ", "")
    if any(word in compact for word in ("博士", "PhD", "PHD")):
        return "博士"
    if any(word in compact for word in ("硕士", "研究生", "Master", "MASTER")):
        return "硕士"
    if any(word in compact for word in ("本科", "学士", "Bachelor", "BACHELOR")):
        return "本科"
    if any(word in compact for word in ("大专", "专科", "高职")):
        return "大专"
    if any(word in compact for word in ("中专", "高中", "技校")):
        return "高中/中专"
    return ""


def format_education_summary(edu_list: list) -> str:
    if not edu_list:
        return ""
    top = edu_list[0] or {}
    return normalize_education_level(top.get("学历")) or normalize_education_level(top.get("学位"))


def normalize_structured_resume(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}

    education = data.get("教育经历")
    if not isinstance(education, list):
        return data

    for item in education:
        if not isinstance(item, dict):
            continue
        normalized_level = normalize_education_level(item.get("学历"))
        degree_level = normalize_education_level(item.get("学位"))
        item["学历"] = normalized_level or degree_level
    return data
