import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="InterviewMate")


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


# 生产模式：挂载前端构建产物
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """所有非 API 路由返回前端 index.html（SPA fallback）"""
    return FileResponse("frontend/dist/index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
