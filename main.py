import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from backend.config import UPLOAD_DIR, INTERVIEW_DIR
from backend.controllers.interview_controller import router as interview_router
from backend.controllers.chat_controller import router as chat_router
from backend.controllers.report_controller import router as report_router
from backend.controllers.jd_controller import router as jd_router
from backend.controllers.resume_controller import router as resume_router
from backend.controllers.plan_controller import router as plan_router
from backend.controllers.record_controller import router as record_router
from backend.controllers.auth_controller import router as auth_router
from backend.controllers.interviewer_training_controller import router as interviewer_training_router
from backend.controllers.assistant_controller import router as assistant_router
from backend.controllers.ai_tools_controller import router as ai_tools_router
from backend.controllers.task_controller import router as task_router
from backend.controllers.archive_controller import router as archive_router
from backend.controllers.voice_controller import router as voice_router
from backend.repositories.admin_repo import init_db as init_admin_db
from backend.repositories.candidate_repo import init_db as init_candidate_db
from backend.repositories.jd_repo import init_db as init_jd_db
from backend.repositories.resume_repo import init_db as init_resume_db
from backend.repositories.resume_parse_cache_repo import init_db as init_resume_parse_cache_db
from backend.repositories.plan_repo import init_db as init_plan_db
from backend.repositories.task_repo import init_db as init_task_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(os.path.join(UPLOAD_DIR, "jd"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "resume"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "temp_resume"), exist_ok=True)
os.makedirs(INTERVIEW_DIR, exist_ok=True)
init_jd_db()
init_resume_db()
init_resume_parse_cache_db()
init_plan_db()
init_admin_db()
init_candidate_db()
init_task_db()

app = FastAPI(title="InterviewMate")

app.include_router(interview_router)
app.include_router(chat_router)
app.include_router(report_router)
app.include_router(jd_router)
app.include_router(resume_router)
app.include_router(plan_router)
app.include_router(record_router)
app.include_router(auth_router)
app.include_router(interviewer_training_router)
app.include_router(assistant_router)
app.include_router(ai_tools_router)
app.include_router(task_router)
app.include_router(archive_router)
app.include_router(voice_router)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

FRONTEND_DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")
FRONTEND_ASSETS_DIR = os.path.join(FRONTEND_DIST_DIR, "assets")
FRONTEND_INDEX = os.path.join(FRONTEND_DIST_DIR, "index.html")

if os.path.isdir(FRONTEND_ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str = ""):  # noqa: ARG001
    if os.path.exists(FRONTEND_INDEX):
        return FileResponse(FRONTEND_INDEX)
    return HTMLResponse(
        """
        <html>
          <head><title>InterviewMate</title></head>
          <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 40px;">
            <h2>前端还没有构建</h2>
            <p>请先在 <code>frontend</code> 目录执行 <code>npm run build</code>，然后重新启动后端服务。</p>
            <p>开发调试时也可以单独启动前端：<code>npm run dev</code>。</p>
          </body>
        </html>
        """,
        status_code=503,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
