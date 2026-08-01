import sqlite3
from datetime import datetime, timedelta

from backend.config import DB_PATH
from backend.repositories import application_repo, plan_repo


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=5, factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_username TEXT NOT NULL,
                event_key TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                target_url TEXT DEFAULT '/user',
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(candidate_username, event_key)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_candidate ON notifications(candidate_username, is_read, id DESC)")


def create_once(username: str, event_key: str, type_: str, title: str, content: str, target_url: str = "/user") -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO notifications (candidate_username,event_key,type,title,content,target_url) VALUES (?,?,?,?,?,?)",
            (username, event_key, type_, title, content, target_url),
        )


def sync_candidate_events(username: str) -> None:
    init_db()
    applications = application_repo.list_by_candidate_username(username)
    for app in applications:
        aid = int(app["id"])
        job = app.get("jd_name") or "投递岗位"
        target = f"/user?application_id={aid}"
        screening = app.get("screening_status")
        if screening in {"初筛通过", "不合适"}:
            passed = screening == "初筛通过"
            create_once(username, f"screening:{aid}:{screening}", "screening", f"{job} · {'初筛通过' if passed else '初筛未通过'}", "招聘方已更新简历筛选结果。" if passed else "本次流程已结束，你仍可查看完整投递记录。", target)
        if app.get("workflow_id") and not str(app.get("workflow_id")).startswith("apply_"):
            create_once(username, f"workflow:{aid}:{app['workflow_id']}", "interview", f"{job} · 面试流程已创建", "请查看面试轮次和时间安排。", target)
        offer = app.get("offer_status")
        if offer in {"offered", "accepted", "declined", "rejected"}:
            labels = {"offered": "Offer 已发放", "accepted": "Offer 已接受", "declined": "Offer 已拒绝", "rejected": "本次不发放 Offer"}
            create_once(username, f"offer:{aid}:{offer}", "offer", f"{job} · {labels[offer]}", "请进入投递记录查看 Offer 状态。", target)

    now = datetime.now()
    for plan in plan_repo.list_by_candidate_username(username):
        scheduled = str(plan.get("scheduled_at") or "").strip()
        if not scheduled or plan.get("status") not in {"wait", "running"}:
            continue
        try:
            start = datetime.fromisoformat(scheduled.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            continue
        if now <= start <= now + timedelta(hours=24):
            create_once(username, f"reminder:{plan['id']}:{scheduled}", "reminder", f"面试提醒 · {plan.get('jd_name') or plan.get('interview_round')}", f"{plan.get('interview_round') or '面试'}将在 {scheduled.replace('T', ' ')[:16]} 开始。", f"/user?plan_id={plan['id']}")


def list_by_candidate(username: str, limit: int = 50) -> dict:
    sync_candidate_events(username)
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM notifications WHERE candidate_username=? ORDER BY id DESC LIMIT ?", (username, limit)).fetchall()
        unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE candidate_username=? AND is_read=0", (username,)).fetchone()[0]
    return {"items": [dict(row) for row in rows], "unread": unread}


def mark_read(notification_id: int, username: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND candidate_username=?", (notification_id, username))
    return cur.rowcount > 0


def mark_all_read(username: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE notifications SET is_read=1 WHERE candidate_username=?", (username,))
