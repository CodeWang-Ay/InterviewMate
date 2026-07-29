import json
import os
from collections import defaultdict

from fastapi import APIRouter, Depends

from backend.config import INTERVIEW_DIR
from backend.controllers.auth_controller import require_admin
from backend.repositories import plan_repo

router = APIRouter(prefix="/api/archives", tags=["archives"])


@router.get("")
async def list_archives(search: str = "", _: dict = Depends(require_admin)):
    plans = plan_repo.list_all(search=search)
    records = _load_records()
    groups: dict[str, dict] = {}

    for plan in plans:
        key = _group_key(plan)
        group = groups.setdefault(key, _empty_group(key, plan))
        group["plans"].append(plan)

    for record in records:
        key = record.get("workflow_id") or (f"user:{record.get('candidate_username')}" if record.get("candidate_username") else "")
        if not key:
            key = f"candidate:{record.get('candidate_name') or record.get('resume_name') or '未知'}:{record.get('jd_name') or '待定岗位'}"
        if search and search not in (record.get("candidate_name") or record.get("resume_name") or "") and search not in (record.get("jd_name") or ""):
            continue
        group = groups.setdefault(key, _empty_group(key, record))
        group["records"].append(record)

    result = [_summarize_group(group) for group in groups.values()]
    return sorted(result, key=lambda item: item.get("latest_at", ""), reverse=True)


@router.get("/detail")
async def archive_detail(
    workflow_id: str = "",
    candidate_username: str = "",
    candidate: str = "",
    _: dict = Depends(require_admin),
):
    plans = []
    if workflow_id:
        plans = plan_repo.list_by_workflow_id(workflow_id)
    elif candidate_username:
        plans = plan_repo.list_by_candidate_username_group(candidate_username)
    else:
        plans = [p for p in plan_repo.list_all(search=candidate) if not candidate or p.get("candidate_name") == candidate]

    keys = {_group_key(plan) for plan in plans}
    records = []
    for record in _load_records():
        record_key = record.get("workflow_id") or (f"user:{record.get('candidate_username')}" if record.get("candidate_username") else "")
        candidate_match = candidate and candidate in (record.get("candidate_name") or record.get("resume_name") or "")
        if record_key in keys or (candidate_match and not keys):
            records.append(record)

    seed = plans[0] if plans else (records[0] if records else {})
    group = _empty_group(next(iter(keys), ""), seed)
    group["plans"] = plans
    group["records"] = records
    return _summarize_group(group, include_detail=True)


def _group_key(item: dict) -> str:
    if item.get("workflow_id"):
        return item["workflow_id"]
    if item.get("candidate_username"):
        return f"user:{item['candidate_username']}"
    return f"candidate:{item.get('candidate_name') or item.get('candidate') or '未知'}:{item.get('jd_name') or item.get('position') or '待定岗位'}"


def _empty_group(key: str, seed: dict) -> dict:
    return {
        "key": key,
        "workflow_id": seed.get("workflow_id", ""),
        "workflow_name": seed.get("workflow_name", "") or "单轮面试",
        "candidate_name": seed.get("candidate_name") or seed.get("candidate") or seed.get("resume_name") or "未知候选人",
        "candidate_username": seed.get("candidate_username", ""),
        "jd_name": seed.get("jd_name") or seed.get("position") or "待定岗位",
        "plans": [],
        "records": [],
    }


def _summarize_group(group: dict, include_detail: bool = False) -> dict:
    plans = sorted(group["plans"], key=lambda p: (int(p.get("stage_order") or 1), int(p.get("id") or 0)))
    records = sorted(group["records"], key=lambda r: r.get("created_at", ""), reverse=True)
    stage_total = max([int(p.get("stage_count") or 1) for p in plans] + [len(plans), 1])
    finished = len([p for p in plans if p.get("status") == "finish"])
    scores = [r.get("report", {}).get("overall_score") for r in records if r.get("report", {}).get("overall_score") is not None]
    latest_at = max([p.get("created_at", "") for p in plans] + [r.get("created_at", "") for r in records] + [""])
    item = {
        "key": group["key"],
        "workflow_id": group["workflow_id"],
        "workflow_name": group["workflow_name"],
        "candidate_name": group["candidate_name"],
        "candidate_username": group["candidate_username"],
        "jd_name": group["jd_name"],
        "stage_total": stage_total,
        "finished_stages": finished,
        "record_count": len(records),
        "report_count": len(scores),
        "avg_score": round(sum(scores) / len(scores)) if scores else None,
        "latest_at": latest_at,
        "current_status": _group_status(plans),
    }
    if include_detail:
        item["plans"] = plans
        item["records"] = records
    return item


def _group_status(plans: list[dict]) -> str:
    if not plans:
        return "no_plan"
    if all(p.get("status") == "finish" for p in plans):
        return "finish"
    if any(p.get("status") == "running" for p in plans):
        return "running"
    if any(p.get("status") == "wait" for p in plans):
        return "wait"
    if any(p.get("status") == "finish" for p in plans):
        return "partial"
    return "pending"


def _load_records() -> list[dict]:
    if not os.path.exists(INTERVIEW_DIR):
        return []
    items = []
    for fname in os.listdir(INTERVIEW_DIR):
        if not fname.endswith(".json") or fname.endswith("_report.json"):
            continue
        path = os.path.join(INTERVIEW_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                record = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if str(record.get("workflow_id") or "").startswith("apply_"):
            continue
        session_id = record.get("session_id") or fname.replace(".json", "")
        report_path = os.path.join(INTERVIEW_DIR, f"{session_id}_report.json")
        report = {}
        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
            except (OSError, json.JSONDecodeError):
                report = {}
        record["session_id"] = session_id
        record["report"] = report
        items.append(record)
    return items
