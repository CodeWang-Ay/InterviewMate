import asyncio

from openai import AsyncOpenAI

from backend.services.llm_service import OPENAI_API_KEY, OPENAI_BASE_URL


async def generate_assistant_reply(identity: dict, message: str, history: list[dict] | None = None) -> str:
    history = history or []
    if OPENAI_API_KEY:
        try:
            return await _llm_reply(identity, message, history)
        except Exception:
            pass
    return _fallback_reply(identity, message)


async def stream_assistant_reply(identity: dict, message: str, history: list[dict] | None = None):
    history = history or []
    if OPENAI_API_KEY:
        try:
            async for chunk in _llm_reply_stream(identity, message, history):
                yield chunk
            return
        except Exception:
            pass

    reply = _fallback_reply(identity, message)
    for chunk in _chunk_text(reply, 18):
        yield chunk
        await asyncio.sleep(0.03)


async def _llm_reply(identity: dict, message: str, history: list[dict]) -> str:
    role_name = "后台管理员" if identity.get("kind") == "admin" else "面试者"
    profile = identity.get("profile", {})
    nickname = profile.get("nickname") or profile.get("candidate_name") or identity.get("username") or role_name
    client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)

    system_prompt = f"""你是 InterviewMate 系统里的 AI 聊天助手。

当前用户角色：{role_name}
当前用户昵称：{nickname}

你的任务：
1. 可以和用户自然闲聊，语气轻松、友好、靠谱。
2. 如果用户问的是招聘后台、面试、JD、简历、面试计划、面试官训练等相关内容，优先结合这个系统的语境回答。
3. 不要假装自己已经执行了页面操作或修改了数据库。
4. 回答要简洁、实用，不要太官腔。
5. 如果只是日常聊天，也正常聊天，不必强行扯回招聘系统。
"""

    messages = [{"role": "system", "content": system_prompt}]
    for item in history[-10:]:
        role = item.get("role", "")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    response = await client.chat.completions.create(
        model="qwen-plus",
        temperature=0.8,
        messages=messages,
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )
    return (response.choices[0].message.content or "").strip() or _fallback_reply(identity, message)


async def _llm_reply_stream(identity: dict, message: str, history: list[dict]):
    role_name = "后台管理员" if identity.get("kind") == "admin" else "面试者"
    profile = identity.get("profile", {})
    nickname = profile.get("nickname") or profile.get("candidate_name") or identity.get("username") or role_name
    client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)

    system_prompt = f"""你是 InterviewMate 系统里的 AI 聊天助手。

当前用户角色：{role_name}
当前用户昵称：{nickname}

你的任务：
1. 可以和用户自然闲聊，语气轻松、友好、靠谱。
2. 如果用户问的是招聘后台、面试、JD、简历、面试计划、面试官训练等相关内容，优先结合这个系统的语境回答。
3. 不要假装自己已经执行了页面操作或修改了数据库。
4. 回答要简洁、实用，不要太官腔。
5. 如果只是日常聊天，也正常聊天，不必强行扯回招聘系统。
"""

    messages = [{"role": "system", "content": system_prompt}]
    for item in history[-10:]:
        role = item.get("role", "")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    stream = await client.chat.completions.create(
        model="qwen-plus",
        temperature=0.8,
        messages=messages,
        stream=True,
        extra_body={"enable_thinking": False, "thinking": False, "chat_template_kwargs": {"thinking": False}},
    )

    emitted = False
    async for event in stream:
        try:
            delta = event.choices[0].delta.content or ""
        except Exception:
            delta = ""
        if delta:
            emitted = True
            yield delta

    if not emitted:
        fallback = _fallback_reply(identity, message)
        for chunk in _chunk_text(fallback, 18):
            yield chunk
            await asyncio.sleep(0.03)


def _fallback_reply(identity: dict, message: str) -> str:
    role_name = "管理员" if identity.get("kind") == "admin" else "面试者"
    lower = message.lower()

    if any(token in message for token in ["你好", "在吗", "哈喽", "hello", "hi"]):
        return f"在的，我是你的 AI 助手。你现在是以{role_name}身份在使用系统，想聊聊天，还是想让我帮你梳理面试相关思路？"
    if any(token in message for token in ["简历", "jd", "岗位", "面试计划", "训练台", "面试官"]):
        return "这类问题我能帮你一起拆。你可以直接把你卡住的点发给我，比如“这份简历该怎么追问”或者“这个 JD 一面该问什么”。"
    if any(token in lower for token in ["累", "烦", "迷茫", "焦虑"]):
        return "能理解，长时间盯着这些流程确实会累。先缓一口气也没问题，你把当前最烦的那个点丢给我，我们一个个拆开。"
    if any(token in message for token in ["讲个笑话", "闲聊", "无聊"]):
        return "那我陪你摸会儿鱼也行。不过我比较擅长的是不太尬的那种闲聊。比如，你今天最想吐槽系统里的哪一步？"
    return "我在这儿。你可以随便跟我聊，也可以直接问我招聘流程、简历判断、面试追问、训练思路这些事。"


def _chunk_text(text: str, size: int) -> list[str]:
    if size <= 0:
        return [text]
    return [text[i:i + size] for i in range(0, len(text), size)] or [text]
