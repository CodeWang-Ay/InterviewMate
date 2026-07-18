import re
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.controllers.auth_controller import get_current_candidate, require_admin
from backend.repositories import candidate_repo
from backend.repositories import plan_repo

router = APIRouter(prefix="/api/plans", tags=["plans"])


class PlanUpdate(BaseModel):
    candidate_name: str | None = None
    jd_name: str | None = None
    workflow_id: str | None = None
    workflow_name: str | None = None
    stage_order: int | None = None
    stage_count: int | None = None
    interview_round: str | None = None
    match_score: int | None = None
    question_count: int | None = None
    status: str | None = None
    jd_filename: str | None = None
    resume_filename: str | None = None
    questions: str | None = None
    candidate_username: str | None = None
    candidate_password: str | None = None
    scheduled_at: str | None = None
    interviewer: str | None = None
    meeting_url: str | None = None
    interview_result: str | None = None
    result_score: int | None = None
    result_note: str | None = None


class WorkflowStage(BaseModel):
    name: str
    question_count: int = 10


class WorkflowTemplateSave(BaseModel):
    name: str
    desc: str = ""
    stages: list[WorkflowStage]


class WorkflowCreate(BaseModel):
    candidate_name: str
    jd_name: str = "待定岗位"
    workflow_name: str
    resume_filename: str = ""
    stages: list[WorkflowStage]


class PlanAction(BaseModel):
    action: str
    scheduled_at: str | None = None
    interviewer: str | None = None
    meeting_url: str | None = None
    interview_result: str | None = None
    result_score: int | None = None
    result_note: str | None = None


@router.get("")
async def list_plans(search: str = "", status: str = "", _: dict = Depends(require_admin)):
    return plan_repo.list_all(search, status)


@router.get("/workflow-templates")
async def list_workflow_templates(_: dict = Depends(require_admin)):
    return plan_repo.list_workflow_templates()


@router.post("/workflow-templates")
async def create_workflow_template(body: WorkflowTemplateSave, _: dict = Depends(require_admin)):
    if not body.stages:
        raise HTTPException(status_code=400, detail="流程至少需要一个面试环节")
    return plan_repo.save_workflow_template(body.model_dump())


@router.put("/workflow-templates/{template_id}")
async def update_workflow_template(template_id: int, body: WorkflowTemplateSave, _: dict = Depends(require_admin)):
    if not body.stages:
        raise HTTPException(status_code=400, detail="流程至少需要一个面试环节")
    template = plan_repo.save_workflow_template(body.model_dump(), template_id)
    if not template:
        raise HTTPException(status_code=404, detail="流程模板不存在")
    return template


@router.get("/my")
async def my_plans(username: str = Depends(get_current_candidate)):
    return plan_repo.list_by_candidate_username(username)


@router.get("/{pid}")
async def get_plan(pid: int, _: dict = Depends(require_admin)):
    p = plan_repo.get_by_id(pid)
    if not p:
        raise HTTPException(status_code=404, detail="计划不存在")
    return p


@router.post("")
async def create_plan(body: PlanUpdate, _: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    username, password = _ensure_candidate_account(data)
    data["candidate_username"] = username
    data["candidate_password"] = password
    return plan_repo.create(data)


@router.post("/workflow")
async def create_workflow(body: WorkflowCreate, _: dict = Depends(require_admin)):
    if not body.stages:
        raise HTTPException(status_code=400, detail="流程至少需要一个面试环节")

    workflow_id = f"wf_{uuid.uuid4().hex[:10]}"
    username, password = _ensure_candidate_account({"candidate_name": body.candidate_name})
    plans = []
    for index, stage in enumerate(body.stages, start=1):
        data = {
            "candidate_name": body.candidate_name,
            "jd_name": body.jd_name,
            "workflow_id": workflow_id,
            "workflow_name": body.workflow_name,
            "stage_order": index,
            "stage_count": len(body.stages),
            "interview_round": stage.name,
            "question_count": stage.question_count,
            "status": "wait" if index == 1 else "pending",
            "resume_filename": body.resume_filename,
            "candidate_username": username,
            "candidate_password": password,
        }
        plans.append(plan_repo.create(data))
    return {
        "workflow_id": workflow_id,
        "workflow_name": body.workflow_name,
        "candidate_name": body.candidate_name,
        "candidate_username": username,
        "candidate_password": password,
        "plans": plans,
    }


@router.put("/{pid}")
async def update_plan(pid: int, body: PlanUpdate, _: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    p = plan_repo.update(pid, data)
    if not p:
        raise HTTPException(status_code=404, detail="计划不存在")
    return p


@router.post("/{pid}/action")
async def plan_action(pid: int, body: PlanAction, _: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None and k != "action"}
    try:
        p = plan_repo.transition(pid, body.action, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not p:
        raise HTTPException(status_code=404, detail="计划不存在")
    return p


@router.delete("/{pid}")
async def delete_plan(pid: int, _: dict = Depends(require_admin)):
    if not plan_repo.delete(pid):
        raise HTTPException(status_code=404, detail="计划不存在")
    return {"status": "ok"}


def _ensure_candidate_account(data: dict) -> tuple[str, str]:
    if data.get("candidate_username") and data.get("candidate_password"):
        return data["candidate_username"], data["candidate_password"]

    base = re.sub(r"[^a-zA-Z0-9]+", "", data.get("candidate_name", "")) or "candidate"
    base = base.lower()[:16]
    password = f"IM{secrets.token_hex(3)}"
    for _ in range(10):
        username = f"{base}{secrets.randbelow(9000) + 1000}"
        result = candidate_repo.register(username, password, data.get("candidate_name", "") or username)
        if result:
            return username, password
    raise HTTPException(status_code=500, detail="候选人账号生成失败，请重试")
