import json
import os

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from pydantic import BaseModel

from backend.controllers.auth_controller import require_admin
from backend.config import UPLOAD_DIR
from backend.repositories import resume_repo, upload_repo
from backend.services.file_service import parse_resume
from backend.services.resume_copilot_service import polish_resume, score_resume
from backend.models.schemas import ResumeAssistBody
from backend.utils.resume_normalizer import format_education_summary

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


class ResumeUpdate(BaseModel):
    name: str | None = None
    target_position: str | None = None
    education: str | None = None
    experience_years: str | None = None
    skills: str | None = None
    parse_status: str | None = None
    structured_data: str | None = None
    jd_id: int | None = None
    jd_name: str | None = None


@router.get("")
async def list_resumes(search: str = "", parse_status: str = "", experience_years: str = "", _: dict = Depends(require_admin)):
    return resume_repo.list_all(search, parse_status, experience_years)


@router.get("/{rid}")
async def get_resume(rid: int, _: dict = Depends(require_admin)):
    r = resume_repo.get_by_id(rid)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    return r


@router.post("/upload")
async def upload_resume_file(file: UploadFile = File(...), jd_id: int = Form(0), _: dict = Depends(require_admin)):
    ext = upload_repo.validate(file)
    filename = await upload_repo.save(file, "resume", ext)
    jd_name = ""
    if jd_id > 0:
        from backend.repositories import jd_repo as jdr
        jd = jdr.get_by_id(jd_id)
        if jd:
            jd_name = jd.get("name", "")
    resume = resume_repo.create({
        "name": os.path.splitext(file.filename or "unknown")[0],
        "file_path": filename,
        "file_type": ext.lstrip("."),
        "parse_status": "wait",
        "jd_id": jd_id if jd_id > 0 else None,
        "jd_name": jd_name,
        "original_name": file.filename or "",
    })
    return resume


@router.put("/{rid}")
async def update_resume(rid: int, body: ResumeUpdate, _: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    r = resume_repo.update(rid, data)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    return r


@router.get("/{rid}/raw")
async def get_resume_raw(rid: int, _: dict = Depends(require_admin)):
    r = resume_repo.get_by_id(rid)
    if not r or not r.get("file_path"):
        raise HTTPException(status_code=404, detail="无文件内容")
    fpath = os.path.join(UPLOAD_DIR, "resume", r["file_path"])
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="文件不存在")
    try:
        from backend.repositories.upload_repo import read_text
        text = read_text("resume", r["file_path"])
        return {"raw": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {e}")


@router.delete("/{rid}")
async def delete_resume(rid: int, _: dict = Depends(require_admin)):
    r = resume_repo.get_by_id(rid)
    if r:
        fp = r.get("file_path")
        if fp:
            fpath = os.path.join(UPLOAD_DIR, "resume", fp)
            if os.path.exists(fpath):
                os.remove(fpath)
    if not resume_repo.delete(rid):
        raise HTTPException(status_code=404, detail="简历不存在")
    return {"status": "ok"}


@router.post("/{rid}/parse")
async def parse_resume_api(rid: int, _: dict = Depends(require_admin)):
    r = resume_repo.get_by_id(rid)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    file_path = r.get("file_path")
    if not file_path:
        raise HTTPException(status_code=400, detail="简历未关联文件")

    try:
        result = await parse_resume(file_path)
        structured = result["structured"]
        resume_repo.update(rid, {
            "name": structured.get("基础信息", {}).get("姓名") or r["name"],
            "target_position": structured.get("基础信息", {}).get("意向岗位") or "",
            "education": format_education_summary(structured.get("教育经历", [])),
            "skills": _extract_skills(result["raw"]),
            "parse_status": "success",
            "structured_data": json.dumps(structured, ensure_ascii=False),
        })
        return {"status": "ok", "structured": structured}
    except Exception as e:
        resume_repo.update(rid, {"parse_status": "fail"})
        raise HTTPException(status_code=500, detail=f"解析失败: {e}")


@router.post("/{rid}/score")
async def score_resume_api(rid: int, body: ResumeAssistBody | None = None, _: dict = Depends(require_admin)):
    try:
        return await score_resume(rid, body.jd_id if body else None)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"简历评估失败: {exc}") from exc


@router.post("/{rid}/polish")
async def polish_resume_api(rid: int, body: ResumeAssistBody | None = None, _: dict = Depends(require_admin)):
    try:
        mode = body.mode if body else "jd"
        jd_id = body.jd_id if body else None
        return await polish_resume(rid, jd_id, mode)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"简历润色失败: {exc}") from exc


def _extract_skills(text: str) -> str:
    """简单提取技术关键词"""
    import re
    keywords = ["Java", "Python", "Go", "C++", "TypeScript", "React", "Vue", "Node", "SpringBoot",
                "MySQL", "Redis", "Docker", "Kubernetes", "AWS", "PyTorch", "NLP", "LLM"]
    found = [k for k in keywords if re.search(re.escape(k), text, re.IGNORECASE)]
    return ", ".join(found[:8]) if found else ""
