import json
import os

from fastapi import APIRouter, Depends, HTTPException

from backend.config import INTERVIEW_DIR
from backend.controllers.auth_controller import require_admin
from backend.repositories import plan_repo

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("")
async def list_records(search: str = "", record_type: str = "", conclusion: str = "", _: dict = Depends(require_admin)):
    records = []
    if not os.path.exists(INTERVIEW_DIR):
        return records

    raw_items = []
    for fname in sorted(os.listdir(INTERVIEW_DIR), reverse=True):
        if not fname.endswith(".json") or fname.endswith("_report.json"):
            continue
        fpath = os.path.join(INTERVIEW_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        session_id = data.get("session_id", fname.replace(".json", ""))

        # 读取报告获取分数
        score = None
        report_path = os.path.join(INTERVIEW_DIR, f"{session_id}_report.json")
        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                score = report.get("overall_score")
            except (json.JSONDecodeError, OSError):
                pass

        raw_items.append({
            "fname": fname,
            "session_id": session_id,
            "data": data,
            "score": score,
        })

    inferred_meta = _build_inferred_meta(raw_items)

    for item in raw_items:
        data = item["data"]
        session_id = item["session_id"]
        score = item["score"]
        meta = _resolve_record_meta(data, inferred_meta.get(session_id))
        is_formal = bool(data.get("plan_id") or data.get("jd_filename") or meta.get("jd_name"))
        rtype = "正式面试" if is_formal else "模拟面试"
        candidate = meta.get("candidate_name") or (data.get("resume_filename", "").rsplit(".", 1)[0] if data.get("resume_filename") else "未知")
        position = meta.get("jd_name") or ("面试者模式" if not is_formal else "待定岗位")
        created_at = data.get("created_at", "")
        state = data.get("state", "unknown")

        # 面试结论
        conclusion_label = _get_conclusion(score)

        # 过滤
        if search and search not in candidate:
            continue
        if record_type:
            if record_type == "formal" and not is_formal:
                continue
            if record_type == "simulate" and is_formal:
                continue
        if conclusion and conclusion_label != conclusion:
            continue

        records.append({
            "session_id": session_id,
            "plan_id": data.get("plan_id") or meta.get("plan_id"),
            "candidate": candidate,
            "position": position,
            "type": rtype,
            "type_label": "正式面试" if is_formal else "模拟面试",
            "score": score,
            "score_display": f"{score}/100" if score is not None else "-",
            "conclusion": conclusion_label,
            "created_at": created_at,
            "state": state,
            "workflow_id": meta.get("workflow_id", ""),
            "workflow_name": meta.get("workflow_name", ""),
            "stage_order": meta.get("stage_order", 1),
            "stage_count": meta.get("stage_count", 1),
            "interview_round": meta.get("interview_round", ""),
            "candidate_username": meta.get("candidate_username", ""),
        })

    return records


def _build_inferred_meta(raw_items: list[dict]) -> dict[str, dict]:
    inferred: dict[str, dict] = {}
    grouped: dict[str, list[dict]] = {}
    for item in raw_items:
        data = item["data"]
        if data.get("plan_id") or data.get("candidate_name") or not data.get("resume_filename"):
            continue
        grouped.setdefault(data["resume_filename"], []).append(item)

    for resume_filename, items in grouped.items():
        plans = plan_repo.list_by_resume_filename(resume_filename)
        if not plans:
            continue
        items.sort(key=lambda item: item["data"].get("created_at", ""))
        for index, item in enumerate(items):
            plan = plans[min(index, len(plans) - 1)]
            inferred[item["session_id"]] = {
                "plan_id": plan.get("id"),
                "candidate_name": plan.get("candidate_name", ""),
                "jd_name": plan.get("jd_name", ""),
                "workflow_id": plan.get("workflow_id", ""),
                "workflow_name": plan.get("workflow_name", ""),
                "stage_order": plan.get("stage_order", 1),
                "stage_count": plan.get("stage_count", 1),
                "interview_round": plan.get("interview_round", ""),
                "candidate_username": plan.get("candidate_username", ""),
            }
    return inferred


def _resolve_record_meta(data: dict, inferred: dict | None = None) -> dict:
    if data.get("candidate_name") or data.get("jd_name"):
        return {
            "plan_id": data.get("plan_id"),
            "candidate_name": data.get("candidate_name", ""),
            "jd_name": data.get("jd_name", ""),
            "workflow_id": data.get("workflow_id", ""),
            "workflow_name": data.get("workflow_name", ""),
            "stage_order": data.get("stage_order", 1),
            "stage_count": data.get("stage_count", 1),
            "interview_round": data.get("interview_round", ""),
            "candidate_username": data.get("candidate_username", ""),
        }
    if inferred:
        return inferred

    plan = None
    if data.get("plan_id"):
        plan = plan_repo.get_by_id(int(data["plan_id"]))
    if not plan and data.get("resume_filename"):
        plan = plan_repo.find_latest_by_resume_filename(data.get("resume_filename", ""))
    if not plan:
        return {
            "plan_id": data.get("plan_id"),
            "candidate_name": "",
            "jd_name": "",
            "workflow_id": "",
            "workflow_name": "",
            "stage_order": 1,
            "stage_count": 1,
            "interview_round": "",
            "candidate_username": "",
        }

    return {
        "plan_id": plan.get("id"),
        "candidate_name": plan.get("candidate_name", ""),
        "jd_name": plan.get("jd_name", ""),
        "workflow_id": plan.get("workflow_id", ""),
        "workflow_name": plan.get("workflow_name", ""),
        "stage_order": plan.get("stage_order", 1),
        "stage_count": plan.get("stage_count", 1),
        "interview_round": plan.get("interview_round", ""),
        "candidate_username": plan.get("candidate_username", ""),
    }


def _get_conclusion(score) -> str:
    if score is None:
        return "未知"
    if score >= 80:
        return "建议录用"
    elif score >= 60:
        return "待定观察"
    else:
        return "不予录用"


@router.delete("/{session_id}")
async def delete_record(session_id: str, _: dict = Depends(require_admin)):
    removed = False
    for suffix in (".json", "_report.json"):
        path = os.path.join(INTERVIEW_DIR, f"{session_id}{suffix}")
        if os.path.exists(path):
            os.remove(path)
            removed = True
    if not removed:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    return {"status": "ok"}
