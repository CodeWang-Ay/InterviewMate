import sqlite3
from backend.config import DB_PATH

EXPERIENCE_OPTIONS = ["不限经验", "应届生", "1-3年", "3-5年", "5-10年", "10年以上"]
CATEGORY_OPTIONS = {"技术", "产品", "政企", "销售", "综合"}


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _conn():
    c = sqlite3.connect(DB_PATH, timeout=5, factory=_ClosingConnection)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
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
        cols = {row[1] for row in conn.execute("PRAGMA table_info(jds)").fetchall()}
        for col, definition in [("deleted_at", "TEXT DEFAULT NULL"), ("deleted_by", "TEXT DEFAULT ''"), ("delete_reason", "TEXT DEFAULT ''"), ("published_at", "TEXT DEFAULT ''")]:
            if col not in cols:
                conn.execute(f"ALTER TABLE jds ADD COLUMN {col} {definition}")
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
        # 保证职位首页的六个方向都有可展示的岗位；已有同名岗位时不重复插入。
        category_samples = [
            ("全栈开发工程师", "技术", "深圳", "负责前后端功能开发、接口联调和系统性能优化。", "熟悉Java或Python、Vue/React、MySQL，具备完整项目交付经验。"),
            ("B端产品经理", "产品", "上海", "负责业务调研、需求分析、原型设计和产品迭代。", "3年以上产品经验，熟悉B端产品方法和项目协作流程。"),
            ("机器学习算法工程师", "算法", "北京", "负责模型训练、评估、调优和算法服务落地。", "熟悉Python、PyTorch和常见机器学习算法，有项目经验。"),
            ("数据分析师", "数据", "杭州", "负责业务数据分析、指标体系建设和数据可视化。", "熟悉SQL、Python和至少一种BI工具，具备良好的业务理解能力。"),
            ("招聘运营专员", "运营", "广州", "负责招聘活动运营、候选人沟通和招聘数据跟踪。", "沟通能力良好，熟悉招聘流程和运营工具，有相关经验优先。"),
            ("业务管理培训生", "综合", "成都", "参与业务轮岗、项目协作和跨部门流程优化。", "本科及以上学历，学习能力强，具备良好的沟通和执行能力。"),
            ("政企客户解决方案顾问", "政企", "北京", "负责政企客户需求调研、解决方案设计和项目推进。", "具备政企项目经验，熟悉招投标和客户沟通流程，文字表达能力良好。"),
            ("大客户销售经理", "销售", "深圳", "负责重点客户开拓、商机跟进和商务谈判，完成销售目标。", "具备B端销售经验，沟通和谈判能力强，能够适应出差。"),
            ("政企项目交付经理", "政企", "广州", "负责政企项目计划、交付协调、风险跟踪和客户汇报。", "具备项目管理经验，熟悉政企客户交付流程，沟通协调能力强。"),
            ("政企售前顾问", "政企", "杭州", "负责政企客户技术交流、方案编写和投标支持。", "熟悉解决方案售前流程，具备较强的方案表达和文档编写能力。"),
            ("企业客户销售顾问", "销售", "上海", "负责企业客户开发、需求挖掘、报价谈判和客户维护。", "有B端或软件销售经验，目标感强，善于建立客户关系。"),
            ("销售运营专员", "销售", "成都", "负责销售线索管理、数据分析、合同流程和销售团队支持。", "熟悉Excel或数据分析工具，细致负责，具备良好的跨部门协作能力。"),
        ]
        existing_names = {row[0] for row in conn.execute("SELECT name FROM jds").fetchall()}
        missing = [item for item in category_samples if item[0] not in existing_names]
        if missing:
            conn.executemany(
                "INSERT INTO jds (name, category, location, responsibilities, requirements, status, recruitment_type, experience_required) VALUES (?,?,?,?,?,?,?,?)",
                [(name, category, location, responsibilities, requirements, "enable", "社招", "不限经验") for name, category, location, responsibilities, requirements in missing],
            )
        campus_intern_samples = [
            ("校招-软件开发工程师", "技术", "深圳", "参与业务系统开发、测试和技术文档编写，在导师指导下完成项目任务。", "计算机相关专业本科及以上，熟悉Java、Python或前端开发，有课程或项目实践。", "校招"),
            ("校招-产品助理", "产品", "上海", "协助产品调研、需求整理、原型绘制和版本跟进。", "本科及以上学历，逻辑清晰，具备良好的沟通和文档能力。", "校招"),
            ("校招-政企项目助理", "政企", "北京", "协助政企项目资料整理、进度跟踪和客户会议准备。", "本科及以上学历，责任心强，熟悉Office，能适应项目协作。", "校招"),
            ("实习-数据分析实习生", "技术", "杭州", "协助完成数据清洗、指标统计、报表制作和业务分析。", "在校本科或硕士，熟悉SQL或Python，每周可实习4天以上。", "实习生"),
            ("实习-销售支持实习生", "销售", "广州", "协助销售线索整理、客户资料维护、合同流程和数据统计。", "在校生，细致耐心，熟悉Excel，具备良好的沟通能力。", "实习生"),
            ("实习-综合运营实习生", "综合", "成都", "协助招聘运营、活动执行、内容整理和跨部门沟通。", "在校生，执行力强，学习能力好，每周可实习3天以上。", "实习生"),
            ("实习-前端开发实习生", "技术", "深圳", "协助开发招聘平台页面、组件和接口交互，参与兼容性测试。", "熟悉HTML、CSS、JavaScript和Vue，能保证每周实习4天以上。", "实习生"),
            ("实习-产品运营实习生", "产品", "上海", "协助用户调研、需求整理、竞品分析和产品内容运营。", "产品或市场相关专业优先，逻辑清晰，具备较好的文字表达能力。", "实习生"),
        ]
        existing_names = {row[0] for row in conn.execute("SELECT name FROM jds").fetchall()}
        special_missing = [item for item in campus_intern_samples if item[0] not in existing_names]
        if special_missing:
            conn.executemany(
                "INSERT INTO jds (name, category, location, responsibilities, requirements, status, recruitment_type, experience_required) VALUES (?,?,?,?,?,?,?,?)",
                [(name, category, location, responsibilities, requirements, "enable", recruitment_type, "应届生") for name, category, location, responsibilities, requirements, recruitment_type in special_missing],
            )
        # 统一历史 JD 的分类，前台只暴露五个业务方向。
        # 按优先级一次性归类，避免多个 LIKE 规则互相覆盖（例如“产品运营”被后续规则改成政企）。
        conn.execute("""
            UPDATE jds SET category = CASE
                WHEN name LIKE '%政企%' THEN '政企'
                WHEN name LIKE '%销售%' THEN '销售'
                WHEN name LIKE '%产品%' THEN '产品'
                WHEN name LIKE '%综合%' OR name LIKE '%运营%' OR name LIKE '%业务管理%' OR name LIKE '%招聘%' THEN '综合'
                WHEN name LIKE '%工程师%' OR name LIKE '%开发%' OR name LIKE '%算法%' OR name LIKE '%数据%' OR name LIKE '%测试%' OR name LIKE '%运维%' OR name LIKE '%安全%' OR name LIKE '%标注%' OR name LIKE '%NLP%' THEN '技术'
                ELSE category
            END
            WHERE IFNULL(deleted_at, '')='' AND (category IS NULL OR TRIM(category)='' OR category NOT IN ('技术', '产品', '政企', '销售', '综合'))
        """)
        conn.execute("UPDATE jds SET category='综合' WHERE category NOT IN ('技术', '产品', '政企', '销售', '综合') AND IFNULL(deleted_at, '')=''")
        conn.execute("UPDATE jds SET experience_required='不限经验' WHERE recruitment_type='实习生' AND IFNULL(deleted_at, '')=''")
        # 清理同一招聘类型下的重复岗位名称，保留最早创建的一条，避免列表出现重复 JD。
        duplicate_rows = conn.execute("""
            SELECT recruitment_type, name, GROUP_CONCAT(id) AS ids
            FROM jds
            WHERE IFNULL(deleted_at, '')=''
            GROUP BY recruitment_type, name
            HAVING COUNT(*) > 1
        """).fetchall()
        for row in duplicate_rows:
            ids = sorted(int(value) for value in str(row["ids"]).split(","))
            for duplicate_id in ids[1:]:
                conn.execute("UPDATE jds SET deleted_at=datetime('now'), delete_reason='重复岗位自动归档' WHERE id=?", (duplicate_id,))


def list_all_paged(category="", status="", location="", search="", recruitment_type="", page=1, page_size=10, archived=""):
    where = "WHERE 1=1"
    params = []
    if archived == "archived":
        where += " AND IFNULL(deleted_at, '')<>''"
    else:
        where += " AND IFNULL(deleted_at, '')=''"
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
        active = "IFNULL(deleted_at, '')=''"
        total = conn.execute(f"SELECT COUNT(*) FROM jds WHERE {active}").fetchone()[0]
        archived = conn.execute("SELECT COUNT(*) FROM jds WHERE IFNULL(deleted_at, '')<>''").fetchone()[0]
        enabled = conn.execute(f"SELECT COUNT(*) FROM jds WHERE status='enable' AND {active}").fetchone()[0]
        disabled = conn.execute(f"SELECT COUNT(*) FROM jds WHERE status='disable' AND {active}").fetchone()[0]
        categories = conn.execute(f"SELECT COUNT(DISTINCT category) FROM jds WHERE category != '' AND {active}").fetchone()[0]
        interns = conn.execute(f"SELECT COUNT(*) FROM jds WHERE recruitment_type='实习生' AND {active}").fetchone()[0]
        campus = conn.execute(f"SELECT COUNT(*) FROM jds WHERE recruitment_type='校招' AND {active}").fetchone()[0]
        social = conn.execute(f"SELECT COUNT(*) FROM jds WHERE recruitment_type='社招' AND {active}").fetchone()[0]
        return {"total": total, "archived": archived, "enabled": enabled, "disabled": disabled, "categories": categories,
                "interns": interns, "campus": campus, "social": social}


def get_by_id(jd_id):
    with _conn() as conn:
        row = conn.execute("""
            SELECT j.*,
              (SELECT COUNT(*) FROM applications a WHERE a.jd_id=j.id AND IFNULL(a.deleted_at, '')='' AND a.status NOT IN ('withdrawn','cancel')) AS application_count,
              (SELECT COUNT(*) FROM applications a WHERE a.jd_id=j.id AND IFNULL(a.deleted_at, '')='' AND a.status NOT IN ('withdrawn','cancel','rejected','closed','hired')) AS active_application_count,
              (SELECT COUNT(*) FROM applications a WHERE a.jd_id=j.id AND IFNULL(a.deleted_at, '')='' AND a.status IN ('rejected','closed','hired','withdrawn','cancel')) AS completed_application_count
            FROM jds j WHERE j.id=?
        """, (jd_id,)).fetchone()
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
    if data.get("category") not in CATEGORY_OPTIONS:
        data["category"] = "综合"
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO jds (name, category, location, responsibilities, requirements, status, recruitment_type, experience_required) VALUES (?,?,?,?,?,?,?,?)",
            (data["name"], data.get("category", ""), data.get("location", ""),
             data.get("responsibilities", ""), data.get("requirements", ""), data.get("status", "enable"),
             data.get("recruitment_type", "社招"), normalize_experience(data.get("experience_required", ""))),
        )
        row = conn.execute("SELECT * FROM jds WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row) if row else None


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
    requested_status = data.get("status")
    if requested_status in {"enable", "published"} and existing.get("status") == "closed":
        raise ValueError("已关闭 JD 不能直接恢复为已发布，请创建 JD 副本后重新发布")
    if requested_status in {"enable", "published"} and (not str(existing.get("responsibilities") or "").strip() or not str(existing.get("requirements") or "").strip()):
        # 允许本次更新同时补齐内容后发布
        responsibilities = data.get("responsibilities", existing.get("responsibilities"))
        requirements = data.get("requirements", existing.get("requirements"))
        if not str(responsibilities or "").strip() or not str(requirements or "").strip():
            raise ValueError("发布前请先填写岗位职责和任职要求")
    if requested_status in {"closed", "expired"} and existing.get("active_application_count", 0) > 0:
        raise ValueError(f"该 JD 仍有 {existing['active_application_count']} 条进行中投递，不能直接结束流程")
    fields = ["name", "category", "location", "responsibilities", "requirements", "status", "recruitment_type", "experience_required"]
    if "experience_required" in data:
        data["experience_required"] = normalize_experience(data.get("experience_required"))
    if "category" in data and data.get("category") not in CATEGORY_OPTIONS:
        data["category"] = existing.get("category") if existing.get("category") in CATEGORY_OPTIONS else "综合"
    sets = [f"{f}=?" for f in fields if f in data]
    vals = [data[f] for f in fields if f in data]
    if data.get("status") in {"enable", "published"} and not existing.get("published_at"):
        sets.append("published_at=datetime('now')")
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
        return conn.execute("UPDATE jds SET deleted_at=datetime('now') WHERE id=? AND IFNULL(deleted_at, '')=''", (jd_id,)).rowcount > 0
