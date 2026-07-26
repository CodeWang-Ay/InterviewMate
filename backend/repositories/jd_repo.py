import sqlite3
from backend.config import DB_PATH

EXPERIENCE_OPTIONS = ["不限经验", "应届生", "1-3年", "3-5年", "5-10年", "10年以上"]


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT DEFAULT '',
                location TEXT DEFAULT '',
                responsibilities TEXT DEFAULT '',
                requirements TEXT DEFAULT '',
                status TEXT DEFAULT 'enable',
                recruitment_type TEXT DEFAULT '社招',
                experience_required TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jd_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jd_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                category TEXT DEFAULT '',
                location TEXT DEFAULT '',
                responsibilities TEXT DEFAULT '',
                requirements TEXT DEFAULT '',
                status TEXT DEFAULT 'enable',
                recruitment_type TEXT DEFAULT '社招',
                experience_required TEXT DEFAULT '',
                source TEXT DEFAULT 'manual',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        rows = conn.execute("SELECT id, experience_required FROM jds").fetchall()
        for row in rows:
            normalized = normalize_experience(row["experience_required"])
            if normalized != (row["experience_required"] or ""):
                conn.execute("UPDATE jds SET experience_required=? WHERE id=?", (normalized, row["id"]))
        cnt = conn.execute("SELECT COUNT(*) FROM jds").fetchone()[0]
        if cnt == 0:
            samples = [
                ("后端开发工程师", "技术开发", "深圳",
                 "负责业务后端接口开发，数据库设计，参与需求评审，保障系统稳定运行，优化接口性能，编写单元测试文档。",
                 "本科及以上学历，2年以上Java开发经验，熟练掌握SpringBoot、MySQL、Redis，了解微服务架构。", "enable"),
                ("前端开发工程师", "技术开发", "深圳",
                 "负责Web页面开发，组件封装，对接后端接口，优化页面加载速度，兼容不同浏览器，参与前端工程化建设。",
                 "熟悉Vue3、TypeScript，有中后台系统开发经验，了解前端性能优化方案。", "enable"),
                ("大模型算法工程师", "算法", "上海",
                 "负责LLM微调、RAG知识库搭建，Prompt工程优化，完成AI应用落地，持续迭代模型效果。",
                 "硕士学历优先，熟练Python，熟悉LangChain、向量数据库，具备大模型落地项目经验。", "disable"),
                ("产品经理", "产品", "北京",
                 "负责产品需求分析、原型设计，协调研发与设计资源，推动产品上线迭代。",
                 "3年以上互联网产品经验，逻辑清晰，善于沟通，有B端产品经验优先。", "enable"),
            ]
            conn.executemany(
                "INSERT INTO jds (name, category, location, responsibilities, requirements, status) VALUES (?,?,?,?,?,?)",
                samples,
            )


def list_all_paged(category="", status="", location="", search="", recruitment_type="", page=1, page_size=10):
    where = "WHERE 1=1"
    params = []
    if category:
        where += " AND category=?"
        params.append(category)
    if status:
        where += " AND status=?"
        params.append(status)
    if location:
        where += " AND location=?"
        params.append(location)
    if recruitment_type:
        where += " AND recruitment_type=?"
        params.append(recruitment_type)
    if search:
        where += " AND name LIKE ?"
        params.append(f"%{search}%")

    with _conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM jds {where}", params).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM jds {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
        return [dict(r) for r in rows], total


def get_stats():
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jds").fetchone()[0]
        enabled = conn.execute("SELECT COUNT(*) FROM jds WHERE status='enable'").fetchone()[0]
        disabled = conn.execute("SELECT COUNT(*) FROM jds WHERE status='disable'").fetchone()[0]
        categories = conn.execute("SELECT COUNT(DISTINCT category) FROM jds WHERE category != ''").fetchone()[0]
        interns = conn.execute("SELECT COUNT(*) FROM jds WHERE recruitment_type='实习生'").fetchone()[0]
        campus = conn.execute("SELECT COUNT(*) FROM jds WHERE recruitment_type='校招'").fetchone()[0]
        social = conn.execute("SELECT COUNT(*) FROM jds WHERE recruitment_type='社招'").fetchone()[0]
        return {"total": total, "enabled": enabled, "disabled": disabled, "categories": categories,
                "interns": interns, "campus": campus, "social": social}


def get_by_id(jd_id):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM jds WHERE id=?", (jd_id,)).fetchone()
        return dict(row) if row else None


def get_by_name(name):
    text = str(name or "").strip()
    if not text:
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM jds WHERE name=? ORDER BY id DESC LIMIT 1",
            (text,),
        ).fetchone()
        return dict(row) if row else None


def create(data):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO jds (name, category, location, responsibilities, requirements, status, recruitment_type, experience_required) VALUES (?,?,?,?,?,?,?,?)",
            (data["name"], data.get("category", ""), data.get("location", ""),
             data.get("responsibilities", ""), data.get("requirements", ""), data.get("status", "enable"),
             data.get("recruitment_type", "社招"), normalize_experience(data.get("experience_required", ""))),
        )
        return get_by_id(cur.lastrowid)


def duplicate(jd_id):
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO jds (
                name, category, location, responsibilities, requirements,
                status, recruitment_type, experience_required
            )
            SELECT
                name || '（副本）', category, location, responsibilities, requirements,
                status, recruitment_type, experience_required
            FROM jds
            WHERE id=?
            """,
            (jd_id,),
        )
        if cur.rowcount <= 0:
            return None
        row = conn.execute("SELECT * FROM jds WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row) if row else None


def _save_version(conn, jd, source="manual"):
    conn.execute(
        """
        INSERT INTO jd_versions (
            jd_id, name, category, location, responsibilities, requirements,
            status, recruitment_type, experience_required, source
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            jd["id"], jd.get("name", ""), jd.get("category", ""), jd.get("location", ""),
            jd.get("responsibilities", ""), jd.get("requirements", ""), jd.get("status", "enable"),
            jd.get("recruitment_type", "社招"), jd.get("experience_required", ""), source,
        ),
    )


def update(jd_id, data, source="manual"):
    existing = get_by_id(jd_id)
    if not existing:
        return None
    fields = ["name", "category", "location", "responsibilities", "requirements", "status", "recruitment_type", "experience_required"]
    if "experience_required" in data:
        data["experience_required"] = normalize_experience(data.get("experience_required"))
    sets = [f"{f}=?" for f in fields if f in data]
    vals = [data[f] for f in fields if f in data]
    if not sets:
        return existing
    vals.append(jd_id)
    with _conn() as conn:
        _save_version(conn, existing, source)
        conn.execute(f"UPDATE jds SET {', '.join(sets)}, updated_at=datetime('now') WHERE id=?", vals)
    updated = get_by_id(jd_id)
    if updated and "name" in data:
        from backend.repositories import resume_repo
        resume_repo.sync_jd_name(jd_id, updated.get("name", ""))
    return updated


def list_versions(jd_id):
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jd_versions WHERE jd_id=? ORDER BY id DESC",
            (jd_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def restore_version(jd_id, version_id):
    current = get_by_id(jd_id)
    if not current:
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM jd_versions WHERE id=? AND jd_id=?",
            (version_id, jd_id),
        ).fetchone()
        if not row:
            return None
        version = dict(row)
        _save_version(conn, current, "restore")
        fields = ["name", "category", "location", "responsibilities", "requirements", "status", "recruitment_type", "experience_required"]
        sets = [f"{f}=?" for f in fields]
        vals = [normalize_experience(version.get(f, "")) if f == "experience_required" else version.get(f, "") for f in fields] + [jd_id]
        conn.execute(f"UPDATE jds SET {', '.join(sets)}, updated_at=datetime('now') WHERE id=?", vals)
    updated = get_by_id(jd_id)
    if updated:
        from backend.repositories import resume_repo
        resume_repo.sync_jd_name(jd_id, updated.get("name", ""))
    return updated


def normalize_experience(value):
    text = str(value or "").strip()
    if text in EXPERIENCE_OPTIONS:
        return text
    if not text or text in {"不限", "不限经验", "经验不限", "无经验要求"}:
        return "不限经验"
    if any(token in text for token in ["应届", "校招", "毕业生", "实习"]):
        return "应届生"
    if any(token in text for token in ["10年以上", "10 年以上", "10+", "十年以上"]):
        return "10年以上"
    if any(token in text for token in ["5-10", "5 到 10", "5至10", "5年以上", "5 年以上", "高级", "资深", "专家"]):
        return "5-10年"
    if any(token in text for token in ["3-5", "3 到 5", "3至5", "3年以上", "3 年以上", "中级"]):
        return "3-5年"
    if any(token in text for token in ["1-3", "1 到 3", "1至3", "1年以上", "1 年以上", "初级"]):
        return "1-3年"
    return "不限经验"


def delete(jd_id):
    with _conn() as conn:
        return conn.execute("DELETE FROM jds WHERE id=?", (jd_id,)).rowcount > 0
