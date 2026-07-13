from fastapi import APIRouter, Depends

from backend.controllers.auth_controller import require_admin
from backend.repositories.interview_repo import load_report
from backend.services.report_service import generate_report

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{session_id}")
async def get_report(session_id: str, _: dict = Depends(require_admin)):
    existing = load_report(session_id)
    if existing:
        return existing
    return generate_report(session_id)
