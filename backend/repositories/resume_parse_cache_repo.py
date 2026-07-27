import sqlite3

from backend.config import DB_PATH

PARSER_VERSION = "resume-parser-v2"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resume_parse_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_md5 TEXT NOT NULL,
                parser_version TEXT NOT NULL,
                original_name TEXT DEFAULT '',
                file_size INTEGER DEFAULT 0,
                raw_text TEXT DEFAULT '',
                structured_data TEXT DEFAULT '{}',
                name TEXT DEFAULT '',
                target_position TEXT DEFAULT '',
                education TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(file_md5, parser_version)
            )
        """)


def get(file_md5: str, parser_version: str = PARSER_VERSION) -> dict | None:
    if not file_md5:
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM resume_parse_cache WHERE file_md5=? AND parser_version=?",
            (file_md5, parser_version),
        ).fetchone()
        return dict(row) if row else None


def upsert(data: dict, parser_version: str = PARSER_VERSION) -> dict:
    file_md5 = data.get("file_md5", "")
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO resume_parse_cache (
                file_md5, parser_version, original_name, file_size, raw_text,
                structured_data, name, target_position, education, skills
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(file_md5, parser_version) DO UPDATE SET
                original_name=excluded.original_name,
                file_size=excluded.file_size,
                raw_text=excluded.raw_text,
                structured_data=excluded.structured_data,
                name=excluded.name,
                target_position=excluded.target_position,
                education=excluded.education,
                skills=excluded.skills,
                updated_at=datetime('now')
            """,
            (
                file_md5,
                parser_version,
                data.get("original_name", ""),
                data.get("file_size", 0),
                data.get("raw_text", ""),
                data.get("structured_data", "{}"),
                data.get("name", ""),
                data.get("target_position", ""),
                data.get("education", ""),
                data.get("skills", ""),
            ),
        )
        row = conn.execute(
            "SELECT * FROM resume_parse_cache WHERE file_md5=? AND parser_version=?",
            (file_md5, parser_version),
        ).fetchone()
        return dict(row)
