import asyncio
import uuid
from collections.abc import Awaitable, Callable

from backend.repositories import task_repo


TaskCallable = Callable[[], Awaitable[dict] | dict]


def create_task(task_type: str, title: str, owner: dict | None, runner: TaskCallable) -> dict:
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    task = task_repo.create(task_id, task_type, title, owner)
    asyncio.create_task(_run_task(task_id, runner))
    return task


async def _run_task(task_id: str, runner: TaskCallable) -> None:
    task_repo.update(task_id, status="running", progress=10, message="任务处理中")
    try:
        result = runner()
        if hasattr(result, "__await__"):
            result = await result
        task_repo.update(task_id, status="success", progress=100, message="任务完成", result=result or {})
    except Exception as exc:
        task_repo.update(task_id, status="failed", progress=100, message="任务失败", error=str(exc))
