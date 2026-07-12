import os
import asyncio
from openai import AsyncOpenAI
import platform
import time
from dotenv         import load_dotenv
load_dotenv()

client = AsyncOpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

async def main():
    method_start_time = time.time()
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": "你是谁"}],
        model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    )
    print(response.model_dump_json())
    cost_time = time.time() - method_start_time
    print(f"cost_time: {cost_time:.2f}")

# if platform.system() == "Windows":
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# 异步调用支持并发
if __name__ == '__main__':
    asyncio.run(main())