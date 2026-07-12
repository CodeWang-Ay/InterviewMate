from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.repositories import plan_repo

router = APIRouter(prefix="/api/plans", tags=["plans"])


class PlanUpdate(BaseModel):
    candidate_name: str | None = None
    jd_name: str | None = None
    match_score: int | None = None
    question_count: int | None = None
    status: str | None = None
    jd_filename: str | None = None
    resume_filename: str | None = None
    questions: str | None = None


@router.get("")
async def list_plans(search: str = "", status: str = ""):
    return plan_repo.list_all(search, status)


@router.get("/{pid}")
async def get_plan(pid: int):
    p = plan_repo.get_by_id(pid)
    if not p:
        raise HTTPException(status_code=404, detail="计划不存在")
    return p


@router.post("")
async def create_plan(body: PlanUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    return plan_repo.create(data)


@router.put("/{pid}")
async def update_plan(pid: int, body: PlanUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    p = plan_repo.update(pid, data)
    if not p:
        raise HTTPException(status_code=404, detail="计划不存在")
    return p


@router.delete("/{pid}")
async def delete_plan(pid: int):
    if not plan_repo.delete(pid):
        raise HTTPException(status_code=404, detail="计划不存在")
    return {"status": "ok"}
