import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.repositories import favorite_repo, jd_repo


class CandidateFavoritesTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "favorites.db")
        self.patches = [
            patch.object(jd_repo, "DB_PATH", self.db_path),
            patch.object(favorite_repo, "DB_PATH", self.db_path),
        ]
        for item in self.patches:
            item.start()
        jd_repo.init_db()
        favorite_repo.init_db()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_each_candidate_has_independent_favorites(self):
        first_job = jd_repo.create({"name": "算法工程师", "status": "enable"})
        second_job = jd_repo.create({"name": "数据工程师", "status": "enable"})

        favorite_repo.add("candidate-a", first_job["id"])
        favorite_repo.add("candidate-b", second_job["id"])

        self.assertEqual(
            [item["id"] for item in favorite_repo.list_by_candidate("candidate-a")],
            [first_job["id"]],
        )
        self.assertEqual(
            [item["id"] for item in favorite_repo.list_by_candidate("candidate-b")],
            [second_job["id"]],
        )

        favorite_repo.remove("candidate-a", first_job["id"])
        self.assertEqual(favorite_repo.list_by_candidate("candidate-a"), [])
        self.assertEqual(
            [item["id"] for item in favorite_repo.list_by_candidate("candidate-b")],
            [second_job["id"]],
        )


if __name__ == "__main__":
    unittest.main()
