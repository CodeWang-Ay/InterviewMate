import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.controllers.auth_controller import session_info
from backend.repositories import candidate_repo


class CandidateProfilePersistenceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "candidate-profile.db")
        self.db_patch = patch.object(candidate_repo, "DB_PATH", self.db_path)
        self.db_patch.start()
        candidate_repo.tokens.clear()
        candidate_repo.init_db()

    def tearDown(self):
        candidate_repo.tokens.clear()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_avatar_is_restored_by_login_and_session(self):
        candidate_repo.register("avatar-user", "password123", "头像用户", "13800138000")
        avatar_url = "/uploads/avatars/avatar-persisted.jpg"
        self.assertTrue(candidate_repo.update_profile("avatar-user", {
            "avatar": avatar_url,
            "email": "avatar@example.com",
        }))

        login_result = candidate_repo.login("avatar-user", "password123")
        self.assertEqual(login_result["avatar"], avatar_url)
        self.assertEqual(login_result["email"], "avatar@example.com")

        profile = candidate_repo.get_candidate_info("avatar-user")
        session_result = asyncio.run(session_info({
            "kind": "candidate",
            "username": "avatar-user",
            "profile": profile,
        }))
        self.assertEqual(session_result["avatar"], avatar_url)
        self.assertEqual(session_result["email"], "avatar@example.com")

    def test_remembered_session_survives_memory_cache_reset(self):
        candidate_repo.register("remember-user", "password123", "长期登录用户")

        login_result = candidate_repo.login("remember-user", "password123", remember_me=True)
        token = login_result["token"]
        candidate_repo.tokens.clear()

        self.assertEqual(candidate_repo.get_candidate_by_token(token), "remember-user")
        with candidate_repo._conn() as conn:
            row = conn.execute(
                "SELECT token_hash, expires_at FROM auth_sessions WHERE username=?",
                ("remember-user",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertNotEqual(row["token_hash"], token)

        candidate_repo.logout(token)
        candidate_repo.tokens.clear()
        self.assertIsNone(candidate_repo.get_candidate_by_token(token))


if __name__ == "__main__":
    unittest.main()
