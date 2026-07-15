import json
import os
import re
import json_repair
from loguru import logger
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 先加载 .env，再读取环境变量
load_dotenv(".env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
logger.info(f"OPENAI_API_KEY: {'已设置' if OPENAI_API_KEY else '未设置'}, BASE_URL: {OPENAI_BASE_URL or '(默认)'}")
RESUME_EXTRACTION_PROMPT = """你是一位专业的简历解析专家。请从以下简历文本中提取关键信息，严格按 JSON 格式输出。

输出 JSON 结构如下（缺失字段用空字符串或空数组）：
{
  "基础信息": {
    "姓名": "",
    "性别": "",
    "意向岗位": "",
    "邮箱": "",
    "电话": "",
    "年龄": "",
    "籍贯": "",
    "地址": ""
  },
  "自我评价": "",
  "教育经历": [
    {
      "学校": "",
      "专业": "",
      "学位": "",
      "学历": "",
      "开始时间": "",
      "结束时间": ""
    }
  ],
  "工作经历": [
    {
      "公司名称": "",
      "职位": "",
      "开始时间": "",
      "结束时间": "",
      "工作描述": ""
    }
  ],
  "项目经历": [
    {
      "项目名称": "",
      "角色": "",
      "开始时间": "",
      "结束时间": "",
      "项目描述": ""
    }
  ]
}

要求：
1. 只输出 JSON，不要任何其他文字
2. 缺失字段用 "" 或 [] 表示
3. 工作描述和项目描述保留完整内容
4. 所有时间格式统一为 YYYY-MM

简历文本：
"""


async def extract_resume_info(text: str) -> dict:
    """调用 OpenAI 兼容 API 提取简历结构化信息"""
    if not OPENAI_API_KEY:
        return _fallback_extraction(text)

    try:
        logger.info("简历解析...............")
        client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)

        truncated = text[:15000] if len(text) > 15000 else text

        response = await client.chat.completions.create(
            model="qwen-plus",
            temperature=0.1,
            messages=[
                {"role": "system", "content": "你是一位专业的简历解析专家，输出必须是纯 JSON。"},
                {"role": "user", "content": RESUME_EXTRACTION_PROMPT + truncated},
            ],
            extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}}
        )

        content = response.choices[0].message.content
        llm_result = json_repair.loads(content)

        return llm_result

    except Exception as e:
        print(f"LLM 简历解析失败: {e}")
        return _fallback_extraction(text)


def _fallback_extraction(text: str) -> dict:
    """正则兜底提取（LLM 不可用时）"""
    result = {
        "基础信息": {
            "姓名": _match_first(text, [
                r"姓\s*名[：:]\s*(.+)",
                r"(?<=姓名).{2,4}(?=\s|$|\n)",
            ]) or "",
            "性别": "",
            "意向岗位": _match_first(text, [
                r"意向岗位[：:]\s*(.+)",
                r"求职意向[：:]\s*(.+)",
                r"应聘岗位[：:]\s*(.+)",
            ]) or "",
            "邮箱": _match_first(text, [
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            ]) or "",
            "电话": _match_first(text, [
                r"1[3-9]\d{9}",
                r"\d{3,4}[-\s]?\d{7,8}",
            ]) or "",
            "年龄": _match_first(text, [
                r"年龄[：:]\s*(\d+)",
                r"(\d{2})\s*岁",
            ]) or "",
            "籍贯": "",
            "地址": "",
        },
        "自我评价": _match_section(text, ["自我评价", "个人评价"]) or "",
        "教育经历": [],
        "工作经历": [],
        "项目经历": [],
    }
    return result


def _match_first(text: str, patterns: list[str]) -> str | None:
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1) if m.lastindex else m.group()
    return None


def _match_section(text: str, keywords: list[str]) -> str | None:
    for kw in keywords:
        idx = text.find(kw)
        if idx >= 0:
            end_idx = text.find("\n\n", idx)
            return text[idx:end_idx].strip() if end_idx > 0 else text[idx:].strip()[:200]
    return None
