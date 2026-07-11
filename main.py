import os
import uuid
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="InterviewMate")

# 允许的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(os.path.join(UPLOAD_DIR, "jd"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "resume"), exist_ok=True)


def validate_file(file: UploadFile) -> str:
    """校验文件，返回扩展名"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


async def save_file(file: UploadFile, subdir: str, ext: str) -> str:
    """保存文件，返回保存后的文件名"""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, subdir, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filename


class JDContent(BaseModel):
    content: str


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/save/jd")
async def save_jd(body: JDContent):
    """保存岗位 JD（文本格式）"""
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="JD 内容不能为空")
    filename = f"{uuid.uuid4().hex}.txt"
    filepath = os.path.join(UPLOAD_DIR, "jd", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(body.content)
    return {"filename": filename, "status": "ok"}


@app.post("/api/upload/resume")
async def upload_resume(file: UploadFile = File(...)):
    """上传个人简历"""
    ext = validate_file(file)
    filename = await save_file(file, "resume", ext)
    return {"filename": filename, "original_name": file.filename, "status": "ok"}


# 生产模式：挂载前端构建产物
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str = ""):  # noqa: ARG001
    """所有非 API 路由返回前端 index.html（SPA fallback）"""
    return FileResponse("frontend/dist/index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
