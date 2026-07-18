from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.controllers.auth_controller import require_admin
from backend.repositories import jd_repo
from backend.services.jd_copilot_service import generate_jd_draft, optimize_jd_draft
from backend.services.task_service import create_task

router = APIRouter(prefix="/api/jds", tags=["jds"])


class JdCreate(BaseModel):
    name: str
    category: str = ""
    location: str = ""
    responsibilities: str = ""
    requirements: str = ""
    status: str = "enable"
    recruitment_type: str = "社招"
    experience_required: str = "不限经验"


class JdUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    location: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    status: str | None = None
    recruitment_type: str | None = None
    experience_required: str | None = None


class JdGenerateBody(BaseModel):
    name: str
    summary: str = ""
    category: str = ""
    location: str = ""
    recruitment_type: str = "社招"


@router.get("/stats")
async def jd_stats(_: dict = Depends(require_admin)):
    return jd_repo.get_stats()


@router.get("")
async def list_jds(category: str = "", status: str = "", location: str = "", search: str = "", recruitment_type: str = "", page: int = 1, page_size: int = 10, _: dict = Depends(require_admin)):
    items, total = jd_repo.list_all_paged(category, status, location, search, recruitment_type, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{jd_id}")
async def get_jd(jd_id: int, _: dict = Depends(require_admin)):
    jd = jd_repo.get_by_id(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return jd


@router.post("")
async def create_jd(body: JdCreate, _: dict = Depends(require_admin)):
    return jd_repo.create(body.model_dump())


@router.post("/{jd_id}/duplicate")
async def duplicate_jd(jd_id: int, _: dict = Depends(require_admin)):
    jd = jd_repo.duplicate(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return jd


@router.post("/generate-draft")
async def generate_jd(body: JdGenerateBody, _: dict = Depends(require_admin)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="岗位名称不能为空")
    return await generate_jd_draft(
        name=body.name,
        summary=body.summary,
        category=body.category,
        location=body.location,
        recruitment_type=body.recruitment_type,
    )


@router.post("/generate-task")
async def generate_jd_task(body: JdGenerateBody, admin: dict = Depends(require_admin)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="岗位名称不能为空")

    async def runner():
        return await generate_jd_draft(
            name=body.name,
            summary=body.summary,
            category=body.category,
            location=body.location,
            recruitment_type=body.recruitment_type,
        )

    return create_task("jd_generate", f"生成 JD：{body.name}", {"kind": "admin", "username": admin.get("username", "")}, runner)


@router.post("/{jd_id}/optimize-draft")
async def optimize_jd(jd_id: int, _: dict = Depends(require_admin)):
    jd = jd_repo.get_by_id(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return await optimize_jd_draft(jd)


@router.post("/{jd_id}/optimize-task")
async def optimize_jd_task(jd_id: int, admin: dict = Depends(require_admin)):
    jd = jd_repo.get_by_id(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="JD 不存在")

    async def runner():
        return await optimize_jd_draft(jd)

    return create_task("jd_optimize", f"优化 JD：{jd.get('name', jd_id)}", {"kind": "admin", "username": admin.get("username", "")}, runner)


@router.get("/{jd_id}/versions")
async def list_jd_versions(jd_id: int, _: dict = Depends(require_admin)):
    jd = jd_repo.get_by_id(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return jd_repo.list_versions(jd_id)


@router.post("/{jd_id}/versions/{version_id}/restore")
async def restore_jd_version(jd_id: int, version_id: int, _: dict = Depends(require_admin)):
    jd = jd_repo.restore_version(jd_id, version_id)
    if not jd:
        raise HTTPException(status_code=404, detail="版本不存在")
    return jd


@router.put("/{jd_id}")
async def update_jd(jd_id: int, body: JdUpdate, source: str = "manual", _: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    jd = jd_repo.update(jd_id, data, source=source)
    if not jd:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return jd


@router.delete("/{jd_id}")
async def delete_jd(jd_id: int, _: dict = Depends(require_admin)):
    if not jd_repo.delete(jd_id):
        raise HTTPException(status_code=404, detail="JD 不存在")
    return {"status": "ok"}
