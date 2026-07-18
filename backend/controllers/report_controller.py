from fastapi import APIRouter, Depends

from backend.controllers.auth_controller import require_admin
from backend.repositories.interview_repo import load_record, load_report
from backend.services.report_service import generate_report

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{session_id}")
async def get_report(session_id: str, _: dict = Depends(require_admin)):
    existing = load_report(session_id)
    if existing:
        return _enrich_report(session_id, existing)
    return generate_report(session_id)


def _enrich_report(session_id: str, report: dict) -> dict:
    try:
        record = load_record(session_id)
    except Exception:
        return report
    enriched = dict(report)
    for key in (
        "candidate_name",
        "jd_name",
        "interview_round",
        "workflow_name",
        "workflow_id",
        "candidate_username",
        "resume_name",
    ):
        if not enriched.get(key) and record.get(key):
            enriched[key] = record.get(key)
    if not enriched.get("history") and record.get("history"):
        enriched["history"] = record.get("history")
    return enriched
