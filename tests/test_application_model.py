import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.repositories import application_repo, plan_repo, resume_repo


class ApplicationModelTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "application-model.db")
        self.patches = [
            patch.object(resume_repo, "DB_PATH", self.db_path),
            patch.object(plan_repo, "DB_PATH", self.db_path),
            patch.object(application_repo, "DB_PATH", self.db_path),
        ]
        for item in self.patches:
            item.start()
        resume_repo.init_db()
        plan_repo.init_db()
        application_repo.init_db()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_resume_application_and_plan_use_stable_ids(self):
        resume = resume_repo.create({
            "name": "候选人",
            "file_path": "candidate.pdf",
            "candidate_username": "candidate-user",
            "source": "candidate",
        })
        application = application_repo.create({
            "candidate_username": "candidate-user",
            "candidate_name": "候选人",
            "jd_id": 9,
            "jd_name": "算法工程师",
            "resume_id": resume["id"],
            "source": "candidate",
            "workflow_id": "apply-test",
        })
        plan = plan_repo.create({
            "candidate_username": "candidate-user",
            "candidate_name": "候选人",
            "jd_id": 9,
            "jd_name": "算法工程师",
            "resume_id": resume["id"],
            "resume_filename": resume["file_path"],
            "application_id": application["id"],
            "workflow_id": "apply-test",
        })

        self.assertEqual(plan["resume_id"], resume["id"])
        self.assertEqual(plan["application_id"], application["id"])
        self.assertEqual(application_repo.find_by_candidate_and_jd("candidate-user", 9)["id"], application["id"])
        self.assertEqual(len(application_repo.list_by_resume_id(resume["id"])), 1)

    def test_resumes_can_be_owned_and_filtered_by_source(self):
        resume_repo.create({
            "name": "自主投递",
            "file_path": "self.pdf",
            "candidate_username": "self-user",
            "source": "candidate",
        })
        resume_repo.create({
            "name": "后台推荐",
            "file_path": "admin.pdf",
            "source": "admin",
        })

        self.assertEqual(
            [item["name"] for item in resume_repo.list_by_candidate_username("self-user")],
            ["自主投递"],
        )
        self.assertTrue(any(item["name"] == "自主投递" for item in resume_repo.list_all(source="candidate")))
        self.assertTrue(any(item["name"] == "后台推荐" for item in resume_repo.list_all(source="admin")))


if __name__ == "__main__":
    unittest.main()
