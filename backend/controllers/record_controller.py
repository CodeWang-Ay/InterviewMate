import json
import os

from fastapi import APIRouter, HTTPException

from backend.config import INTERVIEW_DIR

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("")
async def list_records(search: str = "", record_type: str = "", conclusion: str = ""):
    records = []
    if not os.path.exists(INTERVIEW_DIR):
        return records

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

        is_formal = bool(data.get("jd_filename"))
        rtype = "正式面试" if is_formal else "模拟面试"
        candidate = data.get("resume_filename", "").rsplit(".", 1)[0] if data.get("resume_filename") else "未知"
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
            "candidate": candidate,
            "position": "面试者模式",
            "type": rtype,
            "type_label": "正式面试" if is_formal else "模拟面试",
            "score": score,
            "score_display": f"{score}/100" if score is not None else "-",
            "conclusion": conclusion_label,
            "created_at": created_at,
            "state": state,
        })

    return records


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
async def delete_record(session_id: str):
    removed = False
    for suffix in (".json", "_report.json"):
        path = os.path.join(INTERVIEW_DIR, f"{session_id}{suffix}")
        if os.path.exists(path):
            os.remove(path)
            removed = True
    if not removed:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    return {"status": "ok"}
