from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.controllers.auth_controller import require_admin
from backend.repositories import jd_repo
from backend.services.jd_copilot_service import generate_jd_draft, optimize_jd_draft

router = APIRouter(prefix="/api/jds", tags=["jds"])


class JdCreate(BaseModel):
    name: str
    category: str = ""
    location: str = ""
    responsibilities: str = ""
    requirements: str = ""
    status: str = "enable"
    recruitment_type: str = "社招"
    experience_required: str = ""


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


@router.post("/generate-draft")
async def generate_jd(body: JdGenerateBody, _: dict = Depends(require_admin)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="岗位名称不能为空")
    return generate_jd_draft(
        name=body.name,
        summary=body.summary,
        category=body.category,
        location=body.location,
        recruitment_type=body.recruitment_type,
    )


@router.post("/{jd_id}/optimize-draft")
async def optimize_jd(jd_id: int, _: dict = Depends(require_admin)):
    jd = jd_repo.get_by_id(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return optimize_jd_draft(jd)


@router.put("/{jd_id}")
async def update_jd(jd_id: int, body: JdUpdate, _: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    jd = jd_repo.update(jd_id, data)
    if not jd:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return jd


@router.delete("/{jd_id}")
async def delete_jd(jd_id: int, _: dict = Depends(require_admin)):
    if not jd_repo.delete(jd_id):
        raise HTTPException(status_code=404, detail="JD 不存在")
    return {"status": "ok"}
