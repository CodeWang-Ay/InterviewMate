import sqlite3

from backend.config import DB_PATH


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
            CREATE TABLE IF NOT EXISTS candidate_job_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_username TEXT NOT NULL,
                jd_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(candidate_username, jd_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_job_favorites_username "
            "ON candidate_job_favorites(candidate_username)"
        )


def list_by_candidate(candidate_username: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT j.*, f.created_at AS favorited_at
            FROM candidate_job_favorites f
            JOIN jds j ON j.id=f.jd_id
            WHERE f.candidate_username=? AND j.status='enable'
            ORDER BY f.created_at DESC, f.id DESC
            """,
            (candidate_username,),
        ).fetchall()
    return [dict(row) for row in rows]


def add(candidate_username: str, jd_id: int) -> bool:
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO candidate_job_favorites (candidate_username, jd_id) VALUES (?,?)",
            (candidate_username, jd_id),
        )
    return True


def remove(candidate_username: str, jd_id: int) -> bool:
    with _conn() as conn:
        cursor = conn.execute(
            "DELETE FROM candidate_job_favorites WHERE candidate_username=? AND jd_id=?",
            (candidate_username, jd_id),
        )
    return cursor.rowcount > 0
