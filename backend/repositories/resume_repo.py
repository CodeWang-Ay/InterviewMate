import os
import sqlite3
from datetime import datetime

from backend.config import DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT '',
                target_position TEXT DEFAULT '',
                education TEXT DEFAULT '',
                experience_years TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                file_path TEXT DEFAULT '',
                file_type TEXT DEFAULT '',
                parse_status TEXT DEFAULT 'wait',
                structured_data TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cnt = conn.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        if cnt == 0:
            samples = [
                ("李明", "后端开发工程师", "本科", "3年", "Java, SpringBoot, MySQL, Redis, 微服务", "", "", "success"),
                ("王小雨", "前端开发工程师", "硕士", "2年", "Vue3, TypeScript, Vite, ElementPlus, Axios", "", "", "success"),
                ("张伟", "算法工程师", "硕士", "5年", "Python, PyTorch, NLP, LLM", "张伟_算法.pdf", "pdf", "wait"),
                ("陈琳", "测试工程师", "本科", "4年", "Selenium, JMeter, Python", "陈琳_测试.docx", "docx", "fail"),
            ]
            conn.executemany(
                "INSERT INTO resumes (name, target_position, education, experience_years, skills, file_path, file_type, parse_status) VALUES (?,?,?,?,?,?,?,?)",
                samples,
            )


def list_all(search: str = "", parse_status: str = "", experience_years: str = "") -> list[dict]:
    sql = "SELECT * FROM resumes WHERE 1=1"
    params = []
    if parse_status:
        sql += " AND parse_status=?"
        params.append(parse_status)
    if experience_years:
        sql += " AND experience_years=?"
        params.append(experience_years)
    if search:
        sql += " AND (name LIKE ? OR skills LIKE ? OR target_position LIKE ?)"
        p = f"%{search}%"
        params.extend([p, p, p])
    sql += " ORDER BY id DESC"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_by_id(rid: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE id=?", (rid,)).fetchone()
        return dict(row) if row else None


def create(data: dict) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO resumes (name, target_position, education, experience_years, skills, file_path, file_type, parse_status) VALUES (?,?,?,?,?,?,?,?)",
            (data.get("name", ""), data.get("target_position", ""), data.get("education", ""),
             data.get("experience_years", ""), data.get("skills", ""), data.get("file_path", ""),
             data.get("file_type", ""), data.get("parse_status", "wait")),
        )
        return get_by_id(cur.lastrowid)


def update(rid: int, data: dict) -> dict | None:
    existing = get_by_id(rid)
    if not existing:
        return None
    allowed = ["name", "target_position", "education", "experience_years", "skills", "file_path", "file_type", "parse_status", "structured_data"]
    sets = [f"{f}=?" for f in allowed if f in data]
    vals = [data[f] for f in allowed if f in data]
    if not sets:
        return existing
    vals.append(rid)
    with _conn() as conn:
        conn.execute(f"UPDATE resumes SET {', '.join(sets)} WHERE id=?", vals)
    return get_by_id(rid)


def delete(rid: int) -> bool:
    with _conn() as conn:
        return conn.execute("DELETE FROM resumes WHERE id=?", (rid,)).rowcount > 0
