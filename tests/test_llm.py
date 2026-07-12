"""
测试 OpenAI API 简历解析调用
用法:
    export OPENAI_API_KEY="sk-xxx"
    export OPENAI_BASE_URL="https://xxx/v1"   # 可选
    uv run python tests/test_llm.py
"""
import json
import os
import re

SAMPLE_RESUME = """
姓名：陈弘州
性别：男
意向岗位：质量工程师
邮箱：18575579612@163.com
电话：18575579612
年龄：26

教育经历
硕士 江苏大学 电子信息（控制工程） 2022-09 至 2025-06
本科 广东技术师范大学 机械电子工程 2018-09 至 2022-06

工作经历
中信银行股份有限公司上海分行 | 大模型算法及应用研发岗 | 2025-08 至今
1.负责行内大模型技术体系建设，根据业务部门需求设计并落地AI解决方案
2.负责大模型定制化训练，包括SFT和DPO等后训练工作
3.通过知识蒸馏强化模型推理能力，结合量化压缩技术实现推理速度提升60%

上海合合信息科技股份有限公司 | 大模型数据开发实习生 | 2024-05 至 2024-11
1.搭建LLM预训练数据处理全流程管线，基于Python+Spark完成80TB多源数据采集
2.集成FastText、KenLM等模型剔除低质量数据

项目经历
金融知识智能问答助手 | 核心研发 | 2025-08 至 2026-01
构建面向金融业务的智能问答系统，覆盖金融知识问答、贷款策略等5+核心场景

国际跨境业务智能风控系统 | 核心研发 | 2025-08 至 2026-01
构建大模型Agent的跨境交易合规审查系统

自我评价
具有扎实的机器学习和大模型开发经验，熟悉Python、PyTorch等技术栈。
"""

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
    {"学校": "", "专业": "", "学位": "", "学历": "", "开始时间": "", "结束时间": ""}
  ],
  "工作经历": [
    {"公司名称": "", "职位": "", "开始时间": "", "结束时间": "", "工作描述": ""}
  ],
  "项目经历": [
    {"项目名称": "", "角色": "", "开始时间": "", "结束时间": "", "项目描述": ""}
  ]
}

要求：
1. 只输出 JSON，不要任何其他文字
2. 缺失字段用 "" 或 [] 表示
3. 工作描述和项目描述保留完整内容
4. 所有时间格式统一为 YYYY-MM

简历文本：
"""


def test_openai_chat(model: str = "gpt-4o-mini") -> dict:
    """直接测试 OpenAI chat.completions.create 调用"""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "")

    if not api_key:
        raise RuntimeError("请设置环境变量 OPENAI_API_KEY")

    client = OpenAI(api_key=api_key, base_url=base_url or None)

    prompt = RESUME_EXTRACTION_PROMPT + SAMPLE_RESUME

    print(f"调用模型: {model}")
    print(f"Base URL: {base_url or '(默认)'}")
    print(f"Prompt 长度: {len(prompt)} 字符")
    print("-" * 60)

    response = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": "你是一位专业的简历解析专家，输出必须是纯 JSON。"},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content
    usage = response.usage

    print(f"Token 用量: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")
    print(f"模型返回长度: {len(content)} 字符")
    print("-" * 60)
    print("原始返回:")
    print(content)
    print("-" * 60)

    # 提取 JSON
    json_match = re.search(r"\{[\s\S]*\}", content)
    if not json_match:
        raise ValueError("未在返回中找到 JSON")

    result = json.loads(json_match.group())
    return result


def main():
    model = os.getenv("TEST_MODEL", "gpt-4o-mini")

    print("=" * 60)
    print("OpenAI API 简历解析测试")
    print("=" * 60)

    try:
        result = test_openai_chat(model=model)

        print()
        print("=" * 60)
        print("解析结果")
        print("=" * 60)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print()

        # 验证关键字段
        basic = result.get("基础信息", {})
        checks = [
            ("姓名", bool(basic.get("姓名"))),
            ("邮箱", bool(basic.get("邮箱"))),
            ("教育经历", len(result.get("教育经历", [])) >= 1),
            ("工作经历", len(result.get("工作经历", [])) >= 1),
            ("项目经历", len(result.get("项目经历", [])) >= 1),
        ]
        print("字段验证:")
        for name, ok in checks:
            print(f"  {'✅' if ok else '❌'} {name}")
        print()

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    main()
