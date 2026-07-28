import sqlite3

from backend.config import DB_PATH


APPLICATION_SOURCES = {"candidate", "admin", "import"}
APPLICATION_LIMIT_PER_SIX_MONTHS = 3
RECRUITMENT_TYPES = ("社招", "校招", "实习生")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_username TEXT DEFAULT '',
                candidate_name TEXT DEFAULT '',
                jd_id INTEGER DEFAULT NULL,
                jd_name TEXT DEFAULT '',
                resume_id INTEGER DEFAULT NULL,
                match_score INTEGER DEFAULT 0,
                match_details TEXT DEFAULT '{}',
                recruitment_type TEXT DEFAULT '社招',
                source TEXT DEFAULT 'candidate',
                status TEXT DEFAULT 'pending',
                workflow_id TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_candidate ON applications(candidate_username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_resume ON applications(resume_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_workflow ON applications(workflow_id)")
        cols = {row[1] for row in conn.execute("PRAGMA table_info(applications)").fetchall()}
        if "match_score" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN match_score INTEGER DEFAULT 0")
        if "match_details" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN match_details TEXT DEFAULT '{}'")
        if "recruitment_type" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN recruitment_type TEXT DEFAULT '社招'")
        _backfill_existing_plans(conn)


def _backfill_existing_plans(conn) -> None:
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    plan_cols = {row[1] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}
    if not {"application_id", "resume_id", "workflow_id"}.issubset(plan_cols):
        return

    resume_cols = {row[1] for row in conn.execute("PRAGMA table_info(resumes)").fetchall()}
    has_owner = "candidate_username" in resume_cols
    owner_sql = ", candidate_username" if has_owner else ""
    resumes = conn.execute(f"SELECT id, file_path, jd_id{owner_sql} FROM resumes WHERE IFNULL(file_path, '')<>''").fetchall()
    resume_by_file = {row["file_path"]: dict(row) for row in resumes}
    jd_by_name = {}
    if "jds" in tables:
        jd_by_name = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM jds WHERE IFNULL(name, '')<>''").fetchall()
        }

    if has_owner and "candidates" in tables:
        current_resumes = conn.execute(
            "SELECT username, resume_filename FROM candidates WHERE IFNULL(resume_filename, '')<>''"
        ).fetchall()
        for candidate in current_resumes:
            resume = resume_by_file.get(candidate["resume_filename"])
            if resume:
                conn.execute(
                    "UPDATE resumes SET candidate_username=?, source='candidate' WHERE id=?",
                    (candidate["username"], resume["id"]),
                )

    groups = conn.execute("""
        SELECT
            workflow_id,
            MIN(id) AS seed_id,
            MAX(candidate_username) AS candidate_username,
            MAX(candidate_name) AS candidate_name,
            MAX(jd_name) AS jd_name,
            MAX(resume_filename) AS resume_filename
        FROM plans
        WHERE IFNULL(workflow_id, '')<>''
        GROUP BY workflow_id
    """).fetchall()
    for group in groups:
        existing = conn.execute("SELECT id FROM applications WHERE workflow_id=?", (group["workflow_id"],)).fetchone()
        resume = resume_by_file.get(group["resume_filename"] or "")
        resume_id = resume["id"] if resume else None
        jd_id = (resume or {}).get("jd_id") or jd_by_name.get(group["jd_name"] or "")
        if not jd_id and str(group["workflow_id"]).startswith("apply_"):
            try:
                jd_id = int(str(group["workflow_id"]).split("_", 2)[1])
            except (IndexError, TypeError, ValueError):
                jd_id = None
        source = "candidate" if str(group["workflow_id"]).startswith("apply_") else "admin"
        if existing:
            application_id = existing["id"]
            conn.execute(
                """
                UPDATE applications
                SET candidate_username=?, candidate_name=?, jd_id=COALESCE(jd_id, ?),
                    jd_name=?, resume_id=COALESCE(resume_id, ?), source=?,
                    recruitment_type=COALESCE(
                        (SELECT recruitment_type FROM jds WHERE id=COALESCE(applications.jd_id, ?)),
                        recruitment_type
                    ),
                    updated_at=datetime('now')
                WHERE id=?
                """,
                (
                    group["candidate_username"] or "",
                    group["candidate_name"] or "",
                    jd_id,
                    group["jd_name"] or "",
                    resume_id,
                    source,
                    jd_id,
                    application_id,
                ),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO applications (
                    candidate_username, candidate_name, jd_id, jd_name, resume_id, source, workflow_id
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    group["candidate_username"] or "",
                    group["candidate_name"] or "",
                    jd_id,
                    group["jd_name"] or "",
                    resume_id,
                    source,
                    group["workflow_id"],
                ),
            )
            application_id = cur.lastrowid
        conn.execute(
            "UPDATE plans SET application_id=?, resume_id=COALESCE(resume_id, ?) WHERE workflow_id=?",
            (application_id, resume_id, group["workflow_id"]),
        )
        if resume and has_owner and not (resume["candidate_username"] or "") and group["candidate_username"]:
            conn.execute(
                "UPDATE resumes SET candidate_username=?, source=? WHERE id=?",
                (group["candidate_username"], source, resume_id),
            )


def create(data: dict) -> dict:
    source = str(data.get("source") or "candidate").strip()
    if source not in APPLICATION_SOURCES:
        source = "candidate"
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO applications (
                candidate_username, candidate_name, jd_id, jd_name, resume_id,
                match_score, match_details, recruitment_type, source, status, workflow_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data.get("candidate_username", ""),
                data.get("candidate_name", ""),
                data.get("jd_id"),
                data.get("jd_name", ""),
                data.get("resume_id"),
                data.get("match_score", 0),
                data.get("match_details", "{}"),
                normalize_recruitment_type(data.get("recruitment_type")),
                source,
                data.get("status", "pending"),
                data.get("workflow_id", ""),
            ),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row) if row else {}


def update_match(application_id: int, match_score: int, match_details: str) -> dict | None:
    with _conn() as conn:
        conn.execute(
            """
            UPDATE applications
            SET match_score=?, match_details=?, updated_at=datetime('now')
            WHERE id=?
            """,
            (min(max(int(match_score or 0), 0), 100), match_details or "{}", application_id),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    return dict(row) if row else None


def cancel(application_id: int) -> dict | None:
    with _conn() as conn:
        conn.execute(
            """
            UPDATE applications
            SET status='cancel', updated_at=datetime('now')
            WHERE id=? AND status<>'cancel'
            """,
            (application_id,),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    return dict(row) if row else None


def get_by_id(application_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    return dict(row) if row else None


def find_by_candidate_and_jd(candidate_username: str, jd_id: int) -> dict | None:
    if not candidate_username or not jd_id:
        return None
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM applications
            WHERE candidate_username=? AND jd_id=? AND status<>'cancel'
            ORDER BY id DESC LIMIT 1
            """,
            (candidate_username, jd_id),
        ).fetchone()
    return dict(row) if row else None


def get_candidate_quota(candidate_username: str) -> dict:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT id, jd_id, jd_name, recruitment_type, status, created_at
            FROM applications
            WHERE candidate_username=? AND source='candidate'
              AND status<>'cancel'
              AND datetime(created_at) >= datetime('now', '-6 months')
            ORDER BY datetime(created_at) ASC, id ASC
            """,
            (candidate_username,),
        ).fetchall()
        buckets = {}
        for recruitment_type in RECRUITMENT_TYPES:
            type_rows = [
                row for row in rows
                if normalize_recruitment_type(row["recruitment_type"]) == recruitment_type
            ]
            available_at = ""
            if len(type_rows) >= APPLICATION_LIMIT_PER_SIX_MONTHS:
                value = conn.execute(
                    "SELECT datetime(?, '+6 months') AS available_at",
                    (type_rows[0]["created_at"],),
                ).fetchone()
                available_at = value["available_at"] if value else ""
            buckets[recruitment_type] = {
                "limit": APPLICATION_LIMIT_PER_SIX_MONTHS,
                "used": len(type_rows),
                "remaining": max(0, APPLICATION_LIMIT_PER_SIX_MONTHS - len(type_rows)),
                "available_at": available_at,
            }
    return {
        "limit_per_type": APPLICATION_LIMIT_PER_SIX_MONTHS,
        "window_months": 6,
        "buckets": buckets,
        "applications": [dict(row) for row in rows],
    }


def normalize_recruitment_type(value: str | None) -> str:
    text = str(value or "").strip()
    if "实习" in text:
        return "实习生"
    if "校" in text:
        return "校招"
    return "社招"


def list_by_resume_id(resume_id: int) -> list[dict]:
    if not resume_id:
        return []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM applications WHERE resume_id=? ORDER BY id DESC",
            (resume_id,),
        ).fetchall()
    return [dict(row) for row in rows]
