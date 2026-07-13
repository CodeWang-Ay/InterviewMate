import json
import os
from datetime import datetime

from fastapi import HTTPException

from backend.config import INTERVIEW_DIR, chat_sessions


def save_record(session_id: str):
    session = chat_sessions.get(session_id)
    if not session:
        return
    candidate_name = ""
    jd_name = ""
    interview_round = ""
    workflow_name = ""
    workflow_id = ""
    stage_order = 1
    stage_count = 1
    candidate_username = ""
    plan_id = session.get("plan_id")
    if plan_id:
        try:
            from backend.repositories import plan_repo
            plan = plan_repo.get_by_id(plan_id)
            if plan:
                candidate_name = plan.get("candidate_name", "")
                jd_name = plan.get("jd_name", "")
                interview_round = plan.get("interview_round", "")
                workflow_name = plan.get("workflow_name", "")
                workflow_id = plan.get("workflow_id", "")
                stage_order = plan.get("stage_order", 1)
                stage_count = plan.get("stage_count", 1)
                candidate_username = plan.get("candidate_username", "")
        except Exception:
            pass
    record = {
        "session_id": session_id,
        "plan_id": plan_id,
        "candidate_name": candidate_name,
        "jd_name": jd_name,
        "interview_round": interview_round,
        "workflow_name": workflow_name,
        "workflow_id": workflow_id,
        "stage_order": stage_order,
        "stage_count": stage_count,
        "candidate_username": candidate_username,
        "jd_filename": session.get("jd_filename"),
        "resume_filename": session.get("resume_filename"),
        "questions": session.get("questions", []),
        "state": session.get("state"),
        "question_index": session.get("question_index", 0),
        "history": session.get("history", []),
        "created_at": session.get("created_at"),
        "updated_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat() if session.get("state") == "COMPLETED" else None,
    }
    filepath = os.path.join(INTERVIEW_DIR, f"{session_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    print(f"[会话 {session_id}] 记录已保存到 {filepath}")


def load_record(session_id: str) -> dict:
    filepath = os.path.join(INTERVIEW_DIR, f"{session_id}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="面试记录不存在")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_record_if_exists(session_id: str) -> dict | None:
    filepath = os.path.join(INTERVIEW_DIR, f"{session_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def restore_session(session_id: str) -> dict | None:
    if session_id in chat_sessions:
        return chat_sessions[session_id]
    record = load_record_if_exists(session_id)
    if not record or record.get("state") == "COMPLETED":
        return None
    chat_sessions[session_id] = {
        "jd_filename": record.get("jd_filename", ""),
        "resume_filename": record.get("resume_filename", ""),
        "plan_id": record.get("plan_id"),
        "state": record.get("state", "READY_CHECK"),
        "question_index": record.get("question_index", 0),
        "questions": record.get("questions", []),
        "history": record.get("history", []),
        "created_at": record.get("created_at"),
    }
    return chat_sessions[session_id]


def save_report(session_id: str, report: dict):
    filepath = os.path.join(INTERVIEW_DIR, f"{session_id}_report.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[会话 {session_id}] 面试报告已生成")


def load_report(session_id: str) -> dict | None:
    filepath = os.path.join(INTERVIEW_DIR, f"{session_id}_report.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
