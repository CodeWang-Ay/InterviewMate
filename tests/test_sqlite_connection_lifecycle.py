import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.repositories import admin_repo


class SqliteConnectionLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "auth.db")
        self.db_patch = patch.object(admin_repo, "DB_PATH", self.db_path)
        self.db_patch.start()
        admin_repo.tokens.clear()
        admin_repo.init_db()

    def tearDown(self):
        admin_repo.tokens.clear()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_legacy_password_upgrade_commits_and_releases_write_lock(self):
        legacy_hash = hashlib.sha256("legacy-password".encode()).hexdigest()
        with admin_repo._conn() as conn:
            conn.execute(
                "INSERT INTO admins (username, password_hash, nickname) VALUES (?,?,?)",
                ("legacy-admin", legacy_hash, "旧管理员"),
            )

        result = admin_repo.login("legacy-admin", "legacy-password")
        self.assertIsNotNone(result)
        self.assertTrue(admin_repo.update_profile("legacy-admin", {"nickname": "已升级"}))

        with admin_repo._conn() as conn:
            row = conn.execute(
                "SELECT password_hash, nickname FROM admins WHERE username=?",
                ("legacy-admin",),
            ).fetchone()
        self.assertTrue(row["password_hash"].startswith("$2"))
        self.assertEqual(row["nickname"], "已升级")


if __name__ == "__main__":
    unittest.main()
