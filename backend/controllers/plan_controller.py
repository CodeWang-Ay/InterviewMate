import re
import secrets
import uuid

import os
import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.controllers.auth_controller import get_current_candidate, require_admin
from backend.repositories import candidate_repo
from backend.repositories import plan_repo, resume_repo
from backend.repositories import upload_repo
from backend.services.file_service import parse_resume
from backend.config import UPLOAD_DIR

router = APIRouter(prefix="/api/plans", tags=["plans"])


def _mask_password(plan: dict) -> dict:
    """返回脱敏后的 plan，candidate_password 仅创建时可见"""
    if not plan:
        return plan
    if plan.get("candidate_password"):
        plan = {**plan, "candidate_password": ""}
    return plan


def _mask_plans(plans: list[dict]) -> list[dict]:
    return [_mask_password(p) for p in plans]


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
    recruitment_type: str | None = None


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
    recruitment_type: str = ""
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
    return _mask_plans(plan_repo.list_all(search, status))


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
    return _mask_plans(plan_repo.list_by_candidate_username(username))


@router.get("/my-resume")
async def my_resume(filename: str = Query(""), username: str = Depends(get_current_candidate)):
    plans = plan_repo.list_by_candidate_username(username)
    allowed_files = {str(plan.get("resume_filename") or "") for plan in plans}
    selected = filename if filename in allowed_files else next((item for item in allowed_files if item), "")
    resume = resume_repo.get_by_file_path(selected)
    if not resume:
        raise HTTPException(status_code=404, detail="暂未找到绑定的简历")
    return resume


@router.get("/my-resume/file")
async def my_resume_file(filename: str = Query(""), username: str = Depends(get_current_candidate)):
    plans = plan_repo.list_by_candidate_username(username)
    allowed_files = {str(plan.get("resume_filename") or "") for plan in plans}
    selected = filename if filename in allowed_files else next((item for item in allowed_files if item), "")
    resume = resume_repo.get_by_file_path(selected)
    if not resume or not resume.get("file_path"):
        raise HTTPException(status_code=404, detail="暂未找到绑定的简历文件")
    file_path = os.path.join(UPLOAD_DIR, "resume", resume["file_path"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="简历文件不存在")
    return FileResponse(file_path, filename=resume.get("original_name") or resume["file_path"], media_type="application/pdf")


@router.get("/{pid}")
async def get_plan(pid: int, _: dict = Depends(require_admin)):
    p = plan_repo.get_by_id(pid)
    if not p:
        raise HTTPException(status_code=404, detail="计划不存在")
    return _mask_password(p)


@router.post("")
async def create_plan(body: PlanUpdate, _: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    username, password = _ensure_candidate_account(data)
    data["candidate_username"] = username
    data["candidate_password"] = password  # plan_repo.create 内部会 bcrypt 哈希
    plan = plan_repo.create(data)
    return {**plan, "candidate_password": password}  # 返回明文，仅此一次


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
            "recruitment_type": body.recruitment_type,
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
    return _mask_password(p)


@router.post("/{pid}/action")
async def plan_action(pid: int, body: PlanAction, _: dict = Depends(require_admin)):
    return _apply_plan_action(pid, body)


@router.put("/{pid}/action")
async def plan_action_compat(pid: int, body: PlanAction, _: dict = Depends(require_admin)):
    return _apply_plan_action(pid, body)


def _apply_plan_action(pid: int, body: PlanAction):
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
