from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.controllers.auth_controller import require_admin
from backend.repositories import upload_repo
from backend.services.llm_service import extract_resume_info
from backend.services.resume_copilot_service import polish_resume_text, score_resume_text

router = APIRouter(prefix="/api/ai-tools", tags=["ai-tools"])


def _parse_temp_resume(filename: str) -> dict:
    raw = upload_repo.read_text("temp_resume", filename)
    structured = extract_resume_info(raw)
    return {"raw": raw, "structured": structured}


@router.post("/resume/score")
async def ai_resume_score(
    file: UploadFile = File(...),
    jd_id: int | None = Form(None),
    _: dict = Depends(require_admin),
):
    try:
        ext = upload_repo.validate(file)
        filename = await upload_repo.save(file, "temp_resume", ext)
        parsed = _parse_temp_resume(filename)
        result = score_resume_text(file.filename or filename, parsed["raw"], parsed["structured"], jd_id)
        return {
            "filename": file.filename or filename,
            "raw": parsed["raw"],
            "structured": parsed["structured"],
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"简历评估失败: {exc}") from exc


@router.post("/resume/polish")
async def ai_resume_polish(
    file: UploadFile = File(...),
    jd_id: int | None = Form(None),
    mode: str = Form("jd"),
    _: dict = Depends(require_admin),
):
    try:
        ext = upload_repo.validate(file)
        filename = await upload_repo.save(file, "temp_resume", ext)
        parsed = _parse_temp_resume(filename)
        result = polish_resume_text(file.filename or filename, parsed["raw"], parsed["structured"], jd_id, mode)
        return {
            "filename": file.filename or filename,
            "raw": parsed["raw"],
            "structured": parsed["structured"],
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"简历润色失败: {exc}") from exc
