import os
import uuid

from fastapi import UploadFile, HTTPException

from backend.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE


def validate(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


async def save(file: UploadFile, subdir: str, ext: str) -> str:
    content = await file.read()
    return save_content(content, file.filename or "unknown", subdir, ext)


def save_content(content: bytes, original_filename: str, subdir: str, ext: str) -> str:
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")
    original = (original_filename or "unknown").rsplit(".", 1)[0]
    filename = f"{original}_{uuid.uuid4().hex[:6]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, subdir, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filename


def save_text(content: str, subdir: str) -> str:
    filename = f"{uuid.uuid4().hex}.txt"
    filepath = os.path.join(UPLOAD_DIR, subdir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


def read_text(subdir: str, filename: str) -> str:
    filepath = os.path.join(UPLOAD_DIR, subdir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")
    if filename.endswith((".txt", ".md")):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    elif filename.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        pdf_content = "\n".join(page.extract_text() or "" for page in reader.pages)
        return pdf_content
    elif filename.endswith(".docx"):
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise HTTPException(status_code=400, detail=f"无法读取格式: {os.path.splitext(filename)[1]}")
