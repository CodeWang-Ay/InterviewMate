import re

from backend.config import DEFAULT_QUESTIONS
from backend.repositories.upload_repo import read_text
from backend.services.llm_service import extract_resume_info


def extract_questions_from_jd(jd_text: str) -> list[str]:
    lines = jd_text.strip().split("\n")
    questions = []
    in_section = False
    for line in lines:
        line = line.strip()
        if "面试问题" in line or "建议问题" in line:
            in_section = True
            continue
        if in_section and re.match(r"^\d+[\.\、\)]", line):
            q = re.sub(r"^\d+[\.\、\)]\s*", "", line).strip()
            if q:
                questions.append(q)
    return questions if questions else DEFAULT_QUESTIONS


async def parse_resume(filename: str) -> dict:
    """解析简历，返回原始文本 + 结构化信息"""
    raw = read_text("resume", filename)
    structured = await extract_resume_info(raw)               # pdf 简历解析
    return {"raw": raw, "structured": structured}


def read_jd(filename: str) -> str:
    return read_text("jd", filename)
