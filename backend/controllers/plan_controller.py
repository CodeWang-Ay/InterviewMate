import json
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
from backend.repositories import application_repo, plan_repo, resume_repo
from backend.repositories import upload_repo
from backend.services.file_service import parse_resume
from backend.services.job_match_service import evaluate_resume_match
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
    result = []
    for plan in plans:
        ready, reason = plan_repo.candidate_interview_readiness(plan)
        result.append(_mask_password({
            **plan,
            "interview_ready": ready,
            "interview_block_reason": reason,
        }))
    return result


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
    application_id: int | None = None
    resume_id: int | None = None
    jd_id: int | None = None


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
    resume_id: int | None = None
    jd_id: int | None = None
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
    plans = plan_repo.list_by_candidate_username(username)
    for application_id in {plan.get("application_id") for plan in plans if plan.get("application_id")}:
        application = application_repo.get_by_id(int(application_id))
        if application and application.get("candidate_username") == username and not application.get("match_score"):
            _calculate_and_save_application_match(application)
    return _mask_plans(plan_repo.list_by_candidate_username(username))


@router.get("/my/application-quota")
async def my_application_quota(username: str = Depends(get_current_candidate)):
    return application_repo.get_candidate_quota(username)


@router.post("/apply/{job_id}")
async def apply_job(job_id: int, resume_filename: str = "", username: str = Depends(get_current_candidate)):
    """候选人投递岗位，创建投递记录"""
    from backend.repositories import jd_repo
    jd = jd_repo.get_by_id(job_id)
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")
    if jd.get("status") != "enable":
        raise HTTPException(status_code=404, detail="岗位已下线")

    existing_application = application_repo.find_by_candidate_and_jd(username, job_id)
    if existing_application:
        if not existing_application.get("match_score"):
            existing_application = _calculate_and_save_application_match(existing_application)
        existing_plans = plan_repo.list_by_workflow_id(existing_application.get("workflow_id", ""))
        return {
            "applied": True,
            "application": existing_application,
            "plan": _mask_password(existing_plans[0]) if existing_plans else None,
            "message": "已投递过该岗位",
        }
    quota = application_repo.get_candidate_quota(username)
    recruitment_type = application_repo.normalize_recruitment_type(jd.get("recruitment_type"))
    type_quota = quota["buckets"][recruitment_type]
    if type_quota["remaining"] <= 0:
        available_text = f"，下一次可投递时间：{type_quota['available_at']}" if type_quota.get("available_at") else ""
        raise HTTPException(
            status_code=429,
            detail=f"每位候选人滚动 6 个月内最多主动投递 {type_quota['limit']} 个{recruitment_type}岗位{available_text}",
        )

    candidate = candidate_repo.get_candidate_info(username) or {}
    existing = plan_repo.list_by_candidate_username(username)
    # 自动关联候选人当前简历；历史计划中的简历只作旧数据兼容，不再被覆盖
    existing_resume = resume_filename.strip() or str(candidate.get("resume_filename") or "").strip()
    if not existing_resume:
        for p in existing:
            if p.get("resume_filename"):
                existing_resume = p.get("resume_filename")
                break
    resume = resume_repo.get_by_file_path(existing_resume)
    if existing_resume and not resume:
        raise HTTPException(status_code=400, detail="当前简历不存在，请重新上传")
    if resume:
        owner = resume.get("candidate_username") or ""
        if owner and owner != username:
            raise HTTPException(status_code=403, detail="不能使用其他候选人的简历")
        if not owner:
            if existing_resume != str(candidate.get("resume_filename") or ""):
                raise HTTPException(status_code=403, detail="该简历尚未绑定当前候选人")
            resume = resume_repo.update(resume["id"], {"candidate_username": username, "source": "candidate"})

    workflow_id = f"apply_{job_id}_{username}_{uuid.uuid4().hex[:6]}"
    match_result = evaluate_resume_match(resume["id"], job_id) if resume else None
    match_score = int((match_result or {}).get("total_score") or 0)
    application = application_repo.create({
        "candidate_name": candidate.get("candidate_name") or username,
        "candidate_username": username,
        "jd_id": job_id,
        "jd_name": jd.get("name", ""),
        "resume_id": resume.get("id") if resume else None,
        "match_score": match_score,
        "match_details": json.dumps(match_result or {}, ensure_ascii=False),
        "recruitment_type": recruitment_type,
        "source": "candidate",
        "workflow_id": workflow_id,
    })
    plan = plan_repo.create({
        "candidate_name": candidate.get("candidate_name") or username,
        "candidate_username": username,
        "jd_name": jd.get("name", ""),
        "jd_id": job_id,
        "recruitment_type": jd.get("recruitment_type", "社招"),
        "status": "pending",
        "stage_order": 1,
        "stage_count": 1,
        "workflow_id": workflow_id,
        "workflow_name": f"投递：{jd.get('name', '')}",
        "resume_filename": existing_resume,
        "resume_id": resume.get("id") if resume else None,
        "application_id": application.get("id"),
        "match_score": match_score,
    })
    return {
        "applied": True,
        "application": application,
        "plan": plan,
        "message": "投递成功",
        "has_resume": bool(existing_resume),
    }


@router.get("/my-resume")
async def my_resume(filename: str = Query(""), username: str = Depends(get_current_candidate)):
    plans = plan_repo.list_by_candidate_username(username)
    allowed_files = {str(plan.get("resume_filename") or "") for plan in plans}
    candidate = candidate_repo.get_candidate_info(username) or {}
    candidate_resume = str(candidate.get("resume_filename") or "")
    if candidate_resume:
        allowed_files.add(candidate_resume)
    allowed_files.update(item.get("file_path", "") for item in resume_repo.list_by_candidate_username(username))
    selected = filename if filename in allowed_files else next((item for item in allowed_files if item), "")
    resume = resume_repo.get_by_file_path(selected)
    if not resume:
        raise HTTPException(status_code=404, detail="暂未找到绑定的简历")
    return resume


@router.get("/my-resume/file")
async def my_resume_file(filename: str = Query(""), username: str = Depends(get_current_candidate)):
    plans = plan_repo.list_by_candidate_username(username)
    allowed_files = {str(plan.get("resume_filename") or "") for plan in plans}
    candidate = candidate_repo.get_candidate_info(username) or {}
    candidate_resume = str(candidate.get("resume_filename") or "")
    if candidate_resume:
        allowed_files.add(candidate_resume)
    allowed_files.update(item.get("file_path", "") for item in resume_repo.list_by_candidate_username(username))
    selected = filename if filename in allowed_files else next((item for item in allowed_files if item), "")
    resume = resume_repo.get_by_file_path(selected)
    if not resume or not resume.get("file_path"):
        raise HTTPException(status_code=404, detail="暂未找到绑定的简历文件")
    file_path = os.path.join(UPLOAD_DIR, "resume", resume["file_path"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="简历文件不存在")
    return FileResponse(file_path, filename=resume.get("original_name") or resume["file_path"], media_type="application/pdf")


class ResumeEditBody(BaseModel):
    name: str | None = None
    target_position: str | None = None
    structured_data: str | None = None


@router.put("/my-resume")
async def update_my_resume(body: ResumeEditBody, username: str = Depends(get_current_candidate)):
    """候选人编辑自己的简历结构化数据"""
    plans = plan_repo.list_by_candidate_username(username)
    allowed_files = {str(plan.get("resume_filename") or "") for plan in plans}
    candidate = candidate_repo.get_candidate_info(username) or {}
    candidate_resume = str(candidate.get("resume_filename") or "")
    if candidate_resume:
        allowed_files.add(candidate_resume)
    allowed_files.update(item.get("file_path", "") for item in resume_repo.list_by_candidate_username(username))
    if not allowed_files:
        raise HTTPException(status_code=404, detail="暂未绑定简历")
    selected = next((item for item in allowed_files if item), "")
    resume = resume_repo.get_by_file_path(selected)
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = resume_repo.update(resume["id"], data)
    if not updated:
        raise HTTPException(status_code=500, detail="更新失败")
    return updated


@router.post("/my-resume/upload")
async def upload_my_resume(file: UploadFile = File(...), username: str = Depends(get_current_candidate)):
    """候选人上传新简历文件并触发解析"""
    ext = upload_repo.validate(file)
    content = await file.read()
    file_md5 = hashlib.md5(content).hexdigest()
    duplicates = resume_repo.find_duplicates(file_md5)
    owned_duplicate = next((item for item in duplicates if item.get("candidate_username") == username), None)
    if owned_duplicate:
        candidate_repo.update_profile(username, {"resume_filename": owned_duplicate.get("file_path", "")})
        return owned_duplicate
    filename = upload_repo.save_content(content, file.filename or "unknown", "resume", ext)
    candidate = candidate_repo.get_candidate_info(username) or {}
    resume = resume_repo.create({
        "name": os.path.splitext(file.filename or "unknown")[0],
        "file_path": filename,
        "file_type": ext.lstrip("."),
        "parse_status": "wait",
        "candidate_status": "待筛选",
        "original_name": file.filename or "",
        "file_md5": file_md5,
        "candidate_username": username,
        "source": "candidate",
    })
    if not resume:
        raise HTTPException(status_code=500, detail="简历记录创建失败，请重试")
    # 只更新候选人的“当前简历”，历史投递继续保留投递时的简历快照
    candidate_repo.update_profile(username, {"resume_filename": filename})
    # 触发解析
    result = await parse_resume(filename)
    resume_repo.update(resume["id"], {
        "parse_status": "success",
        "structured_data": json.dumps(result["structured"], ensure_ascii=False),
        "name": (result["structured"].get("基础信息", {}) or {}).get("姓名") or resume["name"],
        "target_position": (result["structured"].get("基础信息", {}) or {}).get("意向岗位") or "",
    })
    # 同步电话/邮箱到候选人 profile
    basic = (result.get("structured", {}) or {}).get("基础信息", {}) or {}
    candidate_updates = {}
    if basic.get("电话") and not candidate.get("phone"):
        candidate_updates["phone"] = basic["电话"]
    if basic.get("邮箱") and not candidate.get("email"):
        candidate_updates["email"] = basic["邮箱"]
    if candidate_updates:
        candidate_repo.update_profile(username, candidate_updates)
    return resume_repo.get_by_id(resume["id"])


@router.post("/applications/{application_id}/cancel")
async def cancel_my_application(application_id: int, username: str = Depends(get_current_candidate)):
    application = application_repo.get_by_id(application_id)
    if not application or application.get("candidate_username") != username:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    if application.get("status") == "cancel":
        return {"status": "cancel", "application": application}

    plans = plan_repo.list_by_workflow_id(application.get("workflow_id", ""))
    if any(plan.get("status") in {"running", "finish"} for plan in plans):
        raise HTTPException(status_code=409, detail="该投递已进入面试流程，不能取消")
    for plan in plans:
        if plan.get("status") in {"pending", "wait"}:
            plan_repo.update(plan["id"], {"status": "cancel"})
    cancelled = application_repo.cancel(application_id)
    return {"status": "cancel", "application": cancelled}


@router.get("/{pid}")
async def get_plan(pid: int, _: dict = Depends(require_admin)):
    p = plan_repo.get_by_id(pid)
    if not p:
        raise HTTPException(status_code=404, detail="计划不存在")
    return _mask_password(p)


@router.post("/{pid}/reset-password")
async def reset_candidate_password(pid: int, _: dict = Depends(require_admin)):
    """重置候选人密码，返回新明文密码（仅此一次）"""
    plan = plan_repo.get_by_id(pid)
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    username = (plan.get("candidate_username") or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="该计划未绑定候选人账号")
    candidate = candidate_repo.get_candidate_info(username)
    new_password = f"IM{secrets.token_hex(4)}"
    if candidate:
        candidate_repo.reset_password(username, new_password)
    else:
        candidate_repo.register(username, new_password, plan.get("candidate_name") or username)
    plan_repo.update(pid, {"candidate_password": new_password})
    return {"candidate_username": username, "candidate_password": new_password}


@router.post("")
async def create_plan(body: PlanUpdate, _: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    resume = resume_repo.get_by_id(data.get("resume_id")) if data.get("resume_id") else resume_repo.get_by_file_path(data.get("resume_filename", ""))
    if resume and not data.get("candidate_username"):
        data["candidate_username"] = resume.get("candidate_username", "")
    username, password = _ensure_candidate_account(data)
    data["candidate_username"] = username
    data["candidate_password"] = password  # plan_repo.create 内部会 bcrypt 哈希
    if resume and not resume.get("candidate_username"):
        resume = resume_repo.update(resume["id"], {"candidate_username": username})
    workflow_id = data.get("workflow_id") or f"wf_{uuid.uuid4().hex[:10]}"
    data["workflow_id"] = workflow_id
    data["resume_id"] = (resume or {}).get("id")
    if not data.get("application_id"):
        match_result = None
        jd_id = data.get("jd_id") or (resume or {}).get("jd_id")
        if resume and jd_id:
            match_result = evaluate_resume_match(resume["id"], int(jd_id))
            data["match_score"] = int(match_result.get("total_score") or 0)
        application = application_repo.create({
            "candidate_username": username,
            "candidate_name": data.get("candidate_name", ""),
            "jd_id": jd_id,
            "jd_name": data.get("jd_name", ""),
            "resume_id": (resume or {}).get("id"),
            "match_score": data.get("match_score", 0),
            "match_details": json.dumps(match_result or {}, ensure_ascii=False),
            "recruitment_type": data.get("recruitment_type", "社招"),
            "source": "admin",
            "workflow_id": workflow_id,
        })
        data["application_id"] = application.get("id")
    plan = plan_repo.create(data)
    return {**plan, "candidate_password": password}  # 返回明文，仅此一次


@router.post("/workflow")
async def create_workflow(body: WorkflowCreate, _: dict = Depends(require_admin)):
    if not body.stages:
        raise HTTPException(status_code=400, detail="流程至少需要一个面试环节")

    workflow_id = f"wf_{uuid.uuid4().hex[:10]}"
    resume = resume_repo.get_by_id(body.resume_id) if body.resume_id else resume_repo.get_by_file_path(body.resume_filename)
    existing_owner = (resume or {}).get("candidate_username", "")
    username, password = _ensure_candidate_account({
        "candidate_name": body.candidate_name,
        "candidate_username": existing_owner,
    })
    if resume and not existing_owner:
        resume = resume_repo.update(resume["id"], {"candidate_username": username, "source": resume.get("source") or "admin"})
    candidate = candidate_repo.get_candidate_info(username) or {}
    if resume and not candidate.get("resume_filename"):
        candidate_repo.update_profile(username, {"resume_filename": resume.get("file_path", "")})
    workflow_jd_id = body.jd_id or (resume or {}).get("jd_id")
    match_result = evaluate_resume_match(resume["id"], int(workflow_jd_id)) if resume and workflow_jd_id else None
    application = application_repo.create({
        "candidate_username": username,
        "candidate_name": body.candidate_name,
        "jd_id": workflow_jd_id,
        "jd_name": body.jd_name,
        "resume_id": (resume or {}).get("id"),
        "match_score": int((match_result or {}).get("total_score") or 0),
        "match_details": json.dumps(match_result or {}, ensure_ascii=False),
        "recruitment_type": body.recruitment_type,
        "source": "admin",
        "workflow_id": workflow_id,
    })
    resume_filename = (resume or {}).get("file_path") or body.resume_filename
    match_score = int(application.get("match_score") or 0)
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
            "resume_filename": resume_filename,
            "resume_id": (resume or {}).get("id"),
            "jd_id": body.jd_id or (resume or {}).get("jd_id"),
            "application_id": application.get("id"),
            "match_score": match_score,
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
        "application": application,
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
    if data.get("candidate_username"):
        existing = candidate_repo.get_candidate_info(data["candidate_username"])
        if existing:
            return data["candidate_username"], data.get("candidate_password", "")
        if data.get("candidate_password"):
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


def _calculate_and_save_application_match(application: dict) -> dict:
    resume_id = application.get("resume_id")
    jd_id = application.get("jd_id")
    if not resume_id or not jd_id:
        return application
    result = evaluate_resume_match(int(resume_id), int(jd_id))
    score = int(result.get("total_score") or 0)
    updated = application_repo.update_match(
        int(application["id"]),
        score,
        json.dumps(result, ensure_ascii=False),
    ) or application
    for plan in plan_repo.list_by_workflow_id(application.get("workflow_id", "")):
        if int(plan.get("match_score") or 0) != score:
            plan_repo.update(plan["id"], {"match_score": score})
    return updated
