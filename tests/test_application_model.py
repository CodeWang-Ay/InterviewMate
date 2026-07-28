import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.repositories import application_repo, plan_repo, resume_repo
from backend.services.job_match_service import calculate_resume_jd_match


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
        self.assertEqual(application_repo.cancel(application["id"])["status"], "cancel")

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

    def test_job_match_is_explainable_and_changes_with_jd(self):
        resume = {
            "id": 1,
            "target_position": "大模型算法工程师",
            "education": "硕士",
            "experience_years": "3年",
            "skills": "Python, PyTorch, LLM, RAG, NLP, Docker",
            "structured_data": json.dumps({
                "基础信息": {"意向岗位": "大模型算法工程师"},
                "项目经历": [{"项目名称": "RAG 知识库"}, {"项目名称": "模型微调"}],
                "工作经历": [{"公司": "科技公司", "职位": "算法工程师"}],
            }, ensure_ascii=False),
        }
        matching_jd = {
            "id": 9,
            "name": "大模型算法工程师",
            "category": "算法",
            "requirements": "硕士，熟悉 Python、PyTorch、LLM、RAG 和 Docker",
            "responsibilities": "负责大模型应用和 NLP 算法研发",
            "experience_required": "1-3年",
        }
        unrelated_jd = {
            "id": 10,
            "name": "Java 后端开发工程师",
            "category": "后端",
            "requirements": "本科，熟悉 Java、SpringBoot、MySQL、Redis",
            "responsibilities": "负责微服务后端开发",
            "experience_required": "5-10年",
        }

        matched = calculate_resume_jd_match(resume, matching_jd)
        unrelated = calculate_resume_jd_match(resume, unrelated_jd)

        self.assertGreater(matched["total_score"], unrelated["total_score"])
        self.assertEqual(sum(item["weight"] for item in matched["dimensions"]), 100)
        self.assertIn("python", matched["matched_skills"])
        self.assertIn("java", unrelated["missing_skills"])

    def test_six_month_quota_is_separate_for_each_recruitment_type(self):
        for jd_id in range(1, 4):
            application_repo.create({
                "candidate_username": "quota-user",
                "candidate_name": "额度测试",
                "jd_id": jd_id,
                "recruitment_type": "社招",
                "source": "candidate",
                "status": "cancel" if jd_id == 1 else "pending",
                "workflow_id": f"quota-{jd_id}",
            })
        application_repo.create({
            "candidate_username": "quota-user",
            "candidate_name": "额度测试",
            "jd_id": 4,
            "recruitment_type": "校招",
            "source": "candidate",
            "workflow_id": "campus-1",
        })
        application_repo.create({
            "candidate_username": "quota-user",
            "candidate_name": "额度测试",
            "jd_id": 99,
            "source": "admin",
            "workflow_id": "admin-invitation",
        })

        quota = application_repo.get_candidate_quota("quota-user")
        self.assertEqual(quota["buckets"]["社招"]["used"], 2)
        self.assertEqual(quota["buckets"]["社招"]["remaining"], 1)
        self.assertFalse(quota["buckets"]["社招"]["available_at"])
        self.assertEqual(quota["buckets"]["校招"]["remaining"], 2)
        self.assertEqual(quota["buckets"]["实习生"]["remaining"], 3)
        self.assertNotIn(1, [item["jd_id"] for item in quota["applications"]])


if __name__ == "__main__":
    unittest.main()
