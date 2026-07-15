import json

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from backend.controllers.auth_controller import require_admin
from backend.models.schemas import JDContent, ResumeParse, PlanGenerate
from backend.repositories.upload_repo import validate, save, save_text
from backend.services.file_service import parse_resume, read_jd, extract_questions_from_jd

router = APIRouter(prefix="/api", tags=["interview"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/save/jd")
async def save_jd(body: JDContent, _: dict = Depends(require_admin)):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="JD 内容不能为空")
    filename = save_text(body.content, "jd")
    return {"filename": filename, "status": "ok"}


@router.post("/upload/resume")
async def upload_resume(file: UploadFile = File(...), _: dict = Depends(require_admin)):
    ext = validate(file)
    filename = await save(file, "resume", ext)
    return {"filename": filename, "original_name": file.filename, "status": "ok"}


@router.post("/parse/resume")
async def api_parse_resume(body: ResumeParse, _: dict = Depends(require_admin)):
    result = await parse_resume(body.resume_filename)
    print("=" * 60)
    print("【简历解析结果】")
    print(result["raw"][:500])
    print("【结构化信息】")
    print(json.dumps(result["structured"], ensure_ascii=False, indent=2))
    print("=" * 60)
    return {"resume": result["raw"], "structured": result["structured"]}


@router.post("/generate/plan")
async def generate_plan(body: PlanGenerate, _: dict = Depends(require_admin)):
    jd_text = read_jd(body.jd_filename)
    result = await parse_resume(body.resume_filename)
    resume_text = result["raw"]

    questions = extract_questions_from_jd(jd_text)
    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    plan = (
        "【面试岗位】\n根据 JD 描述分析，本面试针对的岗位要求如下：\n"
        "（请根据下方 JD 内容确认岗位核心需求）\n\n"
        "【候选人背景摘要】\n根据简历内容，候选人的背景如下：\n"
        "（请根据下方简历内容确认候选人核心经历）\n\n"
        "【建议面试问题】\n" + questions_text + "\n\n"
        + "=" * 60 + "\n【岗位 JD】\n" + jd_text + "\n"
        + "=" * 60 + "\n【个人简历】\n" + resume_text + "\n"
        + "=" * 60 + "\n"
    )

    print("=" * 60)
    print("【面试计划】")
    print(plan)
    print("=" * 60)

    return {"plan": plan}
