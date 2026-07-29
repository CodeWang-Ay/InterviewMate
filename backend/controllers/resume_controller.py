import hashlib
import json
import os
import sqlite3

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.controllers.auth_controller import require_admin
from backend.config import UPLOAD_DIR
from backend.repositories import application_repo, candidate_repo, plan_repo, resume_parse_cache_repo, resume_repo, upload_repo
from backend.services.file_service import parse_resume
from backend.services.resume_copilot_service import polish_resume, score_resume
from backend.services.task_service import create_task
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
    candidate_status: str | None = None
    structured_data: str | None = None
    jd_id: int | None = None
    jd_name: str | None = None


@router.get("")
async def list_resumes(
    search: str = "",
    parse_status: str = "",
    experience_years: str = "",
    candidate_status: str = "",
    source: str = "",
    page: int | None = None,
    page_size: int | None = None,
    _: dict = Depends(require_admin),
):
    if page is not None or page_size is not None:
        current_page = page or 1
        current_page_size = page_size or 10
        items, total = resume_repo.list_management_paged(
            search,
            parse_status,
            experience_years,
            candidate_status,
            source,
            current_page,
            current_page_size,
        )
        return {"items": items, "total": total, "page": current_page, "page_size": current_page_size}
    return resume_repo.list_all(search, parse_status, experience_years, candidate_status, source)


@router.get("/{rid}")
async def get_resume(rid: int, _: dict = Depends(require_admin)):
    r = resume_repo.get_by_id(rid)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    return r


@router.post("/upload")
async def upload_resume_file(file: UploadFile = File(...), jd_id: int = Form(0), allow_duplicate: bool = Form(False), _: dict = Depends(require_admin)):
    ext = upload_repo.validate(file)
    content = await file.read()
    file_md5 = hashlib.md5(content).hexdigest()
    duplicates = resume_repo.find_duplicates(file_md5)
    if duplicates and not allow_duplicate:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "检测到重复简历",
                "duplicates": [_public_duplicate(item) for item in duplicates],
            },
        )
    filename = upload_repo.save_content(content, file.filename or "unknown", "resume", ext)
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
        "candidate_status": "待筛选",
        "jd_id": jd_id if jd_id > 0 else None,
        "jd_name": jd_name,
        "original_name": file.filename or "",
        "file_md5": file_md5,
        "source": "admin",
    })
    if duplicates:
        resume["duplicate_of"] = [_public_duplicate(item) for item in duplicates]
    return resume


@router.put("/{rid}")
async def update_resume(
    rid: int,
    body: ResumeUpdate,
    application_id: int = Query(0),
    _: dict = Depends(require_admin),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if application_id and "candidate_status" in data:
        application = application_repo.get_by_id(application_id)
        if not application or int(application.get("resume_id") or 0) != rid:
            raise HTTPException(status_code=404, detail="投递记录不存在或未关联当前简历")
        screening_status = data.pop("candidate_status")
        try:
            updated_application = application_repo.update_screening(application_id, screening_status)
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                raise HTTPException(status_code=503, detail="数据库正在处理其他操作，请稍后重试") from exc
            raise
        if not data:
            resume = resume_repo.get_by_id(rid) or {}
            return {
                **resume,
                "application_id": application_id,
                "application_status": (updated_application or {}).get("status", ""),
                "candidate_status": (updated_application or {}).get("screening_status", screening_status),
                "jd_id": (updated_application or {}).get("jd_id"),
                "jd_name": (updated_application or {}).get("jd_name", ""),
                "record_key": f"application:{application_id}",
            }
    try:
        r = resume_repo.update(rid, data)
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            raise HTTPException(status_code=503, detail="数据库正在处理其他操作，请稍后重试") from exc
        raise
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


@router.get("/{rid}/download")
async def download_resume_file(rid: int, _: dict = Depends(require_admin)):
    r = resume_repo.get_by_id(rid)
    if not r or not r.get("file_path"):
        raise HTTPException(status_code=404, detail="无文件内容")
    fpath = os.path.join(UPLOAD_DIR, "resume", r["file_path"])
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="文件不存在")
    filename = r.get("original_name") or r.get("file_path") or "resume"
    return FileResponse(fpath, filename=filename, media_type="application/octet-stream")


@router.delete("/{rid}")
async def delete_resume(rid: int, _: dict = Depends(require_admin)):
    r = resume_repo.get_by_id(rid)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    applications = application_repo.list_by_resume_id(rid)
    if applications:
        raise HTTPException(status_code=409, detail=f"该简历已关联 {len(applications)} 条投递记录，不能直接删除")
    if r:
        fp = r.get("file_path")
        if fp:
            fpath = os.path.join(UPLOAD_DIR, "resume", fp)
            if os.path.exists(fpath):
                os.remove(fpath)
        username = r.get("candidate_username") or ""
        candidate = candidate_repo.get_candidate_info(username) if username else None
        if candidate and candidate.get("resume_filename") == fp:
            candidate_repo.update_profile(username, {"resume_filename": ""})
    if not resume_repo.delete(rid):
        raise HTTPException(status_code=404, detail="简历不存在")
    return {"status": "ok"}


@router.post("/{rid}/parse")
async def parse_resume_api(rid: int, force: bool = Query(False), _: dict = Depends(require_admin)):
    try:
        return await _parse_resume_record(rid, force)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        resume_repo.update(rid, {"parse_status": "fail"})
        raise HTTPException(status_code=500, detail=f"解析失败: {e}") from e


@router.post("/{rid}/parse-task")
async def parse_resume_task(rid: int, force: bool = Query(False), admin: dict = Depends(require_admin)):
    r = resume_repo.get_by_id(rid)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    title = f"解析简历：{r.get('original_name') or r.get('name') or rid}"

    async def runner():
        return await _parse_resume_record(rid, force)

    return create_task("resume_parse", title, {"kind": "admin", "username": admin.get("username", "")}, runner)


async def _parse_resume_record(rid: int, force: bool = False) -> dict:
    r = resume_repo.get_by_id(rid)
    if not r:
        raise FileNotFoundError("简历不存在")
    file_path = r.get("file_path")
    if not file_path:
        raise ValueError("简历未关联文件")
    abs_path = os.path.join(UPLOAD_DIR, "resume", file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError("文件不存在")

    file_md5 = _file_md5(abs_path)
    if not force:
        cached = resume_parse_cache_repo.get(file_md5)
        if cached:
            structured = json.loads(cached.get("structured_data") or "{}")
            resume_repo.update(rid, {
                "name": cached.get("name") or r["name"],
                "target_position": cached.get("target_position") or "",
                "education": cached.get("education") or "",
                "skills": cached.get("skills") or "",
                "parse_status": "success",
                "structured_data": cached.get("structured_data") or "{}",
            })
            return {"status": "ok", "structured": structured, "cache_hit": True, "resume": resume_repo.get_by_id(rid)}

    result = await parse_resume(file_path)
    structured = result["structured"]
    update_data = _build_resume_parse_update(r, structured, result["raw"])
    resume_repo.update(rid, update_data)
    resume_parse_cache_repo.upsert({
        "file_md5": file_md5,
        "original_name": r.get("original_name") or file_path,
        "file_size": os.path.getsize(abs_path),
        "raw_text": result["raw"],
        "structured_data": update_data["structured_data"],
        "name": update_data["name"],
        "target_position": update_data["target_position"],
        "education": update_data["education"],
        "skills": update_data["skills"],
    })
    return {"status": "ok", "structured": structured, "cache_hit": False, "resume": resume_repo.get_by_id(rid)}


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


def _file_md5(path: str) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _public_duplicate(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name", ""),
        "target_position": item.get("target_position", ""),
        "jd_name": item.get("jd_name", ""),
        "original_name": item.get("original_name") or item.get("file_path", ""),
        "created_at": item.get("created_at", ""),
    }


def _build_resume_parse_update(resume: dict, structured: dict, raw: str) -> dict:
    return {
        "name": structured.get("基础信息", {}).get("姓名") or resume["name"],
        "target_position": structured.get("基础信息", {}).get("意向岗位") or "",
        "education": format_education_summary(structured.get("教育经历", [])),
        "skills": _extract_skills(raw),
        "parse_status": "success",
        "structured_data": json.dumps(structured, ensure_ascii=False),
    }
