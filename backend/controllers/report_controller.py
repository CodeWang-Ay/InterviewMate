from fastapi import APIRouter, Depends, HTTPException

from backend.controllers.auth_controller import get_current_identity
from backend.repositories.interview_repo import load_record, load_report
from backend.repositories import plan_repo
from backend.services.report_service import generate_report

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{session_id}")
async def get_report(session_id: str, identity: dict = Depends(get_current_identity)):
    _ensure_report_access(session_id, identity)
    existing = load_report(session_id)
    if existing:
        return _enrich_report(session_id, existing)
    return generate_report(session_id)


def _ensure_report_access(session_id: str, identity: dict) -> None:
    if identity["kind"] == "admin":
        return
    try:
        record = load_record(session_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="面试记录不存在") from exc
    plan_id = record.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=403, detail="无权访问该报告")
    plan = plan_repo.get_by_id(int(plan_id))
    if not plan or plan.get("candidate_username") != identity["username"]:
        raise HTTPException(status_code=403, detail="无权访问该报告")


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
        "interviewer",
        "scheduled_at",
        "stage_order",
        "stage_count",
    ):
        if not enriched.get(key) and record.get(key):
            enriched[key] = record.get(key)
    plan_id = record.get("plan_id")
    if plan_id:
        plan = plan_repo.get_by_id(int(plan_id))
        if plan:
            for key in ("interviewer", "scheduled_at", "interview_round", "stage_order", "stage_count"):
                if not enriched.get(key) and plan.get(key):
                    enriched[key] = plan.get(key)
    if not enriched.get("history") and record.get("history"):
        enriched["history"] = record.get("history")
    return enriched
