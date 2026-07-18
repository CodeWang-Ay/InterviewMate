from fastapi import APIRouter, Depends, HTTPException

from backend.controllers.auth_controller import get_current_identity
from backend.repositories import task_repo

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(limit: int = 30, identity: dict = Depends(get_current_identity)):
    return task_repo.list_recent(identity, limit)


@router.get("/{task_id}")
async def get_task(task_id: str, identity: dict = Depends(get_current_identity)):
    task = task_repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if identity["kind"] != "admin":
        if task.get("owner_kind") != identity["kind"] or task.get("owner_username") != identity["username"]:
            raise HTTPException(status_code=403, detail="无权访问该任务")
    return task
