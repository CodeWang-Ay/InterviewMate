from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.controllers.auth_controller import require_admin
from backend.repositories import jd_repo

router = APIRouter(prefix="/api/jds", tags=["jds"])


class JdCreate(BaseModel):
    name: str
    category: str = ""
    location: str = ""
    responsibilities: str = ""
    requirements: str = ""
    status: str = "enable"


class JdUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    location: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    status: str | None = None


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
