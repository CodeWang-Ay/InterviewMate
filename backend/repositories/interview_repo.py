import json
import os
from datetime import datetime

from fastapi import HTTPException

from backend.config import INTERVIEW_DIR, chat_sessions


def save_record(session_id: str):
    session = chat_sessions.get(session_id)
    if not session:
        return
    record = {
        "session_id": session_id,
        "jd_filename": session.get("jd_filename"),
        "resume_filename": session.get("resume_filename"),
        "questions": session.get("questions", []),
        "state": session.get("state"),
        "question_index": session.get("question_index", 0),
        "history": session.get("history", []),
        "created_at": session.get("created_at"),
        "completed_at": datetime.now().isoformat(),
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
