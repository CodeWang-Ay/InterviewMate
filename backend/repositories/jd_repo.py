import sqlite3
from backend.config import DB_PATH


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


def get_by_id(jd_id):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM jds WHERE id=?", (jd_id,)).fetchone()
        return dict(row) if row else None


def create(data):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO jds (name, category, location, responsibilities, requirements, status, recruitment_type, experience_required) VALUES (?,?,?,?,?,?,?,?)",
            (data["name"], data.get("category", ""), data.get("location", ""),
             data.get("responsibilities", ""), data.get("requirements", ""), data.get("status", "enable"),
             data.get("recruitment_type", "社招"), data.get("experience_required", "")),
        )
        return get_by_id(cur.lastrowid)


def update(jd_id, data):
    existing = get_by_id(jd_id)
    if not existing:
        return None
    fields = ["name", "category", "location", "responsibilities", "requirements", "status", "recruitment_type", "experience_required"]
    sets = [f"{f}=?" for f in fields if f in data]
    vals = [data[f] for f in fields if f in data]
    if not sets:
        return existing
    vals.append(jd_id)
    with _conn() as conn:
        conn.execute(f"UPDATE jds SET {', '.join(sets)} WHERE id=?", vals)
    return get_by_id(jd_id)


def delete(jd_id):
    with _conn() as conn:
        return conn.execute("DELETE FROM jds WHERE id=?", (jd_id,)).rowcount > 0
