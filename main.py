import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import UPLOAD_DIR, INTERVIEW_DIR
from backend.controllers.interview_controller import router as interview_router
from backend.controllers.chat_controller import router as chat_router
from backend.controllers.report_controller import router as report_router
from backend.controllers.jd_controller import router as jd_router
from backend.controllers.resume_controller import router as resume_router
from backend.controllers.plan_controller import router as plan_router
from backend.controllers.record_controller import router as record_router
from backend.controllers.auth_controller import router as auth_router
from backend.repositories.jd_repo import init_db as init_jd_db
from backend.repositories.resume_repo import init_db as init_resume_db
from backend.repositories.plan_repo import init_db as init_plan_db
from backend.repositories.user_repo import init_db as init_user_db

os.makedirs(os.path.join(UPLOAD_DIR, "jd"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "resume"), exist_ok=True)
os.makedirs(INTERVIEW_DIR, exist_ok=True)
init_jd_db()
init_resume_db()
init_plan_db()
init_user_db()

app = FastAPI(title="InterviewMate")

app.include_router(interview_router)
app.include_router(chat_router)
app.include_router(report_router)
app.include_router(jd_router)
app.include_router(resume_router)
app.include_router(plan_router)
app.include_router(record_router)
app.include_router(auth_router)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str = ""):  # noqa: ARG001
    return FileResponse("frontend/dist/index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
